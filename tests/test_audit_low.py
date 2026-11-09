import struct
import subprocess

import pytest

from crusader.bridge import game
from crusader.bridge.memory import MAX_READ


class UnitMemory:
    def __init__(self, count):
        self.data = bytearray(count * game.UNIT_SIZE)
        self.pos = 0
        self.reads = []

    def file(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def seek(self, address):
        self.pos = address - game.UNITS

    def read(self, size):
        assert 0 < size <= MAX_READ
        self.reads.append(size)
        data = self.data[self.pos : self.pos + size]
        self.pos += size
        return data


def test_unit_scans_chunk_large_tables(monkeypatch):
    count = MAX_READ // game.UNIT_SIZE + 3
    memory = UnitMemory(count)
    slot = (count - 1) * game.UNIT_SIZE
    struct.pack_into("<hh", memory.data, slot + game.U_STATE, 2, game.PEASANT)
    struct.pack_into("<h", memory.data, slot + game.U_OWNER, 1)
    pid = game._GamePid("42", memory)
    monkeypatch.setattr(game, "i32", lambda pid, address: count)
    assert [unit["id"] for unit in game.units(pid)] == [count - 1]
    assert game.idle_peasants(pid) == 1
    assert len(memory.reads) == 4


def test_save_name_validation_survives_optimized_python(monkeypatch):
    monkeypatch.setattr(game, "_require_game_pid", lambda pid: pid)
    for name in ("a/b", "a" * 250):
        with pytest.raises(game.RealGameError):
            game.save_game(name, object())


def test_xdo_propagates_failure(monkeypatch):
    monkeypatch.setattr(game, "IN_CONTAINER", True)

    def fail(*args, **kwargs):
        assert kwargs["check"] is True
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(game.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        game._xdo("mousemove", 1, 2)


def test_goods_amount_rejects_out_of_range():
    instance = object.__new__(game.Game)
    instance.game_over = None
    assert instance._goods_amount("wood", 2147483645) == game.GOODS["wood"]
    with pytest.raises(game.RealGameError):
        instance._goods_amount("wood", 2147483650)


def test_xdo_requires_explicit_container(monkeypatch):
    monkeypatch.setattr(game, "IN_CONTAINER", False)
    monkeypatch.setattr(game, "CONTAINER", None)
    with pytest.raises(game.RealGameError, match="CRUSADER_CONTAINER"):
        game._xdo("mousemove", 1, 2)
