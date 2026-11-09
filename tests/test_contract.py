"""The command catalog must match the public Game methods."""

import inspect

from crusader import Game
from crusader.commands import COMMANDS


def test_public_game_methods_match_catalog():
    methods = {
        name for name, value in inspect.getmembers(Game, predicate=inspect.isfunction) if not name.startswith("_")
    }
    assert methods == set(COMMANDS)


def test_catalog_signatures_and_metadata():
    for name, command in COMMANDS.items():
        params = list(inspect.signature(getattr(Game, name)).parameters.values())[1:]
        specs = command["params"]
        assert [param.name for param in params] == [spec["name"] for spec in specs], name
        for param, spec in zip(params, specs, strict=True):
            assert spec["type"], (name, param.name)
            if param.default is inspect.Parameter.empty:
                assert "default" not in spec, (name, param.name)
            else:
                assert "default" in spec, (name, param.name)
                assert spec["default"] == param.default, (name, param.name)
        assert command["command"]
        assert command["group"]
        assert command["return_type"]
        assert command["summary"]
