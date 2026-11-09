"""Bounded access to a verified game process. Never expose this interface over HTTP."""

from __future__ import annotations

import hashlib
import os
import struct
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

GAME_SHA256 = "3bb0a8c1e72331b3a30a5aa93ed94beca0081b476b04c1960e26d5b45387ac5a"
MAX_READ = 1024 * 1024

# Half-open ranges for the fixed-address host writes in game.py. Hook addresses
# (mailbox, tick target and seed slot) are dynamic and deliberately excluded.
GAME_WRITE_RANGES = (
    (0x01FE7DD8, 0x01FE7DDC),  # SPEED
    (0x01A24A64, 0x01A24A68),  # SK_SCROLL
    (0x01652740 + 0x150 + 0xFA * 2, 0x01652740 + 0x150 + 0xFA * 3),  # SAVE_NAME
    (0x01387FAC, 0x01387FAC + 400),  # SELECTION
)


class Memory(Protocol):
    def read_bytes(self, address: int, size: int) -> bytes: ...
    def read_i32(self, address: int) -> int: ...
    def write_i32(self, address: int, value: int) -> None: ...
    def write_bytes(self, address: int, data: bytes) -> None: ...


@dataclass(frozen=True)
class Region:
    start: int
    end: int
    permissions: str
    device: str
    inode: int
    path: str


def parse_maps(text: str) -> list[Region]:
    regions = []
    for line in text.splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) < 5:
            raise ValueError("malformed process map")
        bounds, permissions, _offset, device, inode = fields[:5]
        start, end = (int(x, 16) for x in bounds.split("-"))
        if start >= end or len(permissions) != 4:
            raise ValueError("malformed process map")
        regions.append(Region(start, end, permissions, device, int(inode), fields[5] if len(fields) > 5 else ""))
    return regions


def _range(address: int, size: int) -> tuple[int, int]:
    if type(address) is not int or type(size) is not int or address < 0 or not 0 < size <= MAX_READ:
        raise ValueError("invalid memory range")
    end = address + size
    if end > 1 << 64:
        raise ValueError("invalid memory range")
    return address, end


def _mapped(regions: list[Region], address: int, size: int, permission: str) -> bool:
    start, end = _range(address, size)
    return any(r.start <= start and end <= r.end and permission in r.permissions[:2] for r in regions)


