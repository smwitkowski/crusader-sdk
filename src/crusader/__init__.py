"""Client for Stronghold Crusader through the Crusader bridge."""

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterable, Sequence
from typing import Any, Literal

from .types import AdvanceResult, BuildingInfo, CommandResult, Event, ReportResult, Site, State

__version__ = "0.1.0"
__all__ = ["CrusaderError", "Game"]


class CrusaderError(Exception):
    """The bridge rejected a command."""


class Game:
    """Send commands to a Crusader bridge."""

    def __init__(self, url: str, timeout: float = 600, token: str | None = None) -> None:
        """Set the bridge URL, request timeout, and optional bearer token."""
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.token = token if token is not None else os.environ.get("CRUSADER_TOKEN")

    @classmethod
    def connect(cls, url: str | None = None, timeout: float = 600, token: str | None = None) -> "Game":
        """Connect using explicit settings or CRUSADER_URL and CRUSADER_TOKEN."""
        return cls(url or os.environ.get("CRUSADER_URL", "http://127.0.0.1:8000"), timeout=timeout, token=token)

    def _call(self, cmd: str, **args: Any) -> Any:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(
            f"{self.url}/api/{cmd}",
            data=json.dumps(args).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                out = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                message = json.load(exc).get("error", str(exc))
            except (ValueError, UnicodeDecodeError):
                message = str(exc)
            raise CrusaderError(message) from None
        if "error" in out:
            raise CrusaderError(out["error"])
        return out["result"]

    def state(self) -> State:
        """Return the current visible game state."""
        return self._call("state")

    def map(self, x0: int = 0, y0: int = 0, x1: int = 399, y1: int = 399) -> str:
        """Return the inclusive tile rectangle as text."""
        return self._call("ascii_map", x0=x0, y0=y0, x1=x1, y1=y1)

    def find_sites(self, building: str, limit: int = 5, near: tuple[int, int] | None = None) -> list[Site]:
        """Find valid building sites, optionally near a tile."""
        coords = near or (None, None)
        return self._call("find_sites", building=building, limit=limit, near_x=coords[0], near_y=coords[1])

    def look(self, x: int, y: int) -> CommandResult:
        """Centre the camera on a tile; always refused by the game driver."""
        return self._call("look", x=x, y=y)

    def select(self, unit_ids: Iterable[int]) -> CommandResult:
        """Select owned soldiers by ID."""
        return self._call("select", unit_ids=list(unit_ids))

    def events(self, since: int = 0) -> list[Event]:
        """Return events from list offset since onward."""
        return self._call("events", since=since)

    def build(self, building: str, x: int, y: int) -> CommandResult:
        """Place a building at the top-left tile of its footprint."""
        return self._call("build", building=building, x=x, y=y)

    def demolish(self, building_id: int) -> CommandResult:
        """Demolish an owned building."""
        return self._call("demolish", building_id=building_id)

    def set_tax(self, level: int) -> CommandResult:
        """Set tax from -3 to 8."""
        return self._call("set_tax", level=level)

    def set_rations(self, level: Literal["none", "half", "normal", "extra", "double"]) -> CommandResult:
        """Set the ration level."""
        return self._call("set_rations", level=level)

    def trade(self, good: str, qty: int) -> CommandResult:
        """Buy or sell goods in multiples of five."""
        return self._call("trade", good=good, qty=qty)

    def recruit(self, unit: str, count: int = 1) -> CommandResult:
        """Recruit soldiers or mercenaries."""
        return self._call("recruit", unit=unit, count=count)

    def move(
        self, unit_ids: Iterable[int] | None, x: int, y: int, waypoints: Iterable[Sequence[int]] | None = None
    ) -> CommandResult:
        """Order units to a tile and optional subsequent waypoints."""
        ids = None if unit_ids is None else list(unit_ids)
        if waypoints is None:
            return self._call("move", unit_ids=ids, x=x, y=y)
        return self._call("move", unit_ids=ids, x=x, y=y, waypoints=[list(p) for p in waypoints])

    def set_stance(
        self, unit_ids: Iterable[int] | None, stance: Literal["stand_ground", "defensive", "aggressive"]
    ) -> CommandResult:
        """Set unit stance to stand_ground, defensive, or aggressive."""
        return self._call("set_stance", unit_ids=None if unit_ids is None else list(unit_ids), stance=stance)

    def stop(self, unit_ids: Iterable[int] | None) -> CommandResult:
        """Stop the selected units."""
        return self._call("stop", unit_ids=None if unit_ids is None else list(unit_ids))

    def disband(self, unit_ids: Iterable[int] | None) -> CommandResult:
        """Return soldiers to the campfire as peasants."""
        return self._call("disband", unit_ids=None if unit_ids is None else list(unit_ids))

    def patrol(self, unit_ids: Iterable[int] | None, points: Iterable[Sequence[int]]) -> CommandResult:
        """Order units to patrol one to nine points."""
        return self._call(
            "patrol", unit_ids=None if unit_ids is None else list(unit_ids), points=[list(p) for p in points]
        )

    def attack_ground(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult:
        """Order ranged units to attack a tile."""
        return self._call("attack_ground", unit_ids=None if unit_ids is None else list(unit_ids), x=x, y=y)

    def attack_wall(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult:
        """Order units to attack an enemy wall tile."""
        return self._call("attack_wall", unit_ids=None if unit_ids is None else list(unit_ids), x=x, y=y)

    def attack(self, unit_ids: Iterable[int] | None, target_id: int) -> CommandResult:
        """Order units to attack an enemy unit."""
        return self._call("attack", unit_ids=None if unit_ids is None else list(unit_ids), target_id=target_id)

    def attack_building(self, unit_ids: Iterable[int] | None, building_id: int) -> CommandResult:
        """Order units to attack an enemy building."""
        return self._call(
            "attack_building", unit_ids=None if unit_ids is None else list(unit_ids), building_id=building_id
        )

    def build_siege(
        self,
        engineer_ids: Iterable[int] | None,
        engine: Literal["catapult", "trebuchet", "battering_ram", "siege_tower", "portable_shield", "fire_ballista"],
        x: int,
        y: int,
    ) -> CommandResult:
        """Construct a siege engine at the tent's top-left tile."""
        return self._call(
            "build_siege", engineer_ids=None if engineer_ids is None else list(engineer_ids), engine=engine, x=x, y=y
        )

    def man(self, engineer_ids: Iterable[int] | None, engine_id: int) -> CommandResult:
        """Assign engineers to crew an engine."""
        return self._call("man", engineer_ids=None if engineer_ids is None else list(engineer_ids), engine_id=engine_id)

    def unman(self, engine_id: int) -> CommandResult:
        """Remove an engine's crew."""
        return self._call("unman", engine_id=engine_id)

    def buy_ammo(self, engine_id: int) -> CommandResult:
        """Buy ammunition for a catapult or trebuchet."""
        return self._call("buy_ammo", engine_id=engine_id)

    def throw_cow(self, engine_id: int, x: int, y: int) -> CommandResult:
        """Order a catapult or trebuchet to throw a cow at a tile."""
        return self._call("throw_cow", engine_id=engine_id, x=x, y=y)

    def set_ladder(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult:
        """Order laddermen to raise ladders against a wall."""
        return self._call("set_ladder", unit_ids=None if unit_ids is None else list(unit_ids), x=x, y=y)

    def dig_tunnel(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult:
        """Order tunnelers to dig from a tile."""
        return self._call("dig_tunnel", unit_ids=None if unit_ids is None else list(unit_ids), x=x, y=y)

    def repair(self, building_id: int) -> CommandResult:
        """Repair an owned tower or gatehouse."""
        return self._call("repair", building_id=building_id)

    def set_building_active(self, building_id: int, active: bool) -> CommandResult:
        """Set whether buildings of this type are active."""
        return self._call("set_building_active", building_id=building_id, active=active)

    def set_workshop_product(
        self, building_id: int, weapon: Literal["bows", "crossbows", "spears", "pikes", "maces", "swords"]
    ) -> CommandResult:
        """Set a workshop's product."""
        return self._call("set_workshop_product", building_id=building_id, weapon=weapon)

    def set_food_allowed(self, food: str, allowed: bool) -> CommandResult:
        """Allow or disallow consumption of a food."""
        return self._call("set_food_allowed", food=food, allowed=allowed)

    def set_gate(self, building_id: int, open: bool) -> CommandResult:
        """Open or close a gatehouse or drawbridge."""
        return self._call("set_gate", building_id=building_id, open=open)

    def plan_moat(self, x1: int, y1: int, x2: int, y2: int, dig: bool = True) -> CommandResult:
        """Mark or remove a moat plan along a line."""
        return self._call("plan_moat", x1=x1, y1=y1, x2=x2, y2=y2, dig=dig)

    def dig_moat(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult:
        """Order units to dig a planned moat tile."""
        return self._call("dig_moat", unit_ids=None if unit_ids is None else list(unit_ids), x=x, y=y)

    def fill_moat(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult:
        """Order units to fill an enemy moat tile."""
        return self._call("fill_moat", unit_ids=None if unit_ids is None else list(unit_ids), x=x, y=y)

    def delete_wall(self, x: int, y: int) -> CommandResult:
        """Delete an owned wall tile."""
        return self._call("delete_wall", x=x, y=y)

    def light_pitch(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult:
        """Order ranged units to ignite a pitch ditch."""
        return self._call("light_pitch", unit_ids=None if unit_ids is None else list(unit_ids), x=x, y=y)

    def oil_duty(self, engineer_ids: Iterable[int] | None, smelter_id: int) -> CommandResult:
        """Assign engineers to an oil smelter."""
        return self._call(
            "oil_duty", engineer_ids=None if engineer_ids is None else list(engineer_ids), smelter_id=smelter_id
        )

    def pour_oil(self, engineer_ids: Iterable[int] | None, x: int, y: int) -> CommandResult:
        """Order engineers to pour oil; currently refused by the game driver."""
        return self._call("pour_oil", engineer_ids=None if engineer_ids is None else list(engineer_ids), x=x, y=y)

    def report(
        self,
        page: Literal["popularity", "fear", "religion", "army", "food", "population", "stores", "weapons", "merit"],
    ) -> ReportResult:
        """Return a page of the scribe's book."""
        return self._call("report", page=page)

    def building_info(self, building_id: int) -> BuildingInfo:
        """Return the panel information for an owned building."""
        return self._call("building_info", building_id=building_id)

    def ally_order(
        self, ally: int, order: Literal["attack", "defend", "cancel"], target: int | None = None
    ) -> CommandResult:
        """Ask an ally to attack, defend, or cancel orders."""
        return self._call("ally_order", ally=ally, order=order, target=target)

    def ally_send_goods(self, ally: int, good: str, qty: int) -> CommandResult:
        """Send goods to an ally."""
        return self._call("ally_send_goods", ally=ally, good=good, qty=qty)

    def ally_request_goods(self, ally: int, good: str, qty: int) -> CommandResult:
        """Request goods from an ally."""
        return self._call("ally_request_goods", ally=ally, good=good, qty=qty)

    def ally_answer(self, ally: int, accept: bool) -> CommandResult:
        """Accept or refuse an ally's request."""
        return self._call("ally_answer", ally=ally, accept=accept)

    def build_wall(self, x1: int, y1: int, x2: int, y2: int, kind: str = "wall") -> CommandResult:
        """Build a straight line of wall or stairs."""
        return self._call("build_wall", x1=x1, y1=y1, x2=x2, y2=y2, kind=kind)

    def advance(self, ticks: int) -> AdvanceResult:
        """Run the game for 1 to 3000 ticks."""
        return self._call("advance", ticks=ticks)
