"""Integration tests for the local REST and MCP bridge."""

import json
import time

import pytest
from starlette.testclient import TestClient

from crusader.bridge.server import create_app
from crusader.commands import COMMANDS


class FakeGame:
    def __init__(self):
        self.calls = []

    def state(self):
        self.calls.append(("state", {}))
        return {"gold": 42}

    def look(self, x, y):
        self.calls.append(("look", {"x": x, "y": y}))
        return {"x": x, "y": y}

    def build(self, building, x, y):
        self.calls.append(("build", {"building": building, "x": x, "y": y}))
        return {"ok": True}


@pytest.fixture
def game():
    return FakeGame()


@pytest.fixture
def client(game):
    with TestClient(create_app(game), base_url="http://localhost") as client:
        yield client


def test_health_and_rest_dispatch(client, game):
    assert client.get("/health").status_code == 200
    response = client.post("/api/look", json={"x": 3, "y": 4})
    assert response.status_code == 200
    assert response.json()["result"] == {"x": 3, "y": 4}
    assert game.calls == [("look", {"x": 3, "y": 4})]


@pytest.mark.parametrize("body", [b"{", b"null", b"[]", b"1", b'"text"'])
def test_invalid_request_bodies_rejected(client, game, body):
    response = client.post("/api/look", content=body, headers={"content-type": "application/json"})
    assert 400 <= response.status_code < 500
    assert game.calls == []


@pytest.mark.parametrize(
    "command,args",
    [
        ("not_a_command", {}),
        ("look", {"x": 1}),
        ("look", {"x": 1, "y": 2, "extra": 3}),
    ],
)
def test_invalid_command_or_arguments_rejected(client, game, command, args):
    response = client.post(f"/api/{command}", json=args)
    assert response.status_code == (404 if command == "not_a_command" else 400)
    assert game.calls == []


def test_authentication_applies_to_command_endpoints(game):
    with TestClient(create_app(game, token="secret"), base_url="http://localhost") as client:
        assert client.get("/health").status_code == 200
        assert client.post("/api/state", json={}).status_code == 401
        assert client.post("/api/state", json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.post("/api/state", json={}, headers={"Authorization": "Bearer secret"}).status_code == 200
        assert client.post("/mcp", json={}).status_code == 401
    assert game.calls == [("state", {})]


def test_oversized_request_rejected(client, game):
    response = client.post("/api/look", content=b" " * (2 * 1024 * 1024), headers={"content-type": "application/json"})
    assert response.status_code == 413
    assert game.calls == []


def _mcp_response(response):
    assert response.status_code == 200
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        messages = [line[5:].strip() for line in response.text.splitlines() if line.startswith("data:")]
        return json.loads(messages[-1])
    return response.json()


def test_mcp_tool_names_match_command_spec(game):
    app = create_app(game)
    with TestClient(app, base_url="http://localhost:8000") as client:
        headers = {"Accept": "application/json, text/event-stream"}
        response = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert _mcp_response(response)["result"]
        session = response.headers.get("mcp-session-id")
        if session:
            headers["mcp-session-id"] = session
        response = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
        )
        assert response.status_code in (200, 202)
        response = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            },
        )
        tools = _mcp_response(response)["result"]["tools"]
        specs = {spec["command"]: spec for spec in COMMANDS.values()}
        assert {tool["name"] for tool in tools} == set(specs) == app.state.commands
        for tool in tools:
            spec = specs[tool["name"]]
            schema = tool["inputSchema"]
            assert set(schema["properties"]) == {
                name for parameter in spec["params"] for name in parameter.get("wire_names", [parameter["name"]])
            }
            assert set(schema.get("required", [])) == {
                name
                for parameter in spec["params"]
                if "default" not in parameter
                for name in parameter.get("wire_names", [parameter["name"]])
            }


