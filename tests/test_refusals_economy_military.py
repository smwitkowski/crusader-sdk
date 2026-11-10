"""Offline checks that documented command refusals happen before memory writes."""

import pytest

from crusader.bridge import game

pytest_plugins = ["test_game"]


@pytest.fixture
def driver(memory, monkeypatch):
    monkeypatch.setattr(game, "start_match", lambda **kwargs: memory.pid)
    monkeypatch.setattr(game, "seed_slot_address", lambda pid: 0x3000)
    result = game.Game(game.CastleBuilder())
    result.menu = False
    memory.writes.clear()
    return result


@pytest.mark.parametrize(
    ("method", "args", "reason"),
    [
        ("set_tax", (9,), "tax level must be"),
        ("set_tax", (True,), "tax level must be"),
        ("set_rations", ("banquet",), "rations must be"),
        ("trade", ("gold", 5), "unknown good"),
        ("recruit", ("dragon", 1), "unknown unit"),
        ("recruit", ("archer", 0), "count must be"),
        ("recruit", ("archer", 1), "need a barracks"),
    ],
)
def test_economy_refuses_before_writes(driver, memory, method, args, reason):
    with pytest.raises(game.RealGameError, match=reason):
        getattr(driver, method)(*args)
    assert memory.writes == []
    assert driver._reserved == {}


def test_trade_without_market_refuses_before_writes(driver, memory):
    resource = game.GOODS["wood"]
    memory.put_i32(game.TRADEABLE + 4 * resource, 1)
    with pytest.raises(game.RealGameError, match="need a market"):
        driver.trade("wood", 5)
    assert memory.writes == []
    assert driver._reserved == {}


@pytest.mark.parametrize("ids", [None, [], [1, 1], [True], list(range(501))])
def test_military_invalid_selection_refuses_before_writes(driver, memory, ids):
    with pytest.raises(game.RealGameError, match=r"1\.\.500 distinct integers"):
        driver.stop(ids)
    assert memory.writes == []


def test_military_enemy_unit_refused_before_writes(driver, memory, monkeypatch):
    monkeypatch.setattr(
        game, "units", lambda pid: [{"id": 17, "owner": 2, "type": game.UNIT_TYPE["archer"], "hp": 100}]
    )
    with pytest.raises(game.RealGameError, match="not one of your live soldiers"):
        driver.move([17], 2, 3)
    assert memory.writes == []


def test_military_invalid_stance_refused_before_selection(driver, memory, monkeypatch):
    monkeypatch.setattr(
        game, "units", lambda pid: [{"id": 17, "owner": 1, "type": game.UNIT_TYPE["archer"], "hp": 100}]
    )
    with pytest.raises(game.RealGameError, match="stance must be"):
        driver.set_stance([17], "charge")
    assert memory.writes == []


def test_move_off_map_refused_before_selection(driver, memory, terrain, monkeypatch):
    monkeypatch.setattr(game, "Terrain", lambda pid: terrain)
    monkeypatch.setattr(
        game, "units", lambda pid: [{"id": 17, "owner": 1, "type": game.UNIT_TYPE["archer"], "hp": 100}]
    )
    with pytest.raises(game.RealGameError, match="off the map"):
        driver.move([17], -1, 3)
    assert memory.writes == []
