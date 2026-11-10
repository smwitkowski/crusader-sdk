# Crusader SDK

![Stronghold Crusader gameplay: a catapult firing across an oasis during a siege, driven through the SDK](assets/hero.jpg)

<sub>Gameplay screenshot from Stronghold Crusader, © Firefly Studios, captured from a game driven through this SDK.</sub>

[![CI](https://github.com/smwitkowski/crusader-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/smwitkowski/crusader-sdk/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/smwitkowski/crusader-sdk)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-blue)](https://docs.astral.sh/ruff/)
[![Pyright](https://img.shields.io/badge/type%20checking-pyright-blue)](https://github.com/microsoft/pyright)
[![PyPI](https://img.shields.io/pypi/v/crusader-sdk)](https://pypi.org/project/crusader-sdk/)
[![Python versions](https://img.shields.io/pypi/pyversions/crusader-sdk)](https://pypi.org/project/crusader-sdk/)
[![Codecov](https://codecov.io/gh/smwitkowski/crusader-sdk/graph/badge.svg)](https://codecov.io/gh/smwitkowski/crusader-sdk)

A Python SDK for observing and controlling Stronghold Crusader through a local bridge. Read game state, inspect the map, and issue commands from Python.

Unofficial; not affiliated with or endorsed by Firefly Studios. You must provide your own supported game files. See [LEGAL.md](LEGAL.md).

## Client example

With a bridge running (see [Get started](#get-started)), play a month of the game from Python:

```python
from crusader import CrusaderError, Game

game = Game.connect()  # CRUSADER_URL and CRUSADER_TOKEN are read from the environment
print(game.state()["gold"], "gold at tick", game.state()["tick"])

site = game.find_sites("granary", limit=1)[0]  # the game's own placement check
game.build("granary", site["x"], site["y"])
game.set_tax(2)

result = game.advance(800)  # one game month (800 ticks); the game is paused otherwise
for event in result["events"]:
    print(event["type"], event.get("message", ""))

try:
    game.set_tax(42)
except CrusaderError as exc:  # refusals come back as errors, like the game's UI
    print("refused:", exc)
```

## How it works

```mermaid
flowchart TB
    A["Your code or agent"] -->|"Python SDK, REST or MCP"| B["Bridge server"]
    B -->|"reads game memory"| G["Stronghold Crusader 1.41<br/>under Wine"]
    B -->|"queues commands, controls ticks"| U["UCP3 module inside the game"]
    U -->|"the game's own command queue"| G
```

Commands go through the same command queue the game's UI uses, so the game applies its own costs and rules. The game
stays paused between calls; time moves only when you call `advance`. Details: [how it works](docs/how-it-works.md).
The Docker setup has been verified live: `tools/smoke.py` passes all 12 steps against a fresh skirmish.

## Get started

1. Supply your own supported game files and [set up the bridge](docs/quickstart.md#run-the-bridge).
2. [Install the client](docs/quickstart.md#install-the-client): `pip install --pre crusader-sdk` (pre-release for now).
3. Connect to the running bridge and [try the client](docs/quickstart.md#install-the-client).

See the [quickstart](docs/quickstart.md) for bridge setup, requirements, and the experimental Docker option.

## Explore

| | |
| --- | --- |
| [Documentation](docs/index.md) | [API reference](docs/api.md) |
| [LLM guide](llms.txt) | [Protocol](docs/protocol.md) |
| [How it works](docs/how-it-works.md) | [Contributing](CONTRIBUTING.md) |
| [Security](SECURITY.md) | [Legal](LEGAL.md) |