def test_slow_response_is_valid_streamed_json(game):
    def slow_state():
        time.sleep(0.08)
        return {"gold": 42}

    game.state = slow_state
    with TestClient(create_app(game, slow_threshold=0.01), base_url="http://localhost") as client:
        response = client.post("/api/state", json={})
    assert response.status_code == 200
    assert response.json() == {"result": {"gold": 42}}
    assert response.content[:1].isspace()


def test_plain_jsonl_log_can_be_replayed(tmp_path, game):
    from crusader.bridge.server import replay

    log_path = tmp_path / "commands.jsonl"
    with TestClient(create_app(game, log_path=log_path), base_url="http://localhost") as client:
        assert client.post("/api/look", json={"x": 3, "y": 4}).status_code == 200
        assert client.post("/api/build", json={"building": "farm", "x": 5, "y": 6}).status_code == 200
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [entry["cmd"] for entry in entries] == ["look", "build"]
    assert [entry["args"] for entry in entries] == [
        {"x": 3, "y": 4},
        {"building": "farm", "x": 5, "y": 6},
    ]
    replay_game = FakeGame()
    replay(replay_game, log_path)
    assert replay_game.calls == game.calls


def test_optional_target_and_invalid_unit_lists(game):
    game.ally_order = lambda ally, order, target=None: {"target": target}
    game.move = lambda unit_ids, x, y: {"ids": unit_ids}
    with TestClient(create_app(game), base_url="http://localhost") as client:
        assert client.post("/api/ally_order", json={"ally": 2, "order": "attack", "target": 3}).status_code == 200
        assert client.post("/api/move", json={"unit_ids": [True], "x": 1, "y": 2}).status_code == 400


def test_replay_skips_errors_and_translates_near(tmp_path, game):
    from crusader.bridge.server import replay

    game.find_sites = lambda building, limit=5, near=None: game.calls.append((building, near)) or []
    path = tmp_path / "calls.jsonl"
    with TestClient(create_app(game, log_path=path, token="secret"), base_url="http://localhost") as client:
        headers = {"Authorization": "Bearer secret"}
        assert client.post("/api/look", json={"x": 1}, headers=headers).status_code == 400
        assert (
            client.post(
                "/api/find_sites", json={"building": "farm", "near_x": 2, "near_y": 3}, headers=headers
            ).status_code
            == 200
        )
    entries = [json.loads(line) for line in path.read_text().splitlines()]
    assert "error" in entries[0]
    game.calls.clear()
    replay(game, path)
    assert game.calls == [("farm", (2, 3))]


@pytest.mark.parametrize(
    "spec,expected",
    [
        ("castle_builder:12", ("castle_builder", 12)),
        ("skirmish:Inches Apart:rat:42", ("skirmish", "Inches Apart", "rat", 42)),
        ("load:my-save", ("load", "my-save")),
    ],
)
def test_cli_real_backend_configuration(monkeypatch, spec, expected):
    import sys
    import types

    import uvicorn

    from crusader.bridge.server import main

    calls = []
    module = types.ModuleType("crusader.bridge.game")
    module.CastleBuilder = lambda seed: ("castle_builder", seed)
    module.Skirmish = lambda map_name, ai, seed: ("skirmish", map_name, ai, seed)
    module.LoadSave = lambda name: ("load", name)
    module.Game = lambda match, **kwargs: calls.append((match, kwargs)) or FakeGame()
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setenv("CRUSADER_MATCH", spec)
    monkeypatch.setenv("CRUSADER_GAME_DIR", "/game")
    monkeypatch.setenv("CRUSADER_SAVES_DIR", "/saves")
    monkeypatch.setenv("CRUSADER_PROCESS_NAME", "game.exe")
    monkeypatch.delenv("CRUSADER_BACKEND", raising=False)
    monkeypatch.setattr(sys, "argv", ["crusader-bridge"])
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: None)
    main()
    assert calls == [(expected, {"game_dir": "/game", "process_lookup": "game.exe"})]


