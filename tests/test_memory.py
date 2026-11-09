import pytest

from crusader.bridge.memory import MAX_READ, _mapped, _range, parse_maps


def test_maps_permissions_and_boundaries():
    regions = parse_maps("1000-2000 rw-p 00000000 00:00 0\n2000-3000 r--p 00000000 00:00 0")
    assert _mapped(regions, 0x1000, 4, "w")
    assert _mapped(regions, 0x2FFC, 4, "r")
    assert not _mapped(regions, 0x1FFF, 2, "r")
    assert not _mapped(regions, 0x2000, 4, "w")


@pytest.mark.parametrize("address,size", [(-1, 4), (0, 0), (0, MAX_READ + 1), (2**64 - 1, 4), (True, 4)])
def test_invalid_ranges(address, size):
    with pytest.raises(ValueError):
        _range(address, size)


def test_malformed_map():
    with pytest.raises(ValueError):
        parse_maps("not a map")


def test_exact_byte_access_and_file_adapter(monkeypatch):
    from crusader.bridge import memory

    process = object.__new__(memory.ProcessMemory)
    process.pid = 1
    process._fd = 123
    process._verified = True
    process._identity = (10, "00:01")
    process._write_ranges = ((0x1000, 0x1010),)
    monkeypatch.setattr(memory.Path, "read_text", lambda _: "1000-2000 rw-p 0 00:01 10 /game")
    written = []
    monkeypatch.setattr(memory.os, "pwrite", lambda fd, data, address: written.append((address, data)) or len(data))
    monkeypatch.setattr(memory.os, "pread", lambda fd, size, address: b"x" * size)
    with process.file() as f:
        assert f.seek(0x1000) == 0x1000
        assert f.write(b"\x00\xff") == 2
        assert f.read(2) == b"xx"
        assert f.seek(-2, 1) == 0x1002
    assert written == [(0x1000, b"\x00\xff")]
    with pytest.raises(ValueError):
        f.read(1)
    with pytest.raises(ValueError):
        process.write_bytes(0x100F, b"xx")
    with pytest.raises(TypeError):
        process.write_bytes(0x1000, bytearray(b"x"))
    process._verified = False
    with pytest.raises(ValueError):
        process.write_bytes(0x1000, b"x")


def test_constructor_requires_hash_mapping_and_sanity(monkeypatch, tmp_path):
    import hashlib
    import os

    from crusader.bridge import memory

    exe = tmp_path / "game.exe"
    exe.write_bytes(b"game")
    info = exe.stat()
    device = f"{os.major(info.st_dev):02x}:{os.minor(info.st_dev):02x}"
    maps = f"1000-2000 rw-p 0 {device} {info.st_ino} /game"
    monkeypatch.setattr(memory.Path, "read_text", lambda _: maps)
    monkeypatch.setattr(memory.os, "open", lambda *args: 123)
    closed = []
    monkeypatch.setattr(memory.os, "close", lambda fd: closed.append(fd))
    with pytest.raises(ValueError, match="hash"):
        memory.ProcessMemory(1, exe, sanity=lambda _: True, write_ranges=((0x1000, 0x1010),))
    monkeypatch.setattr(memory, "GAME_SHA256", hashlib.sha256(b"game").hexdigest())
    with pytest.raises(ValueError, match="sanity"):
        memory.ProcessMemory(1, exe, sanity=lambda _: False, write_ranges=((0x1000, 0x1010),))
    assert closed == [123]
    with memory.ProcessMemory(1, exe, sanity=lambda _: True, write_ranges=((0x1000, 0x1010),)):
        pass
    assert closed == [123, 123]
    monkeypatch.setattr(memory.Path, "read_text", lambda _: "1000-2000 rw-p 0 00:01 0")
    with pytest.raises(ValueError, match="not mapped"):
        memory.ProcessMemory(1, exe, sanity=lambda _: True, write_ranges=((0x1000, 0x1010),))


