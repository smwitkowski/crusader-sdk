# Bridge protocol

The bridge serves REST and stateless streamable HTTP MCP from the same application. MCP tools use the command names and wire parameters in the [API reference](api.md); the MCP endpoint is `/mcp`. Both transports invoke the same serialized backend. `GET /health` returns `{"ok": true}` and checks the bridge, not game readiness.

## REST

Send `POST /api/{command}` with a JSON object of arguments. For example:

```sh
curl -X POST http://127.0.0.1:8000/api/state \
  -H 'Content-Type: application/json' -d '{}'
```

A successful response is `{"result": ...}`. An unknown command returns 404; malformed input, invalid arguments, and backend errors normally return 400 with `{"error": "..."}`. The Python `map` method uses the wire command `ascii_map`; `find_sites` sends `near_x` and `near_y` together.

Slow REST requests stream whitespace as keepalives before the final JSON object. A client must allow leading JSON whitespace and read the entire response. Once streaming has started the HTTP status is already 200, even if the final object contains an error; inspect the body. The Python client does this. Requests can take a long time: its default timeout is 600 seconds.

## Access control

The server defaults to loopback and no authentication. Configure `CRUSADER_TOKEN` to require `Authorization: Bearer <token>` on every route except `/health`, including MCP. The server also accepts `--token`, but prefer the environment variable to avoid exposing the token in command-line arguments. The Python client reads `CRUSADER_TOKEN` or accepts an explicit `token` in `Game` and `Game.connect`; the explicit value takes precedence. A token is not transport encryption; use an appropriate secure channel and do not expose an unauthenticated bridge to untrusted networks. Requests are limited to 64 KiB. All routes require a loopback `Host` by default; repeat `--allow-host` for additional host authorities. An `Origin`, if sent, must be loopback, and every POST requires `Content-Type: application/json`.
