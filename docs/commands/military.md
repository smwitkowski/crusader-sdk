# Military commands

These commands give orders to the player's units: movement, stance, patrols and attacks. Rules shared by all of them:

- **Unit IDs.** `unit_ids` is a list of 1 to 500 distinct IDs of the player's own live units, taken from `state()["units"]` where `owner` is 1. Soldiers, the lord and crewed siege engines all qualify. Although the client's signature allows `None`, the driver requires an explicit list. An ID that is not a live own unit refuses the whole command (`unit N is not one of your live soldiers`).
- **Grouping.** Each order selects exactly the listed units as one group and gives the group the order, as a selection and click in the game would. A new order replaces the group's previous one.
- **Timing.** Orders are queued and the units act when time next moves. Walking takes time: advance, then read positions from state.
- **Refusals.** Every command here is refused after the match has ended (`game over: ...`) or once a configured tick budget is spent.
- **Autonomy.** Units also fight enemies that come near without orders, according to their stance.

IDs and coordinates in examples are illustrative.

## `move`

Order units to walk to a tile, optionally continuing through waypoints. [API reference](../api.md#move).

- **Arguments:** `(x, y)` is the destination tile. `waypoints` is an optional list of 1 to 8 further `(x, y)` tiles, walked in order after `(x, y)`; the game keeps at most 9 markers in all. The units stay at the last marker.
- **Limits:** units stop short of a tile they cannot reach (water, walls, enclosed ground) without an error; check their positions after advancing. In a historical campaign the lord can only be sent back to his keep.
- **Returns:** `queued`, `units` (count) and either `x`, `y` or, with waypoints, `markers` (the full route).
- **Refused when:** a tile is off the map or not a pair of integers, or the marker count is outside 2 to 9 when waypoints are given.

```python
game.move([12, 13], 230, 225, waypoints=[(235, 225)])
# {"queued": "move", "units": 2, "markers": [[230, 225], [235, 225]], "note": "they walk the markers in order when game time next moves"}
```

See also: [`state`](observe.md#state); [refusals](../reference/errors.md#move).


## `set_stance`

Set how units react to nearby enemies. [API reference](../api.md#set_stance).

- **Stances:** `stand_ground` keeps units on their spot; `defensive` lets them engage enemies that come close; `aggressive` sends them after enemies that come near.
- **Effect:** applies to exactly the listed units, from when time next moves, until changed.
- **Refused when:** `stance` is not one of the three names.

```python
game.set_stance([12, 13], "defensive")
# {"queued": "stance", "units": 2, "stance": "defensive"}
```

See also: [`stop`](#stop); [refusals](../reference/errors.md#set_stance).


## `stop`

Stop units where they are and cancel their current order. [API reference](../api.md#stop).

- **Effect:** the units halt when time next moves. Their stance still governs how they react to enemies.

```python
game.stop([12, 13])
# {"queued": "stop", "units": 2, "note": "they stop when game time next moves"}
```

See also: [`move`](#move); [refusals](../reference/errors.md#stop).


## `disband`

Turn soldiers back into peasants. [API reference](../api.md#disband).

- **Effect:** the units become peasants and walk to the campfire, where they can take jobs or be recruited again. The gold, weapons and armor they cost are not refunded.
- **Refused when:** the list includes the lord (`your lord cannot be disbanded`).

```python
game.disband([12, 13])
# {"queued": "disband", "units": 2, "note": "they turn back into peasants when game time next moves"}
```

See also: [`recruit`](economy.md#recruit); [refusals](../reference/errors.md#disband).


## `patrol`

Order units to walk a route back and forth. [API reference](../api.md#patrol).

- **Arguments:** `points` is a list of 1 to 9 `(x, y)` tiles.
- **Effect:** the units walk the points in order and back, repeatedly, until they receive another order.
- **Refused when:** `points` is not a list of 1 to 9 integer pairs or a point is off the map. In a historical campaign the lord cannot patrol.

```python
game.patrol([12, 13], [(230, 225), (235, 225)])
# {"queued": "patrol", "units": 2, "points": [[230, 225], [235, 225]]}
```

See also: [`move`](#move); [refusals](../reference/errors.md#patrol).


## `attack_ground`

Order ranged units to keep shooting at a tile. [API reference](../api.md#attack_ground).

- **Units:** ranged soldiers only: archers, crossbowmen, slingers, horse archers, Arabian archers and fire throwers.
- **Effect:** the units shoot at the spot from where they stand, hitting whatever enters it, and pay less attention to enemies elsewhere than idle ranged units do. The order lasts until replaced.
- **Refused when:** a listed unit is not ranged, or the tile is off the map.

```python
game.attack_ground([12, 13], 240, 230)
# {"queued": "attack_ground", "units": 2, "x": 240, "y": 230}
```

See also: [`attack`](#attack); [refusals](../reference/errors.md#attack_ground).


## `attack_wall`

Order units to attack an enemy wall tile. [API reference](../api.md#attack_wall).

- **Arguments:** `(x, y)` must be a wall tile (`^` on the map) owned by a player who is neither the controlled player nor an ally.
- **Effect:** the units walk to the wall and attack that tile. A siege tower given this order rolls to the wall and docks, letting soldiers climb onto the wall over it.
- **Refused when:** the tile is not a wall tile, or the wall is the player's own or an ally's.

```python
game.attack_wall([12, 13], 240, 230)
# {"queued": "attack_wall", "units": 2, "x": 240, "y": 230}
```

See also: [`attack_building`](#attack_building); [`set_ladder`](siege.md#set_ladder); [refusals](../reference/errors.md#attack_wall).


## `attack`

Order units to attack one enemy unit. [API reference](../api.md#attack).

- **Arguments:** `target_id` is the ID of a live unit of another, non-allied player from `state()["units"]`. An enemy lord's ID is in `state()["enemy"]["lords"]`.
- **Effect:** the units pursue and attack the target. When it dies they fall back on their stance; give a new order for the next target.
- **Refused when:** the target is not a live enemy unit of a recognized type, or belongs to an ally.

```python
game.attack([12, 13], target_id=42)
# {"queued": "attack", "units": 2, "target_id": 42, "note": "they attack when game time next moves"}
```

See also: [`state`](observe.md#state); [refusals](../reference/errors.md#attack).


## `attack_building`

Order units to attack one enemy building. [API reference](../api.md#attack_building).

- **Arguments:** `building_id` is the `id` of an entry in `state()["enemy"]["buildings"]`.
- **Effect:** the units walk to the building and attack it until it is destroyed. A keep cannot be damaged. Catapults and trebuchets shoot buildings from range; a battering ram walks up and batters.
- **Refused when:** the ID is not a building of another, non-allied player.

```python
game.attack_building([12, 13], building_id=42)
# {"queued": "attack", "units": 2, "building_id": 42, "note": "they attack when game time next moves"}
```

See also: [`state`](observe.md#state); [refusals](../reference/errors.md#attack_building).