def test_short_io_and_changed_mapping(monkeypatch):
    from crusader.bridge import memory

    process = object.__new__(memory.ProcessMemory)
    process.pid, process._fd, process._verified = 1, 123, True
    process._identity, process._write_ranges = (10, "00:01"), ((0x1000, 0x1010),)
    monkeypatch.setattr(memory.Path, "read_text", lambda _: "1000-2000 rw-p 0 00:01 10 /game")
    monkeypatch.setattr(memory.os, "pread", lambda *args: b"")
    monkeypatch.setattr(memory.os, "pwrite", lambda *args: 0)
    with pytest.raises(OSError):
        process.read_bytes(0x1000, 1)
    with pytest.raises(OSError):
        process.write_bytes(0x1000, b"x")
    monkeypatch.setattr(memory.Path, "read_text", lambda _: "1000-2000 rw-p 0 00:01 11 /game")
    with pytest.raises(ValueError, match="no longer mapped"):
        process.read_bytes(0x1000, 1)


def test_wrong_executable_hash_rejected(tmp_path, monkeypatch):
    from crusader.bridge import memory

    executable = tmp_path / "game.exe"
    executable.write_bytes(b"not the verified executable")
    monkeypatch.setattr(memory.Path, "read_text", lambda self: "")
    with pytest.raises(ValueError, match="unexpected game executable hash"):
        memory.ProcessMemory(123, executable, sanity=lambda _: True)


def test_write_outside_fixed_table_rejected(monkeypatch):
    from crusader.bridge import memory as memmod

    memory = memmod.ProcessMemory.__new__(memmod.ProcessMemory)
    memory._fd = 1
    memory._verified = True
    memory._write_ranges = memmod.GAME_WRITE_RANGES
    monkeypatch.setattr(memory, "_check", lambda *args: None)
    writes = []
    monkeypatch.setattr("os.pwrite", lambda *args: writes.append(args))
    with pytest.raises(ValueError, match="outside allowed ranges"):
        memory.write_i32(0x01FE7DDC, 1)
    assert not writes


def test_dynamic_region_registration_and_writes(monkeypatch):
    from crusader.bridge import memory as memmod

    process = object.__new__(memmod.ProcessMemory)
    process.pid, process._fd, process._verified = 1, 123, True
    process._identity, process._write_ranges = (10, "00:01"), memmod.GAME_WRITE_RANGES
    process._dynamic_regions = []
    maps = ["1000-2000 r-xp 0 00:01 10 /game\n3000-4000 rw-p 0 00:00 0"]
    monkeypatch.setattr(memmod.Path, "read_text", lambda _: maps[0])
    writes = []
    monkeypatch.setattr(memmod.os, "pwrite", lambda fd, data, address: writes.append((address, data)) or len(data))
    process.register_region(0x3100, 0x100)
    process.register_region(0x3200, 4)
    process.write_bytes(0x31FE, b"xx")
    process.write_bytes(0x3200, b"y")
    assert writes == [(0x31FE, b"xx"), (0x3200, b"y")]
    with pytest.raises(ValueError, match="outside allowed"):
        process.write_bytes(0x31FF, b"xx")
    with pytest.raises(ValueError, match="overlaps"):
        process.register_region(0x3180, 4)
    maps[0] = "1000-2000 r-xp 0 00:01 10 /game\n3000-4000 rw-p 0 00:00 0 [heap]"
    with pytest.raises(ValueError, match="mapping changed"):
        process.write_bytes(0x3100, b"x")


@pytest.mark.parametrize(
    "mapping,address,size",
    [
        ("3000-4000 rw-s 0 00:00 0", 0x3100, 4),
        ("3000-4000 rwxp 0 00:00 0", 0x3100, 4),
        ("3000-4000 rw-p 0 00:00 0 [stack]", 0x3100, 4),
        ("3000-4000 rw-p 0 00:01 10 /game", 0x3100, 4),
        ("3000-4000 rw-p 0 00:00 0\n4000-5000 rw-p 0 00:00 0", 0x3FFF, 2),
    ],
)
def test_dynamic_region_rejects_unsafe_mappings(monkeypatch, mapping, address, size):
    from crusader.bridge import memory as memmod

    process = object.__new__(memmod.ProcessMemory)
    process.pid, process._fd, process._verified = 1, 123, True
    process._identity, process._write_ranges = (10, "00:01"), memmod.GAME_WRITE_RANGES
    process._dynamic_regions = []
    monkeypatch.setattr(memmod.Path, "read_text", lambda _: "1000-2000 r-xp 0 00:01 10 /game\n" + mapping)
    with pytest.raises(ValueError):
        process.register_region(address, size)
    assert process._dynamic_regions == []