def test_cli_rejects_saves_dir(monkeypatch):
    import sys

    from crusader.bridge.server import main

    monkeypatch.setattr(sys, "argv", ["crusader-bridge", "--saves-dir", "/saves"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


@pytest.mark.parametrize("spec", ["skirmish:map:rat:nope", "skirmish::rat:1", "load:", "other"])
def test_cli_rejects_invalid_match(monkeypatch, spec):
    import sys
    import types

    from crusader.bridge.server import main

    module = types.ModuleType("crusader.bridge.game")
    module.CastleBuilder = module.Skirmish = module.LoadSave = lambda *args: args
    module.Game = lambda *args, **kwargs: pytest.fail("must reject invalid match before launching game")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.delenv("CRUSADER_BACKEND", raising=False)
    monkeypatch.setattr(sys, "argv", ["crusader-bridge", "--match", spec])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_cli_explicit_backend_does_not_import_game(monkeypatch):
    import sys
    import types

    import uvicorn

    from crusader.bridge.server import main

    module = types.ModuleType("fake_bridge_backend")
    game = FakeGame()
    module.create = lambda: game
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setitem(sys.modules, "crusader.bridge.game", None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crusader-bridge",
            "--backend",
            "fake_bridge_backend:create",
            "--match",
            "bad",
            "--allow-host",
            "bridge.example",
        ],
    )
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: calls.append(app))
    main()
    assert len(calls) == 1
    with TestClient(calls[0], base_url="http://localhost") as client:
        assert client.get("/health", headers={"host": "bridge.example"}).status_code == 200


def test_streamed_error_is_json_after_200(game):
    def slow_failure():
        time.sleep(0.04)
        raise ValueError("command refused")

    game.state = slow_failure
    with TestClient(create_app(game, slow_threshold=0.01), base_url="http://localhost") as client:
        response = client.post("/api/state", json={})
    assert response.status_code == 200
    assert response.json() == {"error": "command refused"}


@pytest.mark.parametrize("path", ["/health", "/api/state", "/mcp", "/missing"])
def test_guard_checks_host_origin_and_post_type_on_every_route(game, path):
    with TestClient(create_app(game), base_url="http://localhost") as client:
        assert client.get(path, headers={"host": "evil.test"}).status_code == 421
        assert client.get(path, headers={"origin": "https://evil.test"}).status_code == 403
        assert client.post(path, content=b"{}", headers={"content-type": "text/plain"}).status_code == 415
    assert game.calls == []


@pytest.mark.parametrize("host", ["localhost", "localhost:8000", "127.0.0.1:4", "[::1]:8000"])
def test_loopback_hosts_accepted(game, host):
    with TestClient(create_app(game), base_url="http://localhost") as client:
        assert client.get("/health", headers={"host": host, "origin": "http://localhost:123"}).status_code == 200


@pytest.mark.parametrize(
    "host", ["localhost.evil", "localhost@evil", "localhost:abc", "[::1]evil", "127.0.0.1:99999", "localhost, evil"]
)
def test_invalid_hosts_rejected(game, host):
    with TestClient(create_app(game), base_url="http://localhost") as client:
        assert client.get("/health", headers={"host": host}).status_code == 421


@pytest.mark.parametrize(
    "origin",
    [
        "null",
        "http://localhost.evil",
        "http://localhost@evil",
        "http://localhost/path",
        "http://localhost?",
        "http://localhost:99999",
    ],
)
def test_invalid_origins_rejected(game, origin):
    with TestClient(create_app(game), base_url="http://localhost") as client:
        assert client.get("/health", headers={"origin": origin}).status_code == 403


def test_explicit_allowed_host_and_json_content_type(game):
    with TestClient(create_app(game, allow_hosts=["bridge.example"]), base_url="http://localhost") as client:
        assert (
            client.post(
                "/api/state",
                content=b"{}",
                headers={"host": "bridge.example:8000", "content-type": "application/json; charset=utf-8"},
            ).status_code
            == 200
        )
        assert (
            client.post("/api/state", content=b"{}", headers={"content-type": "application/jsonp"}).status_code == 415
        )
        assert (
            client.get("/health", headers={"host": "bridge.example", "origin": "https://bridge.example"}).status_code
            == 403
        )
