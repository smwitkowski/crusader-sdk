# Siege commands

These commands build and crew siege engines and direct the specialist troops of an assault: laddermen and tunnelers. Engines are units and, once crewed, take the [military commands](military.md) (`move`, `attack`, `attack_building`, `attack_wall`) with their own unit ID. Unit lists follow the same rules as military commands: 1 to 500 distinct IDs of the player's own live units. Every command is queued for when time next moves and is refused after the match has ended or a tick budget is spent. IDs and coordinates in examples are illustrative.

## `build_siege`

Have engineers put up a siege tent and build an engine in it. [API reference](../api.md#build_siege).

- **Arguments:** `engineer_ids` are engineers; `engine` is `catapult`, `trebuchet`, `battering_ram`, `siege_tower`, `portable_shield` or `fire_ballista`; `(x, y)` is the top-left tile of the 3 × 3 tent. `find_sites(engine)` returns tent sites.
- **Cost:** gold from the game's cost table, charged when time next moves: 150 for every engine except the portable shield (5) in game version 1.41. The result's `gold` field is the amount.
- **Crew:** catapult 2, trebuchet 3, battering ram 4, siege tower 4, portable shield 1, fire ballista 2. The engineers who build the engine become its crew. Send at least the crew size: an engine built by fewer comes out uncrewed and takes no orders until `man` completes its crew. Extra engineers stay free.
- **Timing:** the tent appears when time moves; the engineers walk to it and build, and the engine appears on the tent's tile as a unit in `State.units` a few hundred ticks later (roughly 300 to 600).
- **Refused when:** the engine name is not recognized or the map's siege menu does not offer it; a listed unit is not an engineer; the tent site fails the map check or the game's placement check (for example too close to the enemy); or gold is short.
- **Afterwards:** a `build_refused` event is recorded if the tent could not be placed when time moved.

```python
engineers = [u["id"] for u in game.state()["units"] if u["owner"] == 1 and u["type"] == "engineer"][:2]
site = game.find_sites("catapult", limit=1, near=(220, 200))[0]
game.build_siege(engineers, "catapult", site["x"], site["y"])
# {"queued": "build_siege", "engine": "catapult", "x": 220, "y": 198, "gold": 150, "note": "..."}
```

See also: [siege engines](../reference/units.md#siege-engines); [refusals](../reference/errors.md#build_siege).


## `man`

Send engineers to crew an owned engine that is short of crew. [API reference](../api.md#man).

- **Arguments:** `engineer_ids` are free engineers; `engine_id` is an own siege engine or tower engine from `state()["units"]`.
- **Effect:** as many of the engineers as the engine still needs walk to it and board. Crew is all or nothing: an engine acts only with its full crew, so send enough engineers to complete it. The result's `crew_needed` is the number still missing when the order was given.
- **Tower engines:** a `mangonel` or `ballista` needs 2 engineers, who must be able to walk up to it: the tower has to be joined to a wall with stairs to the ground.
- **Refused when:** a listed unit is not an engineer; `engine_id` is not one of the player's engines; the engine already has its full crew; or the engineers cannot reach it.

```python
game.man([101, 102], 205)
# {"queued": "man", "engine_id": 205, "crew_needed": 2, "note": "they walk to it when game time next moves"}
```

See also: [`unman`](#unman); [refusals](../reference/errors.md#man).


## `unman`

Take the crew off an owned engine. [API reference](../api.md#unman).

- **Effect:** the engineers step off and are free for other work. The engine stays where it is and takes no orders until crewed again.
- **Refused when:** `engine_id` is not one of the player's engines, or it has no crew.

```python
game.unman(205)
# {"queued": "unman", "engine_id": 205}
```

See also: [`man`](#man); [refusals](../reference/errors.md#unman).


## `buy_ammo`

Buy 20 shots for a catapult or trebuchet for 10 stone. [API reference](../api.md#buy_ammo).

- **Applies to:** own catapults and trebuchets. A catapult starts with 20 shots and uses one per shot; `State.units` shows the remaining `ammo`.
- **Cost and timing:** 10 stone from the stockpile for 20 more shots, taken when time next moves.
- **Refused when:** the unit is not an own catapult or trebuchet, or the stockpile holds fewer than 10 stone.

```python
game.buy_ammo(205)
# {"queued": "buy_ammo", "engine_id": 205, "stone": 10, "shots": 20}
```

See also: [`attack_building`](military.md#attack_building); [refusals](../reference/errors.md#buy_ammo).


## `throw_cow`

Order a catapult or trebuchet to throw a cow at a tile. [API reference](../api.md#throw_cow).

- **Needs:** a crewed own catapult or trebuchet, and at least one cow. Cows are the cattle of the player's dairy farms; own catapults and trebuchets show the count as `cows` in state.
- **Effect:** the crew throws one cow at `(x, y)`; the carcass lies where it lands, and the cow count drops by one. The result's `cows` is the count when the order was given.
- **Refused when:** the unit is not an own catapult or trebuchet, it has no crew, the player has no cows, or the tile is off the map.

```python
game.throw_cow(205, 80, 70)
# {"queued": "throw_cow", "engine_id": 205, "x": 80, "y": 70, "cows": 3}
```

See also: [`buy_ammo`](#buy_ammo); [refusals](../reference/errors.md#throw_cow).


## `set_ladder`

Order laddermen to raise a ladder against an enemy wall tile. [API reference](../api.md#set_ladder).

- **Arguments:** `unit_ids` are laddermen; `(x, y)` is a wall tile (`^` on the map) of a player who is neither the controlled player nor an ally.
- **Effect:** the laddermen carry a ladder to the wall and raise it; soldiers ordered onto or over the wall can then climb there. Laddermen cannot fight.
- **Refused when:** a listed unit is not a ladderman, the tile is not a wall tile, or the wall is the player's own or an ally's.

```python
game.set_ladder([301], 80, 70)
# {"queued": "set_ladder", "units": 1, "x": 80, "y": 70}
```

See also: [`attack_wall`](military.md#attack_wall); [refusals](../reference/errors.md#set_ladder).


## `dig_tunnel`

Order tunnelers to start a tunnel at a tile. [API reference](../api.md#dig_tunnel).

- **Arguments:** `unit_ids` are tunnelers; `(x, y)` is the top-left tile of the tunnel entrance.
- **Effect:** a tunneler digs underground from the entrance toward the nearest enemy wall or building; when the tunnel collapses under it, that wall tile is destroyed or the building damaged.
- **Placement:** the game accepts an entrance only where an enemy-built wall or a small enemy tower lies within tunnelling distance; the walls that come with an enemy keep do not count. Against an enemy who has built no walls every spot is refused.
- **Refused when:** a listed unit is not a tunneler, the tile is off the map, or the game refuses the spot (often without stating a reason).

```python
game.dig_tunnel([302], 75, 70)
# {"queued": "dig_tunnel", "units": 1, "x": 75, "y": 70}
```

See also: [`attack_wall`](military.md#attack_wall); [refusals](../reference/errors.md#dig_tunnel).
