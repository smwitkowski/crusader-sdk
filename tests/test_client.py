"""Tests against a local HTTP bridge, without a running game."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest

from crusader import CrusaderError, Game


@pytest.fixture
def bridge():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            self.server.requests.append((self.path, json.loads(self.rfile.read(length))))
            self.server.auth_headers.append(self.headers.get("Authorization"))
            status, body = self.server.responses.pop(0)
            body = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.requests = []
    server.auth_headers = []
    server.responses = []
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_unwrap_and_keepalive_whitespace(bridge):
    server, url = bridge
    server.responses.append((200, '\n  \n{"result": {"gold": 42}}'))
    assert Game(url + "/").state() == {"gold": 42}
    assert server.requests == [("/api/state", {})]


@pytest.mark.parametrize("status", [400, 404, 200])
def test_bridge_errors(bridge, status):
    server, url = bridge
    server.responses.append((status, '{"error": "bridge rejected command"}'))
    with pytest.raises(CrusaderError, match="bridge rejected command"):
        Game(url).state()


def test_environment_url_and_explicit_override(bridge, monkeypatch):
    server, url = bridge
    monkeypatch.setenv("CRUSADER_URL", url)
    server.responses.append((200, '{"result": 7}'))
    assert Game.connect().state() == 7
    assert Game.connect("http://example.test/").url == "http://example.test"


def test_bearer_token_configuration(bridge, monkeypatch):
    server, url = bridge
    monkeypatch.setenv("CRUSADER_TOKEN", "environment-secret")
    server.responses.extend([(200, '{"result": true}')] * 4)
    assert Game(url).state() is True
    assert Game.connect(url).state() is True
    assert Game.connect(url, token="explicit-secret").state() is True
    assert Game(url, token="").state() is True
    assert server.auth_headers == [
        "Bearer environment-secret",
        "Bearer environment-secret",
        "Bearer explicit-secret",
        None,
    ]


def test_no_token_omits_authorization(bridge, monkeypatch):
    server, url = bridge
    monkeypatch.delenv("CRUSADER_TOKEN", raising=False)
    server.responses.append((200, '{"result": true}'))
    assert Game(url).state() is True
    assert server.auth_headers == [None]


def test_iterables_and_coordinates_are_json_arrays(bridge):
    server, url = bridge
    server.responses.extend([(200, '{"result": null}')] * 3)
    game = Game(url)
    game.select((1, 2))
    game.move((i for i in [3, 4]), 5, 6, waypoints=((x, x + 1) for x in [7, 9]))
    game.find_sites("farm", near=(10, 11))
    assert server.requests == [
        ("/api/select", {"unit_ids": [1, 2]}),
        ("/api/move", {"unit_ids": [3, 4], "x": 5, "y": 6, "waypoints": [[7, 8], [9, 10]]}),
        ("/api/find_sites", {"building": "farm", "limit": 5, "near_x": 10, "near_y": 11}),
    ]


def test_configured_timeout_passed_to_transport(bridge):
    server, url = bridge
    server.responses.append((200, '{"result": true}'))
    import urllib.request

    original = urllib.request.urlopen
    with patch("urllib.request.urlopen", wraps=original) as urlopen:
        assert Game.connect(url, timeout=2.5).state() is True
    assert urlopen.call_args.kwargs["timeout"] == 2.5
