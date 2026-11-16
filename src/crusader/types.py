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
    """In-game calendar date."""

    month: int
    year: int


class Building(TypedDict):
    """One of your buildings in `state()['buildings']`."""

    id: int
    type: str
    x: int
    y: int


class EnemyBuilding(Building):
    """An enemy building in `state()['enemy']['buildings']`."""

    owner: int
    hp: int
    max_hp: int


class _UnitOptional(TypedDict, total=False):
    ammo: int
    cows: int


class Unit(_UnitOptional):
    """A unit in `state()['units']`; `ammo` and `cows` appear only for units that carry them."""

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
    """A player's lord; `id`, position and `hp` may be absent."""

    owner: int
    alive: bool


class Enemy(TypedDict):
    """Enemy lords and buildings, when the game mode has an enemy."""

    lords: list[Lord]
    buildings: list[EnemyBuilding]


class AllyRequest(TypedDict):
    """A good and quantity an ally asked you for."""

    good: str
    qty: int


class AllyAttack(TypedDict):
    """An ally's attack order on a player."""

    attack: int


class AllyPanel(TypedDict):
    """One ally's request and current order, as the allies panel shows them."""

    player: int
    request: AllyRequest | None
    order: AllyAttack | str | None


class _AlliesOptional(TypedDict, total=False):
    panel: list[AllyPanel]


class Allies(_AlliesOptional):
    """Your allied players and their lords, plus the allies panel when present."""

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
    """A valid top-left tile for a building, from `find_sites`."""

    x: int
    y: int


class _EventOptional(TypedDict, total=False):
    tick: int
    month: int
    message: str


class Event(_EventOptional):
    """One entry of the game event log, read with `events(since)`."""

    seq: int
    type: str


class AdvanceResult(TypedDict):
    """What `advance` returns after time moves."""

    tick: int
    ticks_left: int
    game_over: str | None
    events: list[Event]
    next_since: int


# The bridge has many command-specific response shapes.
CommandResult = dict[str, object]
ReportResult = dict[str, object]
BuildingInfo = dict[str, object]
