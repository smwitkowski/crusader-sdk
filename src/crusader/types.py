"""Types for values returned by the Crusader bridge.

These describe JSON responses; they do not validate responses at runtime.
"""

from typing import TypedDict


class RawState(TypedDict):
    """Direct game-memory snapshot returned by the bridge's read_state."""

    tick: int
    paused: bool
    month: int
    year: int
    tax: int
    rations: int
    popularity: float
    population: int
    housing: int
    stock: dict[str, int]


class Date(TypedDict):
    month: int
    year: int


class Building(TypedDict):
    id: int
    type: str
    x: int
    y: int


class EnemyBuilding(Building):
    owner: int
    hp: int
    max_hp: int


class _UnitOptional(TypedDict, total=False):
    ammo: int
    cows: int


class Unit(_UnitOptional):
    id: int
    type: str
    owner: int
    x: int
    y: int
    hp: int


class _LordOptional(TypedDict, total=False):
    id: int
    x: int
    y: int
    hp: int


class Lord(_LordOptional):
    owner: int
    alive: bool


class Enemy(TypedDict):
    lords: list[Lord]
    buildings: list[EnemyBuilding]


class AllyRequest(TypedDict):
    good: str
    qty: int


class AllyAttack(TypedDict):
    attack: int


class AllyPanel(TypedDict):
    player: int
    request: AllyRequest | None
    order: AllyAttack | str | None


class _AlliesOptional(TypedDict, total=False):
    panel: list[AllyPanel]


class Allies(_AlliesOptional):
    players: list[int]
    lords: list[Lord]


class _StateOptional(TypedDict, total=False):
    enemy: Enemy
    mission: str
    allies: Allies


class State(_StateOptional):
    """Visible game state, including mode-specific fields when available."""

    tick: int
    month: int
    ticks_per_month: int
    ticks_left: int
    game_over: str | None
    gold: int
    popularity: float
    population: int
    housing: int
    tax: int
    rations: str | int
    stock: dict[str, int]
    date: Date
    buildings: list[Building]
    idle_peasants: int
    units: list[Unit]
    lord_alive: bool


class Site(TypedDict):
    x: int
    y: int


class _EventOptional(TypedDict, total=False):
    tick: int
    month: int
    message: str


class Event(_EventOptional):
    seq: int
    type: str


class AdvanceResult(TypedDict):
    tick: int
    ticks_left: int
    game_over: str | None
    events: list[Event]
    next_since: int


# The bridge has many command-specific response shapes.
CommandResult = dict[str, object]
ReportResult = dict[str, object]
BuildingInfo = dict[str, object]
