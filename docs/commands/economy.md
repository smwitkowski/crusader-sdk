# Economy commands

These commands manage construction, production, trade, and recruitment. Building placement uses the top-left tile of the footprint. Mutating commands can be refused after game over or when the tick budget is exhausted. IDs and coordinates below are illustrative.

## `build`

Place a building at the top-left tile of its footprint. [API reference](../api.md#build).

The driver checks terrain, mission menu and the game’s placement rules, then checks the live cost table for wood, stone and gold (also iron and pitch where supported). It queues placement for the next time game time moves; the response includes `queued`, `x`, `y`, and a note. Queued footprints count as occupied for later site searches. A later `build_refused` event is possible.

```python
game.build("woodcutter", 235, 230)
# On success, for the stated example and a suitable game state:
# {"queued": "woodcutter", "x": 235, "y": 230, "note": "placed when game time next moves"}
```

See also: [related reference](observe.md#find_sites); [refusals](../reference/errors.md#build).


## `demolish`

Demolish an owned building. [API reference](../api.md#demolish).

The ID must be an owned building and cannot be the keep. Removal occurs when game time next moves; part of the cost is refunded. A later `demolish_refused` event is possible.

```python
game.demolish(12)
# On success, for the stated example and a suitable game state:
# {"queued": "demolish", "building_id": 12, "type": "woodcutter", "note": "removed when game time next moves; part of its cost is refunded"}
```

See also: [related reference](observe.md#events); [refusals](../reference/errors.md#demolish).


## `set_tax`

Set tax from -3 to 8. The accepted level is -3 through 8. [API reference](../api.md#set_tax).

Negative levels are bribes; zero means no tax and positive levels increase tax. The driver returns the selected level in `tax`. Levels outside -3..8 are refused.

```python
game.set_tax(1)
# On success, for the stated example and a suitable game state:
# {"tax": 1}
```

See also: [related reference](observe.md#report); [refusals](../reference/errors.md#set_tax).


## `set_rations`

Set the ration level. Levels are none, half, normal, extra, and double. [API reference](../api.md#set_rations).

The driver returns the chosen level in `rations`; other names are refused.

```python
game.set_rations("normal")
# On success, for the stated example and a suitable game state:
# {"rations": "normal"}
```

See also: [related reference](observe.md#report); [refusals](../reference/errors.md#set_rations).


## `trade`

Buy or sell goods in multiples of five. Quantity must be a nonzero multiple of 5. Positive values buy; negative values sell. [API reference](../api.md#trade).

A market is required, and the good must be tradeable. The absolute quantity is at most 500. Purchases are queued in lots of five at the current per-five price, with gold reserved against other queued spending. Sales use game-sized lots: 5 below 50 in stock, 10 below 100, 20 below 200, otherwise 50; an exact requested sale that cannot be made in these lots is refused. The result reports queued quantity and gold; the trade executes when time next moves.

```python
game.trade("wood", 10)
```

On success the return has `queued`, `good`, `qty`, `gold`, and `note`; gold depends on the current game price.

See also: [related reference](../reference/goods.md); [refusals](../reference/errors.md#trade).


## `recruit`

Recruit soldiers or mercenaries. Count defaults to 1 and must be between 1 and 50. [API reference](../api.md#recruit).

The unit must be offered by the mission. Depending on unit, a barracks, mercenary post, cathedral or guild is required, along with idle peasants and sufficient gold; some troops also need weapons or horses. The driver reserves resources against other queued spending. The game takes gold and weapons when time next moves; barracks soldiers appear about 40 ticks later, after their peasants walk there. Mercenaries need no weapons. Recruitment is queued, not a guarantee of immediate appearance.

```python
game.recruit("archer", count=2)
```

On success the return has `queued`, `count`, `gold`, and `note`; the gold amount depends on unit and current price.

See also: [related reference](../reference/units.md); [refusals](../reference/errors.md#recruit).


## `repair`

Repair an owned tower or gatehouse. [API reference](../api.md#repair).

Only damaged owned towers and gatehouses have the repair button. The game calculates wood and stone cost from damage. Repair is refused if resources are short or enemies are nearby (15 tiles in a match against computer lords, 30 otherwise). It queues repair to full HP for the next time game time moves; the result includes wood and stone costs.

```python
game.repair(12)
```

On success the return has `queued`, `building_id`, `wood`, `stone`, and `note`; repair costs depend on damage.

See also: [related reference](observe.md#building_info); [refusals](../reference/errors.md#repair).


## `set_building_active`

Set whether buildings of this type are active. The setting applies to buildings of the specified type. [API reference](../api.md#set_building_active).

The ID identifies the type: **every owned building of that type** sleeps or wakes. Sleeping buildings stop work. Only types with a sleep button are accepted; the change takes effect when game time next moves.

```python
game.set_building_active(12, False)
```

On success the return has `queued`, `type`, `active`, and `note`; type depends on the chosen building.

See also: [related reference](observe.md#building_info); [refusals](../reference/errors.md#set_building_active).


## `set_workshop_product`

Set a workshop's product. Products are bows, crossbows, spears, pikes, maces, and swords. [API reference](../api.md#set_workshop_product).

The ID must be an owned fletcher, poleturner or blacksmith. Fletchers make bows or crossbows, poleturners spears or pikes, and blacksmiths maces or swords; a map can also disable a product. The queued selection applies from its next piece of work.

```python
game.set_workshop_product(12, "bows")
# On success, for the stated example and a suitable game state:
# {"queued": "set_workshop_product", "building_id": 12, "weapon": "bows", "note": "it makes this from its next piece of work"}
```

See also: [related reference](observe.md#building_info); [refusals](../reference/errors.md#set_workshop_product).


## `set_food_allowed`

Allow or disallow consumption of a food. [API reference](../api.md#set_food_allowed).

Requires an owned granary and a game mode where its food toggles are available. This changes the food consumption flag directly; it does not sell the food. Invalid food or a non-boolean flag is refused.

```python
game.set_food_allowed("bread", False)
# On success, for the stated example and a suitable game state:
# {"food": "bread", "allowed": False}
```

See also: [related reference](observe.md#report); [refusals](../reference/errors.md#set_food_allowed).

