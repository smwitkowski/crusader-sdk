# Quickstart

## Install the client

The client requires Python 3.10 or later. From a checkout:

```sh
python -m pip install .
```

The client needs a running bridge and does not start the game itself. Against a bridge on the default local address:

```python
from crusader import Game, CrusaderError

game = Game.connect()  # or Game.connect("http://127.0.0.1:8000")
try:
    print(game.state())
    print(game.map(0, 0, 20, 20))
    print(game.advance(100))
except CrusaderError as exc:
    print(f"Bridge refused the request: {exc}")
```

`CRUSADER_URL` overrides the default URL when no URL is passed. Set `CRUSADER_TOKEN` to the bridge token for authenticated requests, or pass `token=` to `Game` or `Game.connect`. Prefer the environment variable over command-line arguments for secrets. `advance` changes the game; choose a tick count appropriate for your match. See [concepts](concepts.md), the [API reference](api.md), and [protocol](protocol.md).

## Run the bridge

For a bridge installation, install the optional dependencies with `python -m pip install '.[bridge]'`, then run `crusader-bridge --help` for match and process options. The real backend requires the supported game, Wine/Linux process access, and the included UCP3 module. Integration needs a live game run. The `--backend module:callable` option is a development hook for selecting an explicit backend factory. Alternatively, the following experimental Docker setup packages the runtime.

## Run with Docker

This container setup is experimental and has not yet been verified with a live game. You need Docker and your own legally obtained, supported Stronghold Crusader game folder. The image targets `linux/amd64`; other hosts require Docker's amd64 emulation.

From the repository root, verify the executable and build the image:

```sh
./scripts/check-game-files.sh "/path/to/your/game"
./scripts/build-image.sh
```

The game folder must contain `Stronghold Crusader.exe` with the supported SHA-256. The build downloads and verifies UCP3; it does not include the game. Optionally, check a UCP3 archive separately with `./scripts/check-game-files.sh "/path/to/your/game" "/path/to/UCP3.zip"`.

Set `CRUSADER_TOKEN` in the host environment, replace the example path with the absolute path to your game folder, and run:

```sh
docker run --rm --name crusader-sdk \
  --platform linux/amd64 \
  --cap-drop ALL \
  --cap-add SYS_PTRACE \
  -e CRUSADER_TOKEN \
  --mount type=bind,src="/path/to/your/game",dst=/game,readonly \
  -p 127.0.0.1:8000:8000 \
  crusader-sdk:local --host 0.0.0.0
```

The command adds only `SYS_PTRACE` for game-process access; whether it is required has not been verified. Do not use `--privileged` or host networking. The bridge binds to all container interfaces so Docker can publish it, but the published port is restricted to host loopback. The bridge is unauthenticated unless a token is configured; do not expose it to untrusted networks. Other containers on the same Docker network may still reach it.

Check the bridge from the host:

```sh
curl http://127.0.0.1:8000/health
```

The container copies the mounted game to `/opt/crusader` and runs the copy. The original mount remains read-only. Saves are in `/home/crusader/Stronghold Crusader/Saves` inside the container and are lost when the `--rm` container is removed. To load an existing save, place it in the source game's `Saves` folder before starting and pass `--match load:NAME` after the image name (alongside `--host 0.0.0.0`). Stop the container with `docker stop crusader-sdk`.
