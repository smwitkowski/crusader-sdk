# API reference

Generated from the client and command metadata. Examples are illustrative; game state and IDs determine whether commands succeed.

<a id="state"></a>
## state

Return the current visible game state.

Returns `State`; use its owned units and buildings to choose IDs for orders. Enemy information is limited to visible state. Unit IDs can be reused after death, so read them fresh before ordering.

```python
game.state()
```

The returned `State` includes `tick`, `stock`, `units`, and `buildings`; values depend on the running game.

See also: [related reference](reference/state.md); [refusals](reference/errors.md#state).

```python
state(self) -> State
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| — | — | — | — |

**Returns:** `State`

**Refusals:** See [errors for state](reference/errors.md#state); bridge-wide validation can also reject a request.

<a id="map"></a>
## map

Return the inclusive tile rectangle as text. The default rectangle runs from (0, 0) through (399, 399), inclusive.

Returns a string. Invalid rectangles are refused; coordinates include both endpoints.

```python
game.map(220, 220, 240, 240)
```

The return is a newline-separated string; the result contents depend on the terrain.

See also: [related reference](reference/map-legend.md); [refusals](reference/errors.md#map).

```python
map(self, x0: int=0, y0: int=0, x1: int=399, y1: int=399) -> str
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `x0` | `int` | `0` | 0..399; x0 <= x1 |
| `y0` | `int` | `0` | 0..399; y0 <= y1 |
| `x1` | `int` | `399` | 0..399; x1 >= x0 |
| `y1` | `int` | `399` | 0..399; y1 >= y0 |

**Returns:** `str`

**Refusals:** See [errors for map](reference/errors.md#map); bridge-wide validation can also reject a request.

<a id="find_sites"></a>
## find_sites

Find valid building sites, optionally near a tile. The optional near tile narrows the search around a location; the default limit is 5.

Returns `list[Site]`. `limit` must be 1–50; unknown or unavailable buildings are refused. Without `near`, the driver searches around the mission keep, otherwise (235, 230). Queued builds are treated as occupied, even before the map shows them. A site does not guarantee that you can afford a build.

```python
game.find_sites("woodcutter", limit=3, near=(235, 230))
```

Each returned site has `x` and `y`; the list may be empty.

See also: [related reference](commands/economy.md#build); [refusals](reference/errors.md#find_sites).

```python
find_sites(self, building: str, limit: int=5, near: tuple[int, int] | None=None) -> list[Site]
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building` | `str` | `required` | Building or siege engine placement name (not ID); woodcutter, stockpile, hovel, quarry, wheat_farm, hops_farm, apple_orchard, dairy_farm, mill, bakery, brewery, market, hunters_post, granary, armory, barracks, inn, chapel, church, well, fletcher, poleturner, blacksmith, armourer, tanner, mercenary_post, iron_mine, lookout_tower, perimeter_tower, defense_turret, square_tower, round_tower, gatehouse, large_gatehouse, engineers_guild, tunnelers_guild, stables, cathedral, apothecary, ox_tether, pitch_rig, maypole, dancing_bear, small_garden, medium_garden, large_garden, statue, shrine, gallows, cess_pit, stocks, burning_stake, dungeon, stretching_rack, gibbet, chopping_block, dunking_stool, gatehouse_turned, large_gatehouse_turned, drawbridge, killing_pit, pitch_ditch, dog_cage, oil_smelter, water_pot, keep, catapult, trebuchet, battering_ram, siege_tower, portable_shield, fire_ballista; availability depends on driver level and mission |
| `limit` | `int` | `5` | 1..50 |
| `near` | `tuple[int, int] \| None` | `None` | — |

**Returns:** `list[Site]`

**Refusals:** See [errors for find_sites](reference/errors.md#find_sites); bridge-wide validation can also reject a request.

<a id="look"></a>
## look

Centre the camera on a tile and return its visible area.

The current real backend refuses camera control; do not rely on this command to reveal an area.

```python
game.look(235, 230)
```

See also: [related reference](how-it-works.md); [refusals](reference/errors.md#look).

```python
look(self, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `x` | `int` | `required` | — |
| `y` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for look](reference/errors.md#look); bridge-wide validation can also reject a request.

<a id="select"></a>
## select

Select owned soldiers by ID.

Pass 1–500 distinct IDs of your live soldiers. Invalid, enemy, or dead units are refused. Selection changes the game selection.

```python
game.select([12, 13])
```

On success the return has a `tribe` field; its value is assigned by the game.

See also: [related reference](commands/military.md#move); [refusals](reference/errors.md#select).

```python
select(self, unit_ids: Iterable[int]) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int]` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for select](reference/errors.md#select); bridge-wide validation can also reject a request.

<a id="events"></a>
## events

Return events with sequence numbers at or after since. The since value is inclusive and defaults to 0.

The driver treats `since` as an inclusive offset into its event list, from 0 through the current event count. An invalid offset is refused. Use `next_since` from `advance()` to fetch newer events; this is not a tick number. Event fields vary; do not assume optional fields are present.

```python
game.events(since=0)
```

If there are no events at or after the offset, the return is `[]`.

See also: [related reference](reference/events.md); [refusals](reference/errors.md#events).

```python
events(self, since: int=0) -> list[Event]
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `since` | `int` | `0` | 0..current event count |

**Returns:** `list[Event]`

**Refusals:** See [errors for events](reference/errors.md#events); bridge-wide validation can also reject a request.

<a id="build"></a>
## build

Place a building at the top-left tile of its footprint.

The driver checks terrain, mission menu and the game’s placement rules, then checks the live cost table for wood, stone and gold (also iron and pitch where supported). It queues placement for the next time game time moves; the response includes `queued`, `x`, `y`, and a note. Queued footprints count as occupied for later site searches. A later `build_refused` event is possible.

```python
game.build("woodcutter", 235, 230)
# On success, for the stated example and a suitable game state:
# {"queued": "woodcutter", "x": 235, "y": 230, "note": "placed when game time next moves"}
```

See also: [related reference](commands/observe.md#find_sites); [refusals](reference/errors.md#build).

```python
build(self, building: str, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building` | `str` | `required` | Building placement name (not ID); woodcutter, stockpile, hovel, quarry, wheat_farm, hops_farm, apple_orchard, dairy_farm, mill, bakery, brewery, market, hunters_post, granary, armory, barracks, inn, chapel, church, well, fletcher, poleturner, blacksmith, armourer, tanner, mercenary_post, iron_mine, lookout_tower, perimeter_tower, defense_turret, square_tower, round_tower, gatehouse, large_gatehouse, engineers_guild, tunnelers_guild, stables, cathedral, apothecary, ox_tether, pitch_rig, maypole, dancing_bear, small_garden, medium_garden, large_garden, statue, shrine, gallows, cess_pit, stocks, burning_stake, dungeon, stretching_rack, gibbet, chopping_block, dunking_stool, gatehouse_turned, large_gatehouse_turned, drawbridge, killing_pit, pitch_ditch, dog_cage, oil_smelter, water_pot, flag_1, flag_2, flag_3, flag_4, heads, brazier, mangonel, ballista; availability depends on driver level and mission |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for build](reference/errors.md#build); bridge-wide validation can also reject a request.

<a id="demolish"></a>
## demolish

Demolish an owned building.

The ID must be an owned building and cannot be the keep. Removal occurs when game time next moves; part of the cost is refunded. A later `demolish_refused` event is possible.

```python
game.demolish(12)
# On success, for the stated example and a suitable game state:
# {"queued": "demolish", "building_id": 12, "type": "woodcutter", "note": "removed when game time next moves; part of its cost is refunded"}
```

See also: [related reference](commands/observe.md#events); [refusals](reference/errors.md#demolish).

```python
demolish(self, building_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for demolish](reference/errors.md#demolish); bridge-wide validation can also reject a request.

<a id="set_tax"></a>
## set_tax

Set tax from -3 to 8. The accepted level is -3 through 8.

Negative levels are bribes; zero means no tax and positive levels increase tax. The driver returns the selected level in `tax`. Levels outside -3..8 are refused.

```python
game.set_tax(1)
# On success, for the stated example and a suitable game state:
# {"tax": 1}
```

See also: [related reference](commands/observe.md#report); [refusals](reference/errors.md#set_tax).

```python
set_tax(self, level: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `level` | `int` | `required` | -3..8 |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_tax](reference/errors.md#set_tax); bridge-wide validation can also reject a request.

<a id="set_rations"></a>
## set_rations

Set the ration level. Levels are none, half, normal, extra, and double.

The driver returns the chosen level in `rations`; other names are refused.

```python
game.set_rations("normal")
# On success, for the stated example and a suitable game state:
# {"rations": "normal"}
```

See also: [related reference](commands/observe.md#report); [refusals](reference/errors.md#set_rations).

```python
set_rations(self, level: Literal['none', 'half', 'normal', 'extra', 'double']) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `level` | `str` | `required` | none, half, normal, extra, double |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_rations](reference/errors.md#set_rations); bridge-wide validation can also reject a request.

<a id="trade"></a>
## trade

Buy or sell goods in multiples of five. Quantity must be a nonzero multiple of 5. Positive values buy; negative values sell.

A market is required, and the good must be tradeable. The absolute quantity is at most 500. Purchases are queued in lots of five at the current per-five price, with gold reserved against other queued spending. Sales use game-sized lots: 5 below 50 in stock, 10 below 100, 20 below 200, otherwise 50; an exact requested sale that cannot be made in these lots is refused. The result reports queued quantity and gold; the trade executes when time next moves.

```python
game.trade("wood", 10)
```

On success the return has `queued`, `good`, `qty`, `gold`, and `note`; gold depends on the current game price.

See also: [related reference](reference/goods.md); [refusals](reference/errors.md#trade).

```python
trade(self, good: str, qty: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `good` | `str` | `required` | wood, hops, stone, iron, pitch, wheat, bread, cheese, meat, apples, ale, flour, bows, crossbows, spears, pikes, maces, swords, leather_armor, metal_armor; tradeability depends on game state |
| `qty` | `int` | `required` | nonzero multiple of 5; positive buys, negative sells |

**Returns:** `CommandResult`

**Refusals:** See [errors for trade](reference/errors.md#trade); bridge-wide validation can also reject a request.

<a id="recruit"></a>
## recruit

Recruit soldiers or mercenaries. Count defaults to 1 and must be between 1 and 50.

The unit must be offered by the mission. Depending on unit, a barracks, mercenary post, cathedral or guild is required, along with idle peasants and sufficient gold; some troops also need weapons or horses. The driver reserves resources against other queued spending. The game takes gold and weapons when time next moves; barracks soldiers appear about 40 ticks later, after their peasants walk there. Mercenaries need no weapons. Recruitment is queued, not a guarantee of immediate appearance.

```python
game.recruit("archer", count=2)
```

On success the return has `queued`, `count`, `gold`, and `note`; the gold amount depends on unit and current price.

See also: [related reference](reference/units.md); [refusals](reference/errors.md#recruit).

```python
recruit(self, unit: str, count: int=1) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit` | `str` | `required` | Unit name (not ID); archer, crossbowman, spearman, pikeman, maceman, swordsman, knight, arabian_archer, slave, slinger, assassin, horse_archer, arabian_swordsman, fire_thrower, engineer, laddermen, tunneler, monk; availability depends on driver level and mission |
| `count` | `int` | `1` | 1..50 |

**Returns:** `CommandResult`

**Refusals:** See [errors for recruit](reference/errors.md#recruit); bridge-wide validation can also reject a request.

<a id="move"></a>
## move

Order units to a tile and optional subsequent waypoints. The initial destination may be followed by at most 8 waypoints.

Movement is queued; units set off when game time next moves. Waypoints are walked in order and may be unavailable in the current task. When specified, at least one waypoint is required. In historical campaigns the lord can only move back near his keep or attack.

```python
game.move([12, 13], 230, 225, waypoints=[(235, 225)])
# On success, for the stated example and a suitable game state:
# {"queued": "move", "units": 2, "markers": [[230, 225], [235, 225]], "note": "they walk the markers in order when game time next moves"}
```

See also: [related reference](commands/observe.md#state); [refusals](reference/errors.md#move).

```python
move(self, unit_ids: Iterable[int] | None, x: int, y: int, waypoints: Iterable[Sequence[int]] | None=None) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `waypoints` | `Iterable[tuple[int, int]] \| None` | `None` | 1..8 points if provided; each must be a valid map tile (coordinates 0..399) |

**Returns:** `CommandResult`

**Refusals:** See [errors for move](reference/errors.md#move); bridge-wide validation can also reject a request.

<a id="set_stance"></a>
## set_stance

Set unit stance to stand_ground, defensive, or aggressive. Stances are stand_ground, defensive, and aggressive.

Queues a stance for exactly the specified units. `stand_ground` holds position; `aggressive` pursues nearby enemies. Other stance names are refused.

```python
game.set_stance([12, 13], "defensive")
# On success, for the stated example and a suitable game state:
# {"queued": "stance", "units": 2, "stance": "defensive"}
```

See also: [related reference](#stop); [refusals](reference/errors.md#set_stance).

```python
set_stance(self, unit_ids: Iterable[int] | None, stance: Literal['stand_ground', 'defensive', 'aggressive']) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `stance` | `str` | `required` | stand_ground, defensive, aggressive |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_stance](reference/errors.md#set_stance); bridge-wide validation can also reject a request.

<a id="stop"></a>
## stop

Stop the selected units.

Queues a stop instruction; units stop when game time next moves.

```python
game.stop([12, 13])
# On success, for the stated example and a suitable game state:
# {"queued": "stop", "units": 2, "note": "they stop when game time next moves"}
```

See also: [related reference](#move); [refusals](reference/errors.md#stop).

```python
stop(self, unit_ids: Iterable[int] | None) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for stop](reference/errors.md#stop); bridge-wide validation can also reject a request.

<a id="disband"></a>
## disband

Return soldiers to the campfire as peasants.

Queues disbanding; your lord cannot be disbanded. Nothing is refunded.

```python
game.disband([12, 13])
# On success, for the stated example and a suitable game state:
# {"queued": "disband", "units": 2, "note": "they turn back into peasants when game time next moves"}
```

See also: [related reference](commands/economy.md#recruit); [refusals](reference/errors.md#disband).

```python
disband(self, unit_ids: Iterable[int] | None) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for disband](reference/errors.md#disband); bridge-wide validation can also reject a request.

<a id="patrol"></a>
## patrol

Order units to patrol one to nine points. The route contains 1 to 9 points.

Units walk the points in order and back repeatedly until another order. Points must be on the map. The historical-campaign lord movement restriction also applies to patrols.

```python
game.patrol([12, 13], [(230, 225), (235, 225)])
# On success, for the stated example and a suitable game state:
# {"queued": "patrol", "units": 2, "points": [[230, 225], [235, 225]]}
```

See also: [related reference](#move); [refusals](reference/errors.md#patrol).

```python
patrol(self, unit_ids: Iterable[int] | None, points: Iterable[Sequence[int]]) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `points` | `Iterable[tuple[int, int]]` | `required` | 1..9 points; each point must be a valid map tile (coordinates 0..399) |

**Returns:** `CommandResult`

**Refusals:** See [errors for patrol](reference/errors.md#patrol); bridge-wide validation can also reject a request.

<a id="attack_ground"></a>
## attack_ground

Order ranged units to attack a tile.

Only ranged soldiers can use this order: archers, crossbowmen, slingers, horse archers, Arabian archers and fire throwers. Units keep shooting at the spot from where they stand and pay less attention to other enemies than idle archers. The target must be on the map.

```python
game.attack_ground([12, 13], 240, 230)
# On success, for the stated example and a suitable game state:
# {"queued": "attack_ground", "units": 2, "x": 240, "y": 230}
```

See also: [related reference](#attack); [refusals](reference/errors.md#attack_ground).

```python
attack_ground(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for attack_ground](reference/errors.md#attack_ground); bridge-wide validation can also reject a request.

<a id="attack_wall"></a>
## attack_wall

Order units to attack an enemy wall tile.

The target tile must be an enemy wall; a non-wall or non-enemy wall is refused.

```python
game.attack_wall([12, 13], 240, 230)
# On success, for the stated example and a suitable game state:
# {"queued": "attack_wall", "units": 2, "x": 240, "y": 230}
```

See also: [related reference](#attack_building); [refusals](reference/errors.md#attack_wall).

```python
attack_wall(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for attack_wall](reference/errors.md#attack_wall); bridge-wide validation can also reject a request.

<a id="attack"></a>
## attack

Order units to attack an enemy unit.

The target must be a live enemy soldier; allied units are refused. Obtain target IDs from visible state.

```python
game.attack([12, 13], target_id=42)
# On success, for the stated example and a suitable game state:
# {"queued": "attack", "units": 2, "target_id": 42, "note": "they attack when game time next moves"}
```

See also: [related reference](commands/observe.md#state); [refusals](reference/errors.md#attack).

```python
attack(self, unit_ids: Iterable[int] | None, target_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `target_id` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for attack](reference/errors.md#attack); bridge-wide validation can also reject a request.

<a id="attack_building"></a>
## attack_building

Order units to attack an enemy building.

The target ID must identify an enemy building. Inspect visible enemy buildings in state first.

```python
game.attack_building([12, 13], building_id=42)
# On success, for the stated example and a suitable game state:
# {"queued": "attack", "units": 2, "building_id": 42, "note": "they attack when game time next moves"}
```

See also: [related reference](commands/observe.md#state); [refusals](reference/errors.md#attack_building).

```python
attack_building(self, unit_ids: Iterable[int] | None, building_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `building_id` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for attack_building](reference/errors.md#attack_building); bridge-wide validation can also reject a request.

<a id="build_siege"></a>
## build_siege

The 3×3 tent uses `(x, y)` as its top-left tile. Available engines are `catapult`, `trebuchet`, `battering_ram`, `siege_tower`, `portable_shield` and `fire_ballista`. Engineers walk there, build and crew the engine. Gold is charged when time moves; the driver also checks wood and stone. The mission menu, placement or resources may cause refusal. The result reports gold and crew needed; the engine later appears in `state()["units"]`.

```python
game.build_siege([101, 102], "catapult", 45, 60)
```

See also: and [refusals](reference/errors.md#build_siege).

```python
build_siege(self, engineer_ids: Iterable[int] | None, engine: Literal['catapult', 'trebuchet', 'battering_ram', 'siege_tower', 'portable_shield', 'fire_ballista'], x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engineer_ids` | `Iterable[int] \| None` | `required` | — |
| `engine` | `str` | `required` | catapult, trebuchet, battering_ram, siege_tower, portable_shield, fire_ballista |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for build_siege](reference/errors.md#build_siege); bridge-wide validation can also reject a request.

<a id="man"></a>
## man

Selected engineers walk to an owned engine and fill its vacant crew slots. The result reports `crew_needed`; a full engine is refused. At level 5 the driver checks reachability: tower engines need access via a wall and stairs.

```python
game.man([101, 102], 205)
```

See also: and [refusals](reference/errors.md#man).

```python
man(self, engineer_ids: Iterable[int] | None, engine_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engineer_ids` | `Iterable[int] \| None` | `required` | — |
| `engine_id` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for man](reference/errors.md#man); bridge-wide validation can also reject a request.

<a id="unman"></a>
## unman

Order the crew of an owned, crewed engine to step off. An engine short of its full crew takes no orders; an engine with no crew is refused.

```python
game.unman(205)
```

See also: and [refusals](reference/errors.md#unman).

```python
unman(self, engine_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engine_id` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for unman](reference/errors.md#unman); bridge-wide validation can also reject a request.

<a id="buy_ammo"></a>
## buy_ammo

A catapult or trebuchet buys 20 shots for 10 stone. Other engine types and insufficient stone are refused. The queued result reports `stone` and `shots`.

```python
game.buy_ammo(205)
# {"queued": "buy_ammo", "engine_id": 205, "stone": 10, "shots": 20}
```

See also: and [refusals](reference/errors.md#buy_ammo).

```python
buy_ammo(self, engine_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engine_id` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for buy_ammo](reference/errors.md#buy_ammo); bridge-wide validation can also reject a request.

<a id="throw_cow"></a>
## throw_cow

A crewed catapult or trebuchet throws a dairy farm cow at an on-map tile; the carcass remains where it lands. The driver refuses other engines, no crew or no cows. Returned `cows` is the count at ordering time, not proof of impact.

```python
game.throw_cow(205, 80, 70)
```

See also: and [refusals](reference/errors.md#throw_cow).

```python
throw_cow(self, engine_id: int, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engine_id` | `int` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for throw_cow](reference/errors.md#throw_cow); bridge-wide validation can also reject a request.

<a id="set_ladder"></a>
## set_ladder

Select owned laddermen and an enemy wall tile. They carry and raise a ladder for soldiers to climb. Own and allied walls, non-wall tiles and other unit types are refused.

```python
game.set_ladder([301], 80, 70)
```

See also: and [refusals](reference/errors.md#set_ladder).

```python
set_ladder(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_ladder](reference/errors.md#set_ladder); bridge-wide validation can also reject a request.

<a id="dig_tunnel"></a>
## dig_tunnel

Select owned tunnelers and an on-map entrance tile. A tunneler digs toward the nearest enemy building; the eventual collapse damages that building. The game may refuse placement.

```python
game.dig_tunnel([302], 75, 70)
```

See also: and [refusals](reference/errors.md#dig_tunnel).

```python
dig_tunnel(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for dig_tunnel](reference/errors.md#dig_tunnel); bridge-wide validation can also reject a request.

<a id="repair"></a>
## repair

Repair an owned tower or gatehouse.

Only damaged owned towers and gatehouses have the repair button. The game calculates wood and stone cost from damage. Repair is refused if resources are short or enemies are nearby (15 tiles in a match against computer lords, 30 otherwise). It queues repair to full HP for the next time game time moves; the result includes wood and stone costs.

```python
game.repair(12)
```

On success the return has `queued`, `building_id`, `wood`, `stone`, and `note`; repair costs depend on damage.

See also: [related reference](commands/observe.md#building_info); [refusals](reference/errors.md#repair).

```python
repair(self, building_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for repair](reference/errors.md#repair); bridge-wide validation can also reject a request.

<a id="set_building_active"></a>
## set_building_active

Set whether buildings of this type are active. The setting applies to buildings of the specified type.

The ID identifies the type: **every owned building of that type** sleeps or wakes. Sleeping buildings stop work. Only types with a sleep button are accepted; the change takes effect when game time next moves.

```python
game.set_building_active(12, False)
```

On success the return has `queued`, `type`, `active`, and `note`; type depends on the chosen building.

See also: [related reference](commands/observe.md#building_info); [refusals](reference/errors.md#set_building_active).

```python
set_building_active(self, building_id: int, active: bool) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | — |
| `active` | `bool` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_building_active](reference/errors.md#set_building_active); bridge-wide validation can also reject a request.

<a id="set_workshop_product"></a>
## set_workshop_product

Set a workshop's product. Products are bows, crossbows, spears, pikes, maces, and swords.

The ID must be an owned fletcher, poleturner or blacksmith. Fletchers make bows or crossbows, poleturners spears or pikes, and blacksmiths maces or swords; a map can also disable a product. The queued selection applies from its next piece of work.

```python
game.set_workshop_product(12, "bows")
# On success, for the stated example and a suitable game state:
# {"queued": "set_workshop_product", "building_id": 12, "weapon": "bows", "note": "it makes this from its next piece of work"}
```

See also: [related reference](commands/observe.md#building_info); [refusals](reference/errors.md#set_workshop_product).

```python
set_workshop_product(self, building_id: int, weapon: Literal['bows', 'crossbows', 'spears', 'pikes', 'maces', 'swords']) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | — |
| `weapon` | `str` | `required` | fletcher: bows, crossbows; poleturner: spears, pikes; blacksmith: maces, swords |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_workshop_product](reference/errors.md#set_workshop_product); bridge-wide validation can also reject a request.

<a id="set_food_allowed"></a>
## set_food_allowed

Allow or disallow consumption of a food.

Requires an owned granary and a game mode where its food toggles are available. This changes the food consumption flag directly; it does not sell the food. Invalid food or a non-boolean flag is refused.

```python
game.set_food_allowed("bread", False)
# On success, for the stated example and a suitable game state:
# {"food": "bread", "allowed": False}
```

See also: [related reference](commands/observe.md#report); [refusals](reference/errors.md#set_food_allowed).

```python
set_food_allowed(self, food: str, allowed: bool) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `food` | `str` | `required` | apples, cheese, meat, bread |
| `allowed` | `bool` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_food_allowed](reference/errors.md#set_food_allowed); bridge-wide validation can also reject a request.

<a id="set_gate"></a>
## set_gate

Set an owned gatehouse or drawbridge with a Boolean `open`. The change is queued for the next time movement. A closed gate or raised drawbridge stops everyone, including your own units.

```python
game.set_gate(42, False)
```

See also: and [refusals](reference/errors.md#set_gate).

```python
set_gate(self, building_id: int, open: bool) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | — |
| `open` | `bool` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_gate](reference/errors.md#set_gate); bridge-wide validation can also reject a request.

<a id="plan_moat"></a>
## plan_moat

Mark a horizontal or vertical line of at most 100 tiles, or remove a plan with `dig=False`. Planning costs nothing. The game marks acceptable land with a two-tile brush; returned `tiles` is line length, not accepted tile count. Marking occurs when time moves; use `dig_moat` to excavate.

```python
game.plan_moat(40, 50, 50, 50)
```

See also: and [refusals](reference/errors.md#plan_moat).

```python
plan_moat(self, x1: int, y1: int, x2: int, y2: int, dig: bool=True) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `x1` | `int` | `required` | 0..399; valid map tile; line must be straight and at most 100 tiles |
| `y1` | `int` | `required` | 0..399; valid map tile; line must be straight and at most 100 tiles |
| `x2` | `int` | `required` | 0..399; valid map tile; line must be straight and at most 100 tiles |
| `y2` | `int` | `required` | 0..399; valid map tile; line must be straight and at most 100 tiles |
| `dig` | `bool` | `True` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for plan_moat](reference/errors.md#plan_moat); bridge-wide validation can also reject a request.

<a id="dig_moat"></a>
## dig_moat

Order eligible owned diggers to a tile of your existing moat plan. They dig the plan tile by tile; dug moat blocks ground units. Other units and unplanned tiles are refused.

```python
game.dig_moat([101], 40, 50)
# {"queued": "dig_moat", "units": 1, "x": 40, "y": 50}
```

See also: and [refusals](reference/errors.md#dig_moat).

```python
dig_moat(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for dig_moat](reference/errors.md#dig_moat); bridge-wide validation can also reject a request.

<a id="fill_moat"></a>
## fill_moat

Order eligible owned diggers to fill an enemy dug moat tile with earth. Your own or allied moat, an undug plan, and non-diggers are refused. Filling takes unit action.

```python
game.fill_moat([101], 80, 70)
```

See also: and [refusals](reference/errors.md#fill_moat).

```python
fill_moat(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for fill_moat](reference/errors.md#fill_moat); bridge-wide validation can also reject a request.

<a id="delete_wall"></a>
## delete_wall

Queue removal of one owned wall tile. Removal occurs when time moves; the result notes a half-stone refund, which the game halves again for a low wall. This does not remove moat plans or pitch; use `plan_moat(..., dig=False)` for a plan.

```python
game.delete_wall(40, 50)
```

See also: and [refusals](reference/errors.md#delete_wall).

```python
delete_wall(self, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for delete_wall](reference/errors.md#delete_wall); bridge-wide validation can also reject a request.

<a id="light_pitch"></a>
## light_pitch

Select archers or Arabian archers and a friendly-team pitch ditch in reach. The first selected unit must be within three tiles of a lit friendly brazier; range is checked from that unit. They shoot burning arrows to ignite the ditch.

```python
game.light_pitch([101], 45, 50)
```

See also: and [refusals](reference/errors.md#light_pitch).

```python
light_pitch(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for light_pitch](reference/errors.md#light_pitch); bridge-wide validation can also reject a request.

<a id="oil_duty"></a>
## oil_duty

Assign owned engineers to an owned oil smelter. They work it and can receive oil pots. Other unit or building types are refused. The separate `pour_oil` command is currently unavailable.

```python
game.oil_duty([101], 42)
```

See also: and [refusals](reference/errors.md#oil_duty).

```python
oil_duty(self, engineer_ids: Iterable[int] | None, smelter_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engineer_ids` | `Iterable[int] \| None` | `required` | — |
| `smelter_id` | `int` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for oil_duty](reference/errors.md#oil_duty); bridge-wide validation can also reject a request.

<a id="pour_oil"></a>
## pour_oil

The driver currently refuses this order: the game’s pour click has not been reproduced, and a direct ground order was observed to leave a carrier waiting. It first checks for engineers and at least one carried pot, so those errors may appear instead. Use `oil_duty` to assign engineers, but do not rely on this command to pour.

```python
game.pour_oil([101], 45, 50)  # currently refused
```

See also: and [refusals](reference/errors.md#pour_oil).

```python
pour_oil(self, engineer_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engineer_ids` | `Iterable[int] \| None` | `required` | — |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for pour_oil](reference/errors.md#pour_oil); bridge-wide validation can also reject a request.

<a id="report"></a>
## report

Return a page of the scribe's book. Pages: popularity, fear, religion, army, food, population, stores, weapons, merit.

Returns a report page; availability and fields depend on the page and game state.

```python
game.report("food")
```

Returned fields vary by page: for example the army page returns `troops` and `fear_bonus`.

See also: [related reference](reference/state.md); [refusals](reference/errors.md#report).

```python
report(self, page: Literal['popularity', 'fear', 'religion', 'army', 'food', 'population', 'stores', 'weapons', 'merit']) -> ReportResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `page` | `str` | `required` | popularity, fear, religion, army, food, population, stores, weapons, merit |

**Returns:** `ReportResult`

**Refusals:** See [errors for report](reference/errors.md#report); bridge-wide validation can also reject a request.

<a id="building_info"></a>
## building_info

Return the panel information for an owned building.

Pass an owned building ID from state; the panel data depends on building type. An invalid or non-owned ID is refused.

```python
game.building_info(12)
```

Returned fields include `id` and `type`, with additional fields according to the panel.

See also: [related reference](reference/state.md); [refusals](reference/errors.md#building_info).

```python
building_info(self, building_id: int) -> BuildingInfo
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | — |

**Returns:** `BuildingInfo`

**Refusals:** See [errors for building_info](reference/errors.md#building_info); bridge-wide validation can also reject a request.

<a id="ally_order"></a>
## ally_order

Ask a living ally to `"attack"`, `"defend"` or `"cancel"`. Attack requires the player ID of a living enemy lord; the other orders must omit `target`. The ally answers when time moves and may decline; inspect `state()["allies"]["panel"]` for the resulting order.

```python
game.ally_order(2, "attack", target=3)
```

See also: and [refusals](reference/errors.md#ally_order).

```python
ally_order(self, ally: int, order: Literal['attack', 'defend', 'cancel'], target: int | None=None) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ally` | `int` | `required` | — |
| `order` | `str` | `required` | attack, defend, cancel |
| `target` | `int \| None` | `None` | enemy player ID with a living lord for attack; None for defend or cancel |

**Returns:** `CommandResult`

**Refusals:** See [errors for ally_order](reference/errors.md#ally_order); bridge-wide validation can also reject a request.

<a id="ally_send_goods"></a>
## ally_send_goods

Send a positive multiple of five to a living ally. You must have the requested amount; non-gold goods also need a suitable ally store with room. The driver caps the sent quantity to available room and returns it as `qty`. Goods move when time next moves.

```python
game.ally_send_goods(2, "wood", 25)
```

See also: and [refusals](reference/errors.md#ally_send_goods).

```python
ally_send_goods(self, ally: int, good: str, qty: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ally` | `int` | `required` | — |
| `good` | `str` | `required` | wood, hops, stone, iron, pitch, wheat, bread, cheese, meat, apples, ale, gold, flour, bows, crossbows, spears, pikes, maces, swords, leather_armor, metal_armor |
| `qty` | `int` | `required` | positive multiple of 5 |

**Returns:** `CommandResult`

**Refusals:** See [errors for ally_send_goods](reference/errors.md#ally_send_goods); bridge-wide validation can also reject a request.

<a id="ally_request_goods"></a>
## ally_request_goods

Request a positive multiple of five from a living ally. For non-gold goods your store must have room for the full amount. The ally decides immediately; it keeps a reserve and will not give gold, so a request can be refused. If accepted, goods arrive when time next moves.

```python
game.ally_request_goods(2, "wood", 25)
```

See also: and [refusals](reference/errors.md#ally_request_goods).

```python
ally_request_goods(self, ally: int, good: str, qty: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ally` | `int` | `required` | — |
| `good` | `str` | `required` | wood, hops, stone, iron, pitch, wheat, bread, cheese, meat, apples, ale, gold, flour, bows, crossbows, spears, pikes, maces, swords, leather_armor, metal_armor |
| `qty` | `int` | `required` | positive multiple of 5 |

**Returns:** `CommandResult`

**Refusals:** See [errors for ally_request_goods](reference/errors.md#ally_request_goods); bridge-wide validation can also reject a request.

<a id="ally_answer"></a>
## ally_answer

Answer a living ally’s outstanding goods request with a Boolean `accept`. Acceptance sends goods subject to your stock and the ally’s storage capacity; returned `qty` may be capped. Refusal tells the ally no. Either action is queued for when time next moves; no outstanding request is refused. Inspect `state()["allies"]` for requests.

```python
game.ally_answer(2, accept=False)
# {"queued": "ally_answer", "ally": 2, "accept": False,
#  "note": "when game time next moves"}
```

See also: and [refusals](reference/errors.md#ally_answer).

```python
ally_answer(self, ally: int, accept: bool) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ally` | `int` | `required` | — |
| `accept` | `bool` | `required` | — |

**Returns:** `CommandResult`

**Refusals:** See [errors for ally_answer](reference/errors.md#ally_answer); bridge-wide validation can also reject a request.

<a id="build_wall"></a>
## build_wall

Build a horizontal or vertical line; `kind` defaults to `"wall"` and can also select stairs or crenellations. Lines are limited to 100 tiles, or 12 for stairs. Ordinary wall costs half a stone per tile; low wall costs a quarter per tile. The driver checks affordability and placement before queuing. Stairs must start next to your wall; crenellations are laid beside an existing non-keep wall. The game builds and charges on the next command-processing frame. Stone promised to buildings, ammo or repair in the same pause is not reserved, so a line can end short.

```python
game.build_wall(40, 50, 50, 50)
```

See also: and [refusals](reference/errors.md#build_wall).

```python
build_wall(self, x1: int, y1: int, x2: int, y2: int, kind: str='wall') -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `x1` | `int` | `required` | 0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise |
| `y1` | `int` | `required` | 0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise |
| `x2` | `int` | `required` | 0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise |
| `y2` | `int` | `required` | 0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise |
| `kind` | `str` | `'wall'` | wall, stairs, low_wall, crenel; availability depends on driver level |

**Returns:** `CommandResult`

**Refusals:** See [errors for build_wall](reference/errors.md#build_wall); bridge-wide validation can also reject a request.

<a id="advance"></a>
## advance

Advance by an integer from 1 to 3000 ticks. Queued actions can run and units need time to carry out orders. A finite remaining budget caps the actual advance, and a finished match can stop it early. The result contains the current `tick`, `ticks_left` (or `None` for no budget), and `game_over`; inspect state and returned `events` rather than assuming every queued action completed. `next_since` is the event sequence cursor for a later `events(since)` call, not a tick number.

```python
result = game.advance(100)
print(result["tick"], result["ticks_left"], result["game_over"])
```

See also: and [refusals](reference/errors.md#advance).

```python
advance(self, ticks: int) -> AdvanceResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ticks` | `int` | `required` | 1..3000 |

**Returns:** `AdvanceResult`

**Refusals:** See [errors for advance](reference/errors.md#advance); bridge-wide validation can also reject a request.
