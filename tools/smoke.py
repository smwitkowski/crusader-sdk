#!/usr/bin/env python3
"""Exercise a running bridge against a prepared, disposable game.

The game needs room and resources for a hovel, a mercenary post, gold, and an
idle peasant. Commands change the game; start from a disposable match.
"""

import argparse
import sys

from crusader import CrusaderError, Game


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    game = Game.connect()
    failed = False

    def step(name, action):
        nonlocal failed
        try:
            value = action()
        except Exception as exc:
            print(f"SMOKE FAIL {name}: {exc}", flush=True)
            failed = True
            return None
        print(f"SMOKE PASS {name}", flush=True)
        return value

    def refuse(action, reason):
        try:
            action()
        except CrusaderError as exc:
            if reason not in str(exc).lower():
                raise AssertionError(f"unexpected refusal: {exc}") from exc
            return
        raise AssertionError("command was accepted")

    state = step("connect/state", game.state)
    sites = step("find_sites", lambda: game.find_sites("hovel"))

    def build():
        if not sites:
            raise ValueError("no hovel sites found")
        return game.build("hovel", sites[0]["x"], sites[0]["y"])

    step("build", build)
    step("set_tax", lambda: game.set_tax(0))

    def advance_month():
        if state is None:
            raise ValueError("initial state unavailable")
        result = game.advance(800)
        if result["tick"] != state["tick"] + 800:
            raise ValueError(f"advance stopped at tick {result['tick']}; expected {state['tick'] + 800}")
        return result

    step("advance", advance_month)
    step("events", game.events)
    recruited = step("recruit", lambda: game.recruit("slave", 1))

    def move():
        if recruited is None:
            raise ValueError("recruit failed")
        game.advance(100)
        units = [u for u in game.state()["units"] if u["owner"] == 1 and u["type"] == "slave"]
        if not units:
            raise ValueError("no recruited slave visible after 100 ticks")
        unit = units[-1]
        return game.move([unit["id"]], unit["x"], unit["y"])

    step("move", move)
    step("illegal site refusal", lambda: refuse(lambda: game.build("hovel", -1, -1), "cannot place"))
    step("tax out of range refusal", lambda: refuse(lambda: game.set_tax(9), "level"))
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
