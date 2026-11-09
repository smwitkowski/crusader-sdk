"""Tests of the original bridge driver using a synthetic process memory image."""

import ast
import builtins
import inspect
import struct

import pytest

from crusader.bridge import game


class FakeMemory:
    def __init__(self):
        self.data = {}
        self.writes = []
        self.pos = 0

    def put(self, address, data):
        self.data.update({address + i: b for i, b in enumerate(data)})

    def put_i32(self, address, value):
        self.put(address, struct.pack("<i", value))

    def i32(self, pid, address):
        return struct.unpack("<i", self.bytes(address, 4))[0]

    def write_i32(self, pid, address, value):
        self.writes.append((address, value))
        self.put_i32(address, value)
        if address == 0x1000:  # the bridge consumes the mailbox
            self.put_i32(address, 0)
        if address == 0x2000:  # the bridge pauses at the requested tick
            self.put_i32(game.TICK, value)
            self.put_i32(game.PAUSED, 1)

    def bytes(self, address, size):
        return bytes(self.data.get(address + i, 0) for i in range(size))

    def file(self):
        return self

    def seek(self, address):
        self.pos = address

    def read(self, size):
        data = self.bytes(self.pos, size)
        self.pos += size
        return data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def memory(monkeypatch):
    mem = FakeMemory()
    mem.pid = game._GamePid("42", mem)
    monkeypatch.setattr(game, "i32", mem.i32)
    monkeypatch.setattr(game, "write_i32", mem.write_i32)
    monkeypatch.setattr(game, "mailbox_address", lambda pid: 0x1000)
    monkeypatch.setattr(game, "target_address", lambda pid: 0x2000)
    mem.put_i32(game.MENU, game.MENU_IN_GAME)
    mem.put_i32(game.PAUSED, 1)
    return mem


@pytest.fixture
def terrain(memory):
    # A square, flat 400x201 patch, with the remaining rows empty.
    width, height = 400, 201
    for y in range(game.MAP_SIDE):
        start = min(y, height) * width
        end = min(y + 1, height) * width
        memory.put(game.ROWS + y * 12, struct.pack("<iii", start, 0, end))
    memory.put(game.TMS + game.LOGIC, struct.pack("<i", game.L_LAND) * game.N_TILES)
    memory.put(game.TMS + game.LOGIC2, bytes([game.FARMABLE]) * game.N_TILES)
    return game.Terrain(memory.pid)


def test_driver_does_not_open_proc_memory_directly():
    tree = ast.parse(inspect.getsource(game))
    direct_opens = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        if not (
            (isinstance(func, ast.Name) and func.id == "open")
            or (isinstance(func, ast.Attribute) and func.attr == "open")
        ):
            continue
        parts = [
            part.value
            for part in ast.walk(node.args[0])
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        ]
        path = "".join(parts)
        if "/proc/" in path and "/mem" in path:
            direct_opens.append(node.lineno)
    assert not direct_opens, f"direct process memory opens at lines {direct_opens}"


def test_read_bytes_uses_attached_process_memory(monkeypatch):
    class Memory:
        def __init__(self):
            self.reads = []

        def read_bytes(self, address, size):
            self.reads.append((address, size))
            return b"abc"

        def file(self):
            from crusader.bridge.memory import MemoryFile

            return MemoryFile(self)

    memory = Memory()
    pid = game._GamePid("42", memory)

    def forbid_open(*args, **kwargs):
        raise AssertionError("read bypassed ProcessMemory")

    monkeypatch.setattr(builtins, "open", forbid_open)
    assert game.read_bytes(pid, 0x1234, 3) == b"abc"
    assert memory.reads == [(0x1234, 3)]


def test_footprints():
    assert game.footprint("hovel") == (54, 4)
    assert game.footprint("catapult") == (190, 3)
    assert game.footprint("tunnel") == (66, 3)
    with pytest.raises(KeyError):
        game.footprint("unknown")


def test_terrain_tile_and_placement(terrain):
    t = terrain
    assert t.tile(2, 3) == 1202
    assert t.tile(-1, 0) is None
    assert t.tile(0, 201) is None
    assert t.site_error("hovel", 2, 3) is None
    assert t.site_error("hovel", 398, 3) == "off the map"
    assert "taken" in t.site_error("hovel", 2, 3, {(3, 4): "queued"})
    i = t.tile(3, 4)
    t.building[i] = 5
    assert "building" in t.site_error("hovel", 2, 3)
    t.building[i] = 0
    t.unit[i] = 1
    assert "unit" in t.site_error("hovel", 2, 3)
    t.unit[i] = 0
    t.height[i] = 1
    assert "not flat" in t.site_error("hovel", 2, 3)
    t.height[i] = 0
    t.logic2[i] = 0
    assert "not farmable" in t.site_error("wheat_farm", 2, 3)
    assert "not iron ore" in t.site_error("iron_mine", 2, 3)


def test_read_state_reads_signed_and_stock(memory):
    values = {
        game.TICK: 123,
        game.PAUSED: 1,
        game.MONTH: 2,
        game.YEAR: 1100,
        game.TAXES: 3,
        game.RATIONS: 2,
        game.POPULARITY_X100: 9949,
        game.POPULATION: 8,
        game.HOUSING: 12,
    }
    for addr, value in values.items():
        memory.put_i32(addr, value)
    for index in game.GOODS.values():
        memory.put_i32(game.STOCK + 4 * index, index * 10)
    assert game.read_state(memory.pid) == {
        "tick": 123,
        "paused": True,
        "month": 2,
        "year": 1100,
        "tax": 3,
        "rations": 2,
        "popularity": 99.49,
        "population": 8,
        "housing": 12,
        "stock": {name: index * 10 for name, index in game.GOODS.items()},
    }


def test_mailbox_order_and_advance(memory):
    game.queue_command(game.CHANGE_TAXES, 5, pid=memory.pid)
    assert memory.writes == [(0x1004 + 4 * i, v) for i, v in enumerate((5, 0, 0, 0, 0, 0))] + [
        (0x1000, game.CHANGE_TAXES)
    ]
    memory.writes.clear()
    memory.put_i32(game.TICK, 12)
    assert game.advance(3, pid=memory.pid) == 15
    assert memory.writes == [(0x2000, 15)]


def test_build_refuses_blocked_tile_before_any_write(memory, terrain, monkeypatch):
    monkeypatch.setattr(game, "start_match", lambda **kwargs: memory.pid)
    monkeypatch.setattr(game, "seed_slot_address", lambda pid: 0x3000)
    monkeypatch.setattr(game, "Terrain", lambda pid: terrain)
    driver = game.Game(game.CastleBuilder())
    terrain.building[terrain.tile(2, 3)] = 7
    memory.writes.clear()
    with pytest.raises(game.RealGameError, match="not free"):
        driver.build("hovel", 2, 3)
    assert memory.writes == []


def test_required_game_port_functions_exist():
    from crusader.commands import COMMANDS

    missing = [spec["command"] for spec in COMMANDS.values() if not hasattr(game.Game, spec["command"])]
    assert not missing, f"Unimplemented commands: {missing}"
    assert all(hasattr(game, name) for name in ("footprint", "Terrain", "read_state", "place_reason"))
