"""Offline checks that command refusals leave process memory untouched."""

import pytest
from test_game import FakeMemory

from crusader.bridge import game


@pytest.fixture
def driver(monkeypatch):
    mem = FakeMemory()
    mem.pid = game._GamePid("42", mem)
    monkeypatch.setattr(game, "i32", mem.i32)
    monkeypatch.setattr(game, "write_i32", mem.write_i32)
    monkeypatch.setattr(game, "start_match", lambda **kwargs: mem.pid)
    monkeypatch.setattr(game, "seed_slot_address", lambda pid: 0x3000)
    mem.put_i32(game.MENU, game.MENU_IN_GAME)
    mem.put_i32(game.PAUSED, 1)
    result = game.Game(game.CastleBuilder())
    mem.writes.clear()
    return result, mem


def test_siege_rejects_unknown_engine_before_selection(driver):
    g, mem = driver
    with pytest.raises(game.RealGameError, match="unknown engine"):
        g.build_siege([1], "not_an_engine", 10, 10)
    assert mem.writes == []
    assert g._pending == []


def test_siege_rejects_hidden_engine_before_selection(driver, monkeypatch):
    g, mem = driver
    monkeypatch.setattr(game, "game_refuses", lambda *args, **kwargs: game.HIDDEN)
    with pytest.raises(game.RealGameError, match="siege menu does not offer"):
        g.build_siege([1], "catapult", 10, 10)
    assert mem.writes == []
    assert g._pending == []


def test_gate_rejects_non_boolean_without_queue_or_ui_write(driver, monkeypatch):
    g, mem = driver
    monkeypatch.setattr(game, "Terrain", lambda pid: object())
    gate = {"id": 3, "owner": 1, "type": next(iter(game.GATES)), "uid": 9}
    monkeypatch.setattr(game, "buildings", lambda *args: [gate])
    with pytest.raises(game.RealGameError, match="open must be true or false"):
        g.set_gate(3, 1)
    assert mem.writes == []


def test_gate_rejects_other_players_gate(driver, monkeypatch):
    g, mem = driver
    monkeypatch.setattr(game, "Terrain", lambda pid: object())
    gate = {"id": 3, "owner": 2, "type": next(iter(game.GATES)), "uid": 9}
    monkeypatch.setattr(game, "buildings", lambda *args: [gate])
    with pytest.raises(game.RealGameError, match="no building of yours"):
        g.set_gate(3, True)
    assert mem.writes == []


def test_ally_order_rejects_non_ally(driver):
    g, mem = driver
    with pytest.raises(game.RealGameError, match="not your ally"):
        g.ally_order(2, "defend")
    assert mem.writes == []


def test_ally_order_rejects_dead_lord(driver, monkeypatch):
    g, mem = driver
    g.allies = {2}
    g.ally_lords = {2: 12}
    monkeypatch.setattr(game, "units", lambda pid: [])
    with pytest.raises(game.RealGameError, match="has no lord left"):
        g.ally_order(2, "defend")
    assert mem.writes == []


def test_ally_send_rejects_insufficient_stock(driver, monkeypatch):
    g, mem = driver
    g.allies = {2}
    g.ally_lords = {2: 12}
    mem.put_i32(game.LORD_ID + game.STRIDE, 4)
    monkeypatch.setattr(game, "units", lambda pid: [{"id": 4, "uid": 12, "hp": 10, "x": 0, "y": 0}])
    with pytest.raises(game.RealGameError, match="you have 0 wood, not 5"):
        g.ally_send_goods(2, "wood", 5)
    assert mem.writes == []
