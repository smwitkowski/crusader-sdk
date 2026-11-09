# Military commands

These commands issue orders to units, including movement, stance, patrol, and attacks. Pass 1–500 distinct IDs of your live soldiers, invalid IDs are refused. Although the client accepts `None`, the current real driver requires explicit IDs. Orders are queued and take effect as game time moves. Game over and exhausted tick budgets can also cause refusals. IDs and coordinates in examples are illustrative.

## `move`

Order units to a tile and optional subsequent waypoints. The initial destination may be followed by at most 8 waypoints. [API reference](../api.md#move).

Movement is queued; units set off when game time next moves. Waypoints are walked in order and may be unavailable in the current task. When specified, at least one waypoint is required. In historical campaigns the lord can only move back near his keep or attack.

```python
game.move([12, 13], 230, 225, waypoints=[(235, 225)])
# On success, for the stated example and a suitable game state:
# {"queued": "move", "units": 2, "markers": [[230, 225], [235, 225]], "note": "they walk the markers in order when game time next moves"}
```

See also: [related reference](observe.md#state); [refusals](../reference/errors.md#move).


## `set_stance`

Set unit stance to stand_ground, defensive, or aggressive. Stances are stand_ground, defensive, and aggressive. [API reference](../api.md#set_stance).

Queues a stance for exactly the specified units. `stand_ground` holds position; `aggressive` pursues nearby enemies. Other stance names are refused.

```python
game.set_stance([12, 13], "defensive")
# On success, for the stated example and a suitable game state:
# {"queued": "stance", "units": 2, "stance": "defensive"}
```

See also: [related reference](#stop); [refusals](../reference/errors.md#set_stance).


## `stop`

Stop the selected units. [API reference](../api.md#stop).

Queues a stop instruction; units stop when game time next moves.

```python
game.stop([12, 13])
# On success, for the stated example and a suitable game state:
# {"queued": "stop", "units": 2, "note": "they stop when game time next moves"}
```

See also: [related reference](#move); [refusals](../reference/errors.md#stop).


## `disband`

Return soldiers to the campfire as peasants. [API reference](../api.md#disband).

Queues disbanding; your lord cannot be disbanded. Nothing is refunded.

```python
game.disband([12, 13])
# On success, for the stated example and a suitable game state:
# {"queued": "disband", "units": 2, "note": "they turn back into peasants when game time next moves"}
```

See also: [related reference](economy.md#recruit); [refusals](../reference/errors.md#disband).


## `patrol`

Order units to patrol one to nine points. The route contains 1 to 9 points. [API reference](../api.md#patrol).

Units walk the points in order and back repeatedly until another order. Points must be on the map. The historical-campaign lord movement restriction also applies to patrols.

```python
game.patrol([12, 13], [(230, 225), (235, 225)])
# On success, for the stated example and a suitable game state:
# {"queued": "patrol", "units": 2, "points": [[230, 225], [235, 225]]}
```

See also: [related reference](#move); [refusals](../reference/errors.md#patrol).


## `attack_ground`

Order ranged units to attack a tile. [API reference](../api.md#attack_ground).

Only ranged soldiers can use this order: archers, crossbowmen, slingers, horse archers, Arabian archers and fire throwers. Units keep shooting at the spot from where they stand and pay less attention to other enemies than idle archers. The target must be on the map.

```python
game.attack_ground([12, 13], 240, 230)
# On success, for the stated example and a suitable game state:
# {"queued": "attack_ground", "units": 2, "x": 240, "y": 230}
```

See also: [related reference](#attack); [refusals](../reference/errors.md#attack_ground).


## `attack_wall`

Order units to attack an enemy wall tile. [API reference](../api.md#attack_wall).

The target tile must be an enemy wall; a non-wall or non-enemy wall is refused.

```python
game.attack_wall([12, 13], 240, 230)
# On success, for the stated example and a suitable game state:
# {"queued": "attack_wall", "units": 2, "x": 240, "y": 230}
```

See also: [related reference](#attack_building); [refusals](../reference/errors.md#attack_wall).


## `attack`

Order units to attack an enemy unit. [API reference](../api.md#attack).

The target must be a live enemy soldier; allied units are refused. Obtain target IDs from visible state.

```python
game.attack([12, 13], target_id=42)
# On success, for the stated example and a suitable game state:
# {"queued": "attack", "units": 2, "target_id": 42, "note": "they attack when game time next moves"}
```

See also: [related reference](observe.md#state); [refusals](../reference/errors.md#attack).


## `attack_building`

Order units to attack an enemy building. [API reference](../api.md#attack_building).

The target ID must identify an enemy building. Inspect visible enemy buildings in state first.

```python
game.attack_building([12, 13], building_id=42)
# On success, for the stated example and a suitable game state:
# {"queued": "attack", "units": 2, "building_id": 42, "note": "they attack when game time next moves"}
```

See also: [related reference](observe.md#state); [refusals](../reference/errors.md#attack_building).

