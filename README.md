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

With a bridge already running locally:

```python
from crusader import CrusaderError, Game

try:
    game = Game.connect()
    state = game.state()
    print(f"Tick: {state['tick']}")
    print(game.map(0, 0, 20, 20))
    print(game.advance(100))  # advances the game by 100 ticks
except CrusaderError as exc:
    print(f"Request failed: {exc}")
```

## How it works

```mermaid
flowchart LR
    Client[Python client] -->|HTTP commands| Bridge[Bridge]
    Bridge -->|process memory| Game[Stronghold Crusader under Wine / Xvfb]
    Bridge -->|tick control and mailbox| Module[UCP3 module]
    Module -->|game command queue| Game
```

The real backend runs or attaches to the supported game under Linux/Wine. The port and Docker integration have only been tested offline and still need a live game run. See [how it works](docs/how-it-works.md).

## Get started

1. Supply your own supported game files and [set up the bridge](docs/quickstart.md#run-the-bridge).
2. From a checkout, [install the client](docs/quickstart.md#install-the-client) with `python -m pip install .`.
3. Connect to the running bridge and [try the client](docs/quickstart.md#install-the-client).

See the [quickstart](docs/quickstart.md) for bridge setup, requirements, and the experimental Docker option.

## Explore

| | |
| --- | --- |
| [Documentation](docs/index.md) | [API reference](docs/api.md) |
| [LLM guide](llms.txt) | [Protocol](docs/protocol.md) |
| [How it works](docs/how-it-works.md) | [Contributing](CONTRIBUTING.md) |
| [Security](SECURITY.md) | [Legal](LEGAL.md) |
