"""HTTP and MCP bridge for an injected Crusader game backend."""

from __future__ import annotations

import asyncio
import hmac
import inspect
import json
import re
import threading
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from crusader.commands import COMMANDS

MAX_BODY = 64 * 1024


def _authority(value: str) -> tuple[str, int | None] | None:
    """Parse a Host-style authority without accepting URL delimiters or userinfo."""
    if not re.fullmatch(r"(?:\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9.-]+)(?::[0-9]+)?", value):
        return None
    try:
        parsed = urlsplit("http://" + value)
        port = parsed.port
        if value.endswith(":") or (port is not None and port == 0):
            return None
        hostname = parsed.hostname
        return (hostname.lower(), port) if hostname is not None else None
    except ValueError:
        return None


def _loopback_origin(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or parsed.path or parsed.query or parsed.fragment:
            return False
        # Require the original spelling to contain nothing outside the parsed origin.
        if value != f"{parsed.scheme}://{parsed.netloc}":
            return False
        authority = _authority(parsed.netloc)
        return authority is not None and authority[0] in {"localhost", "127.0.0.1", "::1"}
    except ValueError:
        return False


class GameBackend(Protocol):
    """Commands supplied by an injected game backend."""

    def state(self) -> Any: ...

    def ascii_map(self) -> str: ...

    def find_sites(self, building: Any, limit: Any = 5, near: Any = None) -> Any: ...

    def look(self, x: Any, y: Any) -> Any: ...

    def select(self, unit_ids: Any) -> Any: ...

    def events(self, since: Any = 0) -> Any: ...

    def build(self, building: Any, x: Any, y: Any) -> Any: ...

    def demolish(self, building_id: Any) -> Any: ...

    def set_tax(self, level: Any) -> Any: ...

    def set_rations(self, level: Any) -> Any: ...

    def trade(self, good: Any, qty: Any) -> Any: ...

    def recruit(self, unit: Any, count: Any = 1) -> Any: ...

    def move(self, unit_ids: Any, x: Any, y: Any, waypoints: Any = None) -> Any: ...

    def set_stance(self, unit_ids: Any, stance: Any) -> Any: ...

    def stop(self, unit_ids: Any) -> Any: ...

    def disband(self, unit_ids: Any) -> Any: ...

    def patrol(self, unit_ids: Any, points: Any) -> Any: ...

    def attack_ground(self, unit_ids: Any, x: Any, y: Any) -> Any: ...

    def attack_wall(self, unit_ids: Any, x: Any, y: Any) -> Any: ...

    def attack(self, unit_ids: Any, target_id: Any) -> Any: ...

    def attack_building(self, unit_ids: Any, building_id: Any) -> Any: ...

    def build_siege(self, engineer_ids: Any, engine: Any, x: Any, y: Any) -> Any: ...

    def man(self, engineer_ids: Any, engine_id: Any) -> Any: ...

    def unman(self, engine_id: Any) -> Any: ...

    def buy_ammo(self, engine_id: Any) -> Any: ...

    def throw_cow(self, engine_id: Any, x: Any, y: Any) -> Any: ...

    def set_ladder(self, unit_ids: Any, x: Any, y: Any) -> Any: ...

    def dig_tunnel(self, unit_ids: Any, x: Any, y: Any) -> Any: ...

    def repair(self, building_id: Any) -> Any: ...

    def set_building_active(self, building_id: Any, active: Any) -> Any: ...

    def set_workshop_product(self, building_id: Any, weapon: Any) -> Any: ...

    def set_food_allowed(self, food: Any, allowed: Any) -> Any: ...

    def set_gate(self, building_id: Any, open: Any) -> Any: ...

    def plan_moat(self, x1: Any, y1: Any, x2: Any, y2: Any, dig: Any = True) -> Any: ...

    def dig_moat(self, unit_ids: Any, x: Any, y: Any) -> Any: ...

    def fill_moat(self, unit_ids: Any, x: Any, y: Any) -> Any: ...

    def delete_wall(self, x: Any, y: Any) -> Any: ...

    def light_pitch(self, unit_ids: Any, x: Any, y: Any) -> Any: ...

    def oil_duty(self, engineer_ids: Any, smelter_id: Any) -> Any: ...

    def pour_oil(self, engineer_ids: Any, x: Any, y: Any) -> Any: ...

    def report(self, page: Any) -> Any: ...

    def building_info(self, building_id: Any) -> Any: ...

    def ally_order(self, ally: Any, order: Any, target: Any = None) -> Any: ...

    def ally_send_goods(self, ally: Any, good: Any, qty: Any) -> Any: ...

    def ally_request_goods(self, ally: Any, good: Any, qty: Any) -> Any: ...

    def ally_answer(self, ally: Any, accept: Any) -> Any: ...

    def build_wall(self, x1: Any, y1: Any, x2: Any, y2: Any, kind: Any = "wall") -> Any: ...

    def advance(self, ticks: Any) -> Any: ...


def create_app(
    game: GameBackend,
    *,
    token: str | None = None,
    log_path: str | Path | None = None,
    slow_threshold: float = 5.0,
    allow_hosts: list[str] | None = None,
):
    """Create a bridge around a game instance without creating a game at import time."""
    if slow_threshold <= 0:
        raise ValueError("slow_threshold must be positive")
    allowed_hosts = {_authority(host) for host in (allow_hosts or [])}
    if None in allowed_hosts:
        raise ValueError("invalid allowed host")
    lock = threading.RLock()
    mcp = MCPServer("crusader")
    commands = {item["command"]: item for item in COMMANDS.values()}

    def invoke_inner(name: str, args: dict[str, Any]) -> Any:
        spec = commands[name]
        allowed = {}
        for param in spec["params"]:
            for wire in param.get("wire_names", [param["name"]]):
                allowed[wire] = param
        unknown = set(args) - allowed.keys()
        if unknown:
            raise ValueError(f"unknown arguments: {', '.join(sorted(unknown))}")
        for key, param in allowed.items():
            if key not in args:
                if "default" not in param:
                    raise ValueError(f"missing argument: {key}")
                continue
            value = args[key]
            typ = param["type"]
            if value is None and ("None" in typ or key in param.get("wire_names", [])):
                continue
            expected = (
                int
                if key in param.get("wire_names", [])
                else (int if typ in ("int", "int | None") else str if typ == "str" else bool if typ == "bool" else list)
            )
            if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
                raise ValueError(f"invalid argument: {key}")
            if isinstance(value, list):
                point_list = "tuple[int, int]" in typ
                valid = (
                    all(
                        isinstance(point, list) and len(point) == 2 and all(type(v) is int for v in point)
                        for point in value
                    )
                    if point_list
                    else all(type(v) is int for v in value)
                )
                if not valid:
                    raise ValueError(f"invalid argument: {key}")
        ranges = {("set_tax", "level"): (-3, 8), ("recruit", "count"): (1, 50), ("advance", "ticks"): (1, 3000)}
        for (command, key), (minimum, maximum) in ranges.items():
            if name == command and key in args and not minimum <= args[key] <= maximum:
                raise ValueError(f"{key} must be {minimum}..{maximum}")
        for key, param in allowed.items():
            constraint = param.get("constraints", "")
            choices = constraint.split(", ")
            if (
                key in args
                and args[key] is not None
                and len(choices) > 1
                and all(choice.isidentifier() for choice in choices)
                and args[key] not in choices
            ):
                raise ValueError(f"invalid argument: {key}")
        if name in ("trade", "ally_send_goods", "ally_request_goods") and "qty" in args:
            qty = args["qty"]
            if qty % 5 or qty == 0 or (name != "trade" and qty < 0):
                raise ValueError("qty must be a valid multiple of 5")
        if name == "patrol" and "points" in args and not 1 <= len(args["points"]) <= 9:
            raise ValueError("points must contain 1..9 points")
        if name == "move" and args.get("waypoints") is not None and len(args["waypoints"]) > 8:
            raise ValueError("at most 8 waypoints are allowed")
        with lock:
            fn = getattr(game, name, None)
            if fn is None:
                raise ValueError(f"command unavailable: {name}")
            call_args = dict(args)
            if name == "find_sites":
                nx, ny = call_args.pop("near_x", None), call_args.pop("near_y", None)
                if (nx is None) != (ny is None):
                    raise ValueError("near_x and near_y must be supplied together")
                call_args["near"] = (nx, ny) if nx is not None else None
            if name == "ascii_map":
                sig = inspect.signature(fn)
                if not sig.parameters:
                    x0, y0 = call_args.get("x0", 0), call_args.get("y0", 0)
                    x1, y1 = call_args.get("x1", 399), call_args.get("y1", 399)
                    result = "\n".join(row[max(0, x0) : x1 + 1] for row in fn().split("\n")[max(0, y0) : y1 + 1])
                else:
                    result = fn(**call_args)
            else:
                result = fn(**call_args)
            return result

    def invoke(name: str, args: dict[str, Any]) -> Any:
        with lock:
            entry: dict[str, Any] = {"cmd": name, "args": args}
            try:
                result = invoke_inner(name, args)
                entry["result"] = result
                return result
            except Exception as exc:
                entry["error"] = str(exc)
                raise
            finally:
                tick = getattr(game, "tick", None)
                if isinstance(tick, int):
                    entry["tick"] = tick
                if log_path is not None:
                    with Path(log_path).open("a", encoding="utf-8") as out:
                        out.write(json.dumps(entry) + "\n")

    def make_tool(name, spec):
        def tool(**kwargs):
            return invoke(name, kwargs)

        params = []
        for p in spec["params"]:
            for wire in p.get("wire_names", [p["name"]]):
                typ = p["type"]
                annotation = (
                    int
                    if wire in p.get("wire_names", [])
                    else (
                        int
                        if typ in ("int", "int | None")
                        else str
                        if typ == "str"
                        else bool
                        if typ == "bool"
                        else list
                    )
                )
                if annotation is list:
                    annotation = list[list[int]] if "tuple[int, int]" in typ else list[int]
                default = p.get("default", inspect.Parameter.empty)
                if "None" in typ:
                    annotation = annotation | None
                params.append(
                    inspect.Parameter(wire, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=annotation)
                )
        tool.__signature__ = inspect.Signature(params)
        tool.__name__ = name
        tool.__doc__ = spec["summary"]
        return tool

    for name, spec in commands.items():
        mcp.tool(name=name)(make_tool(name, spec))

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request):
        return JSONResponse({"ok": True})

    @mcp.custom_route("/api/{cmd}", methods=["POST"])
    async def api(request: Request):
        name = request.path_params["cmd"]
        if name not in commands:
            return JSONResponse({"error": "unknown command"}, status_code=404)
        try:
            raw = await request.body()
            args = json.loads(raw)
            if not isinstance(args, dict):
                raise ValueError("body must be a JSON object")
        except (ValueError, UnicodeDecodeError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

        def call():
            try:
                return 200, {"result": invoke(name, args)}
            except (ValueError, TypeError) as exc:
                return 400, {"error": str(exc)}
            except Exception as exc:
                return 400, {"error": str(exc)}

        task = asyncio.create_task(asyncio.to_thread(call))
        done, _ = await asyncio.wait({task}, timeout=slow_threshold)
        if done:
            status, payload = task.result()
            return JSONResponse(payload, status_code=status)

        async def stream():
            while not task.done():
                yield b" "
                await asyncio.wait({task}, timeout=slow_threshold)
            yield json.dumps(task.result()[1]).encode()

        return StreamingResponse(stream(), media_type="application/json")

    from mcp.server.transport_security import TransportSecuritySettings

    app = mcp.streamable_http_app(
        stateless_http=True,
        max_request_body_size=MAX_BODY,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    async def guard(request: Request, call_next):
        hosts = request.headers.getlist("host")
        host = _authority(hosts[0]) if len(hosts) == 1 else None
        if host is None or (
            host[0] not in {"localhost", "127.0.0.1", "::1"}
            and host not in allowed_hosts
            and (host[0], None) not in allowed_hosts
        ):
            return JSONResponse({"error": "invalid host"}, status_code=421)
        origins = request.headers.getlist("origin")
        if len(origins) > 1 or (origins and not _loopback_origin(origins[0])):
            return JSONResponse({"error": "invalid origin"}, status_code=403)
        if request.method == "POST":
            types = request.headers.getlist("content-type")
            if len(types) != 1 or types[0].split(";", 1)[0].strip().lower() != "application/json":
                return JSONResponse({"error": "invalid content-type"}, status_code=415)
        if token is not None and request.url.path != "/health":
            header = request.headers.get("authorization", "")
            if not hmac.compare_digest(header.encode(), ("Bearer " + token).encode()):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) < 0 or int(length) > MAX_BODY:
                    return JSONResponse({"error": "body too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"error": "invalid content-length"}, status_code=400)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY:
                return JSONResponse({"error": "body too large"}, status_code=413)
        request._body = bytes(body)
        return await call_next(request)

    from starlette.middleware.base import BaseHTTPMiddleware

    app.add_middleware(BaseHTTPMiddleware, dispatch=guard)
    app.state.commands = frozenset(commands)
    return app


def replay(game: GameBackend, log_path: str | Path) -> None:
    """Reissue commands from a bridge JSONL log on another backend."""
    with Path(log_path).open(encoding="utf-8") as source:
        for line in source:
            entry = json.loads(line)
            if "error" in entry:
                continue
            args = dict(entry["args"])
            name = entry["cmd"]
            if name == "find_sites":
                x, y = args.pop("near_x", None), args.pop("near_y", None)
                args["near"] = (x, y) if x is not None and y is not None else None
            fn = getattr(game, name)
            if name == "ascii_map" and not inspect.signature(fn).parameters:
                fn()
            else:
                fn(**args)


def main() -> None:
    """Run a bridge with the real game or an explicit backend factory."""
    import argparse
    import importlib
    import os

    import uvicorn

    parser = argparse.ArgumentParser(description="Run the Crusader bridge")
    parser.add_argument(
        "--backend", default=os.environ.get("CRUSADER_BACKEND"), help="backend factory as module:callable"
    )
    parser.add_argument(
        "--match",
        default=os.environ.get("CRUSADER_MATCH", "castle_builder:1"),
        help="castle_builder:seed, skirmish:map:ai:seed, or load:save",
    )
    parser.add_argument("--game-dir", default=os.environ.get("CRUSADER_GAME_DIR"))
    parser.add_argument("--process-name", default=os.environ.get("CRUSADER_PROCESS_NAME"))
    parser.add_argument("--host", default=os.environ.get("CRUSADER_HOST", "127.0.0.1"))
    parser.add_argument("--allow-host", action="append", default=[], help="allow an additional Host header")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CRUSADER_PORT", "8000")))
    parser.add_argument("--token", default=os.environ.get("CRUSADER_TOKEN"))
    parser.add_argument("--log", default=os.environ.get("CRUSADER_LOG"))
    args = parser.parse_args()
    if args.backend is not None:
        if ":" not in args.backend or not all(args.backend.split(":", 1)):
            parser.error("--backend must be module:callable")
        module, name = args.backend.split(":", 1)
        backend = getattr(importlib.import_module(module), name)()
    else:
        from crusader.bridge.game import CastleBuilder, Game, LoadSave, Skirmish

        parts = args.match.split(":")
        try:
            if parts[0] == "castle_builder" and len(parts) == 2:
                match = CastleBuilder(int(parts[1]))
            elif parts[0] == "skirmish" and len(parts) == 4 and all(parts[1:]):
                match = Skirmish(parts[1], parts[2], int(parts[3]))
            elif parts[0] == "load" and len(parts) == 2 and parts[1]:
                match = LoadSave(parts[1])
            else:
                raise ValueError
        except ValueError:
            parser.error("--match must be castle_builder:seed, skirmish:map:ai:seed, or load:save")
        backend = Game(match, game_dir=args.game_dir, process_lookup=args.process_name)
    uvicorn.run(
        create_app(backend, token=args.token, log_path=args.log, allow_hosts=args.allow_host),
        host=args.host,
        port=args.port,
    )