class ProcessMemory:
    """Linux process memory, enabled only after executable and layout checks.

    ``executable`` is the mapped game executable, not Wine's loader. ``sanity``
    must check known layout values and return exactly True. Writes are restricted
    to fixed game write ranges by default; the driver must validate values.
    Explicit ranges replace that default and are a trusted caller responsibility.
    A trusted caller may register dynamic module regions after validating each
    address and size. Its mapping is rechecked before each dynamic write.
    """

    def __init__(
        self,
        pid: int,
        executable: str | Path,
        *,
        sanity: Callable[[Memory], bool],
        write_ranges: tuple[tuple[int, int], ...] = GAME_WRITE_RANGES,
    ):
        if type(pid) is not int or pid <= 0 or not callable(sanity) or not write_ranges:
            raise ValueError("pid, sanity check and write ranges are required")
        for start, end in write_ranges:
            _range(start, end - start)
        self.pid = pid
        self._write_ranges = tuple(write_ranges)
        self._dynamic_regions: list[tuple[int, int, Region]] = []
        self._fd = -1
        self._verified = False
        self._identity: tuple[int, str] | None = None
        proc = Path(f"/proc/{pid}")
        regions = parse_maps((proc / "maps").read_text())
        with open(executable, "rb") as exe:
            stat = os.fstat(exe.fileno())
            hasher = hashlib.sha256()
            for block in iter(lambda: exe.read(1024 * 1024), b""):
                hasher.update(block)
            digest = hasher.hexdigest()
        if digest != GAME_SHA256:
            raise ValueError("unexpected game executable hash")
        if not any(
            r.inode == stat.st_ino
            and r.device == f"{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}"
            and r.path
            and not r.path.endswith(" (deleted)")
            for r in regions
        ):
            raise ValueError("verified executable is not mapped by process")
        self._identity = (stat.st_ino, f"{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}")
        self._fd = os.open(proc / "mem", os.O_RDWR | os.O_CLOEXEC)
        try:
            if sanity(self) is not True:
                raise ValueError("game layout sanity check failed")
            self._verified = True
        except BaseException:
            self.close()
            raise

    def _check(self, address: int, size: int, permission: str) -> None:
        if self._fd < 0:
            raise ValueError("memory is closed")
        regions = parse_maps(Path(f"/proc/{self.pid}/maps").read_text())
        if not any(
            (r.inode, r.device) == self._identity and r.path and not r.path.endswith(" (deleted)") for r in regions
        ):
            raise ValueError("verified executable is no longer mapped")
        if not _mapped(regions, address, size, permission):
            raise ValueError("memory range is not mapped with required permissions")

    def register_region(self, address: int, size: int) -> None:
        """Authorize one caller-validated module allocation for bounded writes."""
        if not self._verified or self._fd < 0:
            raise ValueError("memory is not verified")
        start, end = _range(address, size)
        if any(
            start < registered_end and registered_start < end
            for registered_start, registered_end, _ in self._dynamic_regions
        ):
            raise ValueError("dynamic region overlaps an existing registration")
        self._check(address, size, "w")
        regions = parse_maps(Path(f"/proc/{self.pid}/maps").read_text())
        candidates = [r for r in regions if r.start <= start and end <= r.end]
        if len(candidates) != 1:
            raise ValueError("dynamic region must be in one mapping")
        region = candidates[0]
        if (
            region.permissions != "rw-p"
            or (region.inode, region.device) == self._identity
            or region.path.startswith("[stack")
        ):
            raise ValueError("dynamic region must be private writable non-image memory")
        self._dynamic_regions.append((start, end, region))

    def read_bytes(self, address: int, size: int) -> bytes:
        self._check(address, size, "r")
        data = os.pread(self._fd, size, address)
        if len(data) != size:
            raise OSError("short memory read")
        return data

    def read_i32(self, address: int) -> int:
        return struct.unpack("<i", self.read_bytes(address, 4))[0]

    def write_i32(self, address: int, value: int) -> None:
        if not self._verified:
            raise ValueError("memory is not verified")
        if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
            raise ValueError("invalid signed 32-bit value")
        self.write_bytes(address, struct.pack("<i", value))

    def write_bytes(self, address: int, data: bytes) -> None:
        if not self._verified:
            raise ValueError("memory is not verified")
        if type(data) is not bytes:
            raise TypeError("memory writes require bytes")
        self._check(address, len(data), "w")
        if not any(start <= address and address + len(data) <= end for start, end in self._write_ranges):
            dynamic = next(
                (
                    entry
                    for entry in getattr(self, "_dynamic_regions", ())
                    if entry[0] <= address and address + len(data) <= entry[1]
                ),
                None,
            )
            if dynamic is None:
                raise ValueError("write is outside allowed ranges")
            regions = parse_maps(Path(f"/proc/{self.pid}/maps").read_text())
            if dynamic[2] not in regions:
                raise ValueError("dynamic region mapping changed")
        if os.pwrite(self._fd, data, address) != len(data):
            raise OSError("short memory write")

    def file(self) -> MemoryFile:
        """Return an independently positioned, bounded file-like adapter."""
        return MemoryFile(self)

    def close(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1
            self._verified = False

    def __enter__(self) -> ProcessMemory:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class MemoryFile:
    """Seek/read/write adapter; closing it does not close the underlying memory."""

    def __init__(self, memory: Memory):
        self._memory = memory
        self._position = 0
        self._closed = False

    def seek(self, offset: int, whence: int = 0) -> int:
        if self._closed:
            raise ValueError("file is closed")
        if type(offset) is not int or whence not in (0, 1):
            raise ValueError("invalid seek")
        position = offset if whence == 0 else self._position + offset
        if position < 0 or position >= 1 << 64:
            raise ValueError("invalid seek")
        self._position = position
        return position

    def read(self, size: int) -> bytes:
        if self._closed:
            raise ValueError("file is closed")
        data = self._memory.read_bytes(self._position, size)
        self._position += len(data)
        return data

    def write(self, data: bytes) -> int:
        if self._closed:
            raise ValueError("file is closed")
        self._memory.write_bytes(self._position, data)
        self._position += len(data)
        return len(data)

    def close(self) -> None:
        self._closed = True

    def __enter__(self) -> MemoryFile:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
