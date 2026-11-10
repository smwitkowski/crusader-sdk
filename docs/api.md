# API reference

Generated from the client and command metadata. Examples are illustrative; game state and IDs determine whether commands succeed.

<a id="state"></a>
## state

Return the current visible game state.

- **Returns:** one `State` snapshot: clock, treasury and stock, popularity, population and housing, tax and rations, the player's buildings, every recognized unit on the map, and in a skirmish the enemy lords and buildings. Every field is described in the [state reference](reference/state.md).
- **Use:** take unit and building IDs from it immediately before ordering; unit IDs are reused after a unit dies.
- **Refusals:** none from the driver; it also answers after the match has ended.

```python
s = game.state()
archers = [u["id"] for u in s["units"] if u["owner"] == 1 and u["type"] == "archer"]
print(s["tick"], s["gold"], s["stock"]["wood"], s["popularity"], s["idle_peasants"])
```

See also: [state reference](reference/state.md); [refusals](reference/errors.md#state).

```python
state(self) -> State
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| none | | | This command takes no parameters. |

**Returns:** `State`

**Refusals:** See [errors for state](reference/errors.md#state); bridge-wide validation can also reject a request.

<a id="map"></a>
## map

Return the inclusive tile rectangle as text.

- **Arguments:** `x0, y0, x1, y1`, each 0 to 399 with `x0 <= x1` and `y0 <= y1`. The default is the whole 400 × 400 map.
- **Returns:** newline-separated rows, one character per tile. Row 0 of the result is `y0` and column 0 is `x0`, so `rows[y - y0][x - x0]` is tile `(x, y)`. The characters are explained in the [map legend](reference/map-legend.md): `.` open ground, `,` farmable grass, `~` water, `^` blocked or wall, letters for buildings.
- **Limits:** the map shows terrain and buildings, not units, and not builds queued in the current pause.
- **Refused when:** a coordinate is not an integer in range or the rectangle is inverted (`invalid map rectangle`).

```python
rows = game.map(220, 220, 240, 240).splitlines()
tile = rows[230 - 220][235 - 220]  # tile (235, 230)
```

See also: [map legend](reference/map-legend.md); [refusals](reference/errors.md#map).

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

Find positions where the game would accept a building now, nearest first.

- **Arguments:** `building` is a placement name from the [buildings reference](reference/buildings.md), `keep`, or a siege engine name (for its 3 × 3 tent). `limit` is 1 to 50 (default 5). `near` is the tile to search around; without it the search centres on tile (235, 230), so pass a tile near the player's keep or the resource wanted.
- **Returns:** up to `limit` sites as `{"x", "y"}` top-left tiles, nearest to `near` first, none overlapping another or a build queued in this pause. Every site has passed the map checks and the game's own placement check.
- **Limits:** the driver tests at most `10 * limit` candidates against the game, so the list can be shorter than `limit`, or empty, even when valid spots exist farther away; raise `limit` or move `near`. Cost is not checked, and a site can stop being free once time moves.
- **Refused when:** the name is not a recognized placement name, `limit` is out of range, or the map's build menu does not offer the building.

```python
sites = game.find_sites("wheat_farm", limit=3, near=(235, 230))
# [{"x": 228, "y": 236}, {"x": 240, "y": 221}]
if sites:
    game.build("wheat_farm", sites[0]["x"], sites[0]["y"])
```

See also: [`build`](commands/economy.md#build); [refusals](reference/errors.md#find_sites).

```python
find_sites(self, building: str, limit: int=5, near: tuple[int, int] | None=None) -> list[Site]
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building` | `str` | `required` | Building or siege engine placement name (not ID); woodcutter, stockpile, hovel, quarry, wheat_farm, hops_farm, apple_orchard, dairy_farm, mill, bakery, brewery, market, hunters_post, granary, armory, barracks, inn, chapel, church, well, fletcher, poleturner, blacksmith, armourer, tanner, mercenary_post, iron_mine, lookout_tower, perimeter_tower, defense_turret, square_tower, round_tower, gatehouse, large_gatehouse, engineers_guild, tunnelers_guild, stables, cathedral, apothecary, ox_tether, pitch_rig, maypole, dancing_bear, small_garden, medium_garden, large_garden, statue, shrine, gallows, cess_pit, stocks, burning_stake, dungeon, stretching_rack, gibbet, chopping_block, dunking_stool, gatehouse_turned, large_gatehouse_turned, drawbridge, killing_pit, pitch_ditch, dog_cage, oil_smelter, water_pot, keep, catapult, trebuchet, battering_ram, siege_tower, portable_shield, fire_ballista; the map's build menu can withhold some |
| `limit` | `int` | `5` | 1..50 |
| `near` | `tuple[int, int] \| None` | `None` | tile (x, y) to search around; the search centres on (235, 230) when omitted |

**Returns:** `list[Site]`

**Refusals:** See [errors for find_sites](reference/errors.md#find_sites); bridge-wide validation can also reject a request.

<a id="look"></a>
## look

Centre the camera on a tile. Always refused by the game driver.

- **Refusals:** every call fails with `camera control is not supported`. The whole map is readable through `state` and `map` without moving a camera, so nothing depends on this command.

```python
game.look(235, 230)  # raises CrusaderError
```

See also: [how it works](how-it-works.md); [refusals](reference/errors.md#look).

```python
look(self, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `x` | `int` | `required` | 0..399; the command is always refused |
| `y` | `int` | `required` | 0..399; the command is always refused |

**Returns:** `CommandResult`

**Refusals:** See [errors for look](reference/errors.md#look); bridge-wide validation can also reject a request.

<a id="select"></a>
## select

Select owned units by ID, as a drag-select in the game does.

- **Arguments:** a list of 1 to 500 distinct IDs of the player's own live units.
- **Effect:** replaces the game's current selection and groups the units. Every order command selects its own units, so `select` is never required before an order.
- **Returns:** `{"tribe": n}`, the group number the game assigned.
- **Refused when:** the list is empty, too long or has duplicates, or an ID is not one of the player's live units.

```python
game.select([12, 13])
# {"tribe": 1249}
```

See also: [`move`](commands/military.md#move); [refusals](reference/errors.md#select).

```python
select(self, unit_ids: Iterable[int]) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int]` | `required` | list of 1..500 distinct IDs of own live units |

**Returns:** `CommandResult`

**Refusals:** See [errors for select](reference/errors.md#select); bridge-wide validation can also reject a request.

<a id="events"></a>
## events

Return the session's events from a list offset onward.

- **Arguments:** `since` is an offset into the event list, 0 (the default, everything) through the current number of events. It is not a tick.
- **Returns:** a list of event objects, oldest first; `[]` when nothing is new. Each has `type` and `tick` plus the fields of its type; see the [events reference](reference/events.md).
- **Use:** keep a count of events read and pass it as `since` after each `advance`.
- **Refused when:** `since` is negative, beyond the event count or not an integer (`invalid event offset`), and after the match has ended.

```python
seen = 0
game.advance(800)
for event in game.events(since=seen):
    print(event["type"], event["tick"])
    seen += 1
```

See also: [events reference](reference/events.md); [refusals](reference/errors.md#events).

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

- **Arguments:** `building` is a placement name from the [buildings reference](reference/buildings.md), which lists every footprint, cost and placement rule; `(x, y)` is the footprint's top-left tile. Use `find_sites` to get tiles the game accepts.
- **Checks, in order:** the map (every footprint tile on the map, free, level, and for farms farmable, for an iron mine on ore); the game's own placement check (adjacency, distance to the enemy and to the castle); the map's build menu; then the cost, read from the game's cost table, against the current stock of wood, stone, gold, iron and pitch. A drawbridge must also sit in front of the gate of an owned gatehouse.
- **Effect and timing:** the game takes the cost and places the building when time next moves. A staffed building then waits for a free peasant before it works.
- **Special names:** `flag_1` to `flag_4`, `heads` and `brazier` go on top of an owned wall or tower; `mangonel` and `ballista` go on a tower-top tile of an owned square or round tower that has no engine, and then need 2 engineers (`man`).
- **Refused when:** the name is not recognized; a tile fails the map check (the message names the tile and what blocks it); the game refuses the spot (the message carries the game's reason); the build menu does not offer the building; or the stock is short (the message gives the amounts needed and held).
- **Afterwards:** if the spot is no longer free when time moves, a `build_refused` event with a `reason` is recorded and nothing is charged.

```python
site = game.find_sites("woodcutter", limit=1, near=(235, 230))[0]
game.build("woodcutter", site["x"], site["y"])
# {"queued": "woodcutter", "x": 235, "y": 230, "note": "placed when game time next moves"}
```

See also: [`find_sites`](commands/observe.md#find_sites); [buildings reference](reference/buildings.md); [refusals](reference/errors.md#build).

```python
build(self, building: str, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building` | `str` | `required` | Building placement name (not ID); woodcutter, stockpile, hovel, quarry, wheat_farm, hops_farm, apple_orchard, dairy_farm, mill, bakery, brewery, market, hunters_post, granary, armory, barracks, inn, chapel, church, well, fletcher, poleturner, blacksmith, armourer, tanner, mercenary_post, iron_mine, lookout_tower, perimeter_tower, defense_turret, square_tower, round_tower, gatehouse, large_gatehouse, engineers_guild, tunnelers_guild, stables, cathedral, apothecary, ox_tether, pitch_rig, maypole, dancing_bear, small_garden, medium_garden, large_garden, statue, shrine, gallows, cess_pit, stocks, burning_stake, dungeon, stretching_rack, gibbet, chopping_block, dunking_stool, gatehouse_turned, large_gatehouse_turned, drawbridge, killing_pit, pitch_ditch, dog_cage, oil_smelter, water_pot, flag_1, flag_2, flag_3, flag_4, heads, brazier, mangonel, ballista; the map's build menu can withhold some |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for build](reference/errors.md#build); bridge-wide validation can also reject a request.

<a id="demolish"></a>
## demolish

Demolish an owned building.

- **Arguments:** `building_id` from `state()["buildings"]`.
- **Effect and timing:** the game removes the building when time next moves and refunds half of its cost. Its worker returns to the campfire.
- **Refused when:** the ID is not one of the player's buildings, or it is the keep (`the keep cannot be demolished`).
- **Afterwards:** a `demolish_refused` event is recorded if the building is still standing after time moved.

```python
game.demolish(12)
# {"queued": "demolish", "building_id": 12, "type": "woodcutter", "note": "removed when game time next moves; part of its cost is refunded"}
```

See also: [`events`](commands/observe.md#events); [refusals](reference/errors.md#demolish).

```python
demolish(self, building_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | ID of an owned building from state buildings |

**Returns:** `CommandResult`

**Refusals:** See [errors for demolish](reference/errors.md#demolish); bridge-wide validation can also reject a request.

<a id="set_tax"></a>
## set_tax

Set the tax level, from -3 to 8.

- **Levels:** −3 to −1 are bribes paid to the population out of the treasury, 0 is no tax, 1 to 8 are increasingly heavy taxes.
- **Popularity:** each level has a fixed monthly popularity effect: −3: +7, −2: +5, −1: +3, 0: +1, 1: −2, 2: −4, 3: −6, 4: −8, 5: −12, 6: −16, 7: −20, 8: −24.
- **Gold:** tax grows with the level and the population. The game accumulates it weekly and pays it into the treasury at the end of each game month, so receipts trail a change by up to a month. Bribes are deducted the same way.
- **Timing:** the level changes when time next moves and shows as `State.tax`.
- **Refused when:** `level` is not an integer from −3 to 8.

```python
game.set_tax(1)
# {"tax": 1}
```

See also: [`report`](commands/observe.md#report); [popularity](concepts.md#popularity); [refusals](reference/errors.md#set_tax).

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

Set the ration level: none, half, normal, extra or double.

- **Popularity:** `none` −8, `half` −4, `normal` 0, `extra` +4, `double` +8 a month. With no food in the granary the effect is −8 whatever the setting.
- **Food:** higher rations empty the granary faster in proportion.
- **Timing:** the level changes when time next moves and shows as `State.rations`.
- **Refused when:** `level` is not one of the five names.

```python
game.set_rations("extra")
# {"rations": "extra"}
```

See also: [`report`](commands/observe.md#report); [food and rations](concepts.md#food-and-rations); [refusals](reference/errors.md#set_rations).

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

Buy or sell goods at the market in multiples of five. Positive quantities buy; negative quantities sell.

- **Needs:** an owned `market`, and a good the map allows to be traded. Gold itself cannot be traded.
- **Arguments:** `qty` is a non-zero multiple of 5 with an absolute value of at most 500.
- **Buying:** costs the game's current buy price per lot of 5. The driver refuses a purchase the treasury cannot cover after other spending queued in this pause. If the good's store has no room when time moves, the game buys nothing and keeps the gold.
- **Selling:** earns the current sell price per 5. The game sells in lots sized by the stock at each sale: everything below 5 in stock, 5 at a time below 50, 10 below 100, 20 below 200, otherwise 50. The requested amount must be reachable exactly with those lots; for example 15 can be sold from a stock of 40 (three lots of 5) but not from a stock of 120 (lots of 20).
- **Returns:** `queued` (`"buy"` or `"sell"`), `good`, `qty`, `gold` (negative for the cost of a purchase, positive for the proceeds of a sale) and `note`.
- **Timing:** executed when time next moves.
- **Refused when:** the good is not recognized or `cannot be traded`; `qty` is zero, not a multiple of 5 or over 500; there is no market; gold is short; or the sale cannot be made in the game's lot sizes.

```python
game.trade("wood", 10)  # buy 10 wood
game.trade("apples", -20)  # sell 20 apples
# {"queued": "sell", "good": "apples", "qty": -20, "gold": 16, "note": "sold when game time next moves"}
```

See also: [goods reference](reference/goods.md#trading); [refusals](reference/errors.md#trade).

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

Recruit soldiers, mercenaries or specialists from idle peasants.

- **Arguments:** `unit` is a name from the [units reference](reference/units.md), which lists every price and the goods each unit uses; `count` is 1 to 50 (default 1).
- **Needs, per recruit:** one idle peasant at the campfire (`State.idle_peasants`), the gold price, and the recruiting building: a `barracks` for archers, crossbowmen, spearmen, pikemen, macemen, swordsmen and knights; a `mercenary_post` for the seven Arabian units; an `engineers_guild` for engineers and laddermen; a `tunnelers_guild` for tunnelers; a `cathedral` for monks. Barracks troops also use one of each of their weapons and armor from the armory, and a knight uses one horse from the stables.
- **Effect and timing:** the game takes the gold and goods when time next moves. A barracks soldier appears about 40 ticks later, when his peasant has walked to the barracks; other recruits walk from the campfire to their building in the same way. The new unit then appears in `State.units`.
- **Returns:** `queued` (the unit name), `count`, `gold` (the total cost, negative) and `note`.
- **Refused when:** the unit name is not recognized; `count` is out of range; the map does not offer the unit; the building is missing; or gold, a weapon, armor, horses or idle peasants are short. The message names what is missing and how much is available after earlier commands of the same pause.

```python
game.recruit("archer", count=2)
# {"queued": "archer", "count": 2, "gold": -24, "note": "paid when game time next moves; each soldier appears at the barracks ~40 ticks later"}
```

See also: [units reference](reference/units.md); [refusals](reference/errors.md#recruit).

```python
recruit(self, unit: str, count: int=1) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit` | `str` | `required` | Unit name (not ID); archer, crossbowman, spearman, pikeman, maceman, swordsman, knight, arabian_archer, slave, slinger, assassin, horse_archer, arabian_swordsman, fire_thrower, engineer, laddermen, tunneler, monk; a map can withhold some |
| `count` | `int` | `1` | 1..50 |

**Returns:** `CommandResult`

**Refusals:** See [errors for recruit](reference/errors.md#recruit); bridge-wide validation can also reject a request.

<a id="move"></a>
## move

Order units to walk to a tile, optionally continuing through waypoints.

- **Arguments:** `(x, y)` is the destination tile. `waypoints` is an optional list of 1 to 8 further `(x, y)` tiles, walked in order after `(x, y)`; the game keeps at most 9 markers in all. The units stay at the last marker.
- **Limits:** units stop short of a tile they cannot reach (water, walls, enclosed ground) without an error; check their positions after advancing. In a historical campaign the lord can only be sent back to his keep.
- **Returns:** `queued`, `units` (count) and either `x`, `y` or, with waypoints, `markers` (the full route).
- **Refused when:** a tile is off the map or not a pair of integers, or the marker count is outside 2 to 9 when waypoints are given.

```python
game.move([12, 13], 230, 225, waypoints=[(235, 225)])
# {"queued": "move", "units": 2, "markers": [[230, 225], [235, 225]], "note": "they walk the markers in order when game time next moves"}
```

See also: [`state`](commands/observe.md#state); [refusals](reference/errors.md#move).

```python
move(self, unit_ids: Iterable[int] | None, x: int, y: int, waypoints: Iterable[Sequence[int]] | None=None) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `waypoints` | `Iterable[tuple[int, int]] \| None` | `None` | 1..8 points if provided; each must be a valid map tile (coordinates 0..399) |

**Returns:** `CommandResult`

**Refusals:** See [errors for move](reference/errors.md#move); bridge-wide validation can also reject a request.

<a id="set_stance"></a>
## set_stance

Set how units react to nearby enemies.

- **Stances:** `stand_ground` keeps units on their spot; `defensive` lets them engage enemies that come close; `aggressive` sends them after enemies that come near.
- **Effect:** applies to exactly the listed units, from when time next moves, until changed.
- **Refused when:** `stance` is not one of the three names.

```python
game.set_stance([12, 13], "defensive")
# {"queued": "stance", "units": 2, "stance": "defensive"}
```

See also: [`stop`](#stop); [refusals](reference/errors.md#set_stance).

```python
set_stance(self, unit_ids: Iterable[int] | None, stance: Literal['stand_ground', 'defensive', 'aggressive']) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `stance` | `str` | `required` | stand_ground, defensive, aggressive |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_stance](reference/errors.md#set_stance); bridge-wide validation can also reject a request.

<a id="stop"></a>
## stop

Stop units where they are and cancel their current order.

- **Effect:** the units halt when time next moves. Their stance still governs how they react to enemies.

```python
game.stop([12, 13])
# {"queued": "stop", "units": 2, "note": "they stop when game time next moves"}
```

See also: [`move`](#move); [refusals](reference/errors.md#stop).

```python
stop(self, unit_ids: Iterable[int] | None) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |

**Returns:** `CommandResult`

**Refusals:** See [errors for stop](reference/errors.md#stop); bridge-wide validation can also reject a request.

<a id="disband"></a>
## disband

Turn soldiers back into peasants.

- **Effect:** the units become peasants and walk to the campfire, where they can take jobs or be recruited again. The gold, weapons and armor they cost are not refunded.
- **Refused when:** the list includes the lord (`your lord cannot be disbanded`).

```python
game.disband([12, 13])
# {"queued": "disband", "units": 2, "note": "they turn back into peasants when game time next moves"}
```

See also: [`recruit`](commands/economy.md#recruit); [refusals](reference/errors.md#disband).

```python
disband(self, unit_ids: Iterable[int] | None) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |

**Returns:** `CommandResult`

**Refusals:** See [errors for disband](reference/errors.md#disband); bridge-wide validation can also reject a request.

<a id="patrol"></a>
## patrol

Order units to walk a route back and forth.

- **Arguments:** `points` is a list of 1 to 9 `(x, y)` tiles.
- **Effect:** the units walk the points in order and back, repeatedly, until they receive another order.
- **Refused when:** `points` is not a list of 1 to 9 integer pairs or a point is off the map. In a historical campaign the lord cannot patrol.

```python
game.patrol([12, 13], [(230, 225), (235, 225)])
# {"queued": "patrol", "units": 2, "points": [[230, 225], [235, 225]]}
```

See also: [`move`](#move); [refusals](reference/errors.md#patrol).

```python
patrol(self, unit_ids: Iterable[int] | None, points: Iterable[Sequence[int]]) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `points` | `Iterable[tuple[int, int]]` | `required` | 1..9 points; each point must be a valid map tile (coordinates 0..399) |

**Returns:** `CommandResult`

**Refusals:** See [errors for patrol](reference/errors.md#patrol); bridge-wide validation can also reject a request.

<a id="attack_ground"></a>
## attack_ground

Order ranged units to keep shooting at a tile.

- **Units:** ranged soldiers only: archers, crossbowmen, slingers, horse archers, Arabian archers and fire throwers.
- **Effect:** the units shoot at the spot from where they stand, hitting whatever enters it, and pay less attention to enemies elsewhere than idle ranged units do. The order lasts until replaced.
- **Refused when:** a listed unit is not ranged, or the tile is off the map.

```python
game.attack_ground([12, 13], 240, 230)
# {"queued": "attack_ground", "units": 2, "x": 240, "y": 230}
```

See also: [`attack`](#attack); [refusals](reference/errors.md#attack_ground).

```python
attack_ground(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for attack_ground](reference/errors.md#attack_ground); bridge-wide validation can also reject a request.

<a id="attack_wall"></a>
## attack_wall

Order units to attack an enemy wall tile.

- **Arguments:** `(x, y)` must be a wall tile (`^` on the map) owned by a player who is neither the controlled player nor an ally.
- **Effect:** the units walk to the wall and attack that tile. A siege tower given this order rolls to the wall and docks, letting soldiers climb onto the wall over it.
- **Refused when:** the tile is not a wall tile, or the wall is the player's own or an ally's.

```python
game.attack_wall([12, 13], 240, 230)
# {"queued": "attack_wall", "units": 2, "x": 240, "y": 230}
```

See also: [`attack_building`](#attack_building); [`set_ladder`](commands/siege.md#set_ladder); [refusals](reference/errors.md#attack_wall).

```python
attack_wall(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for attack_wall](reference/errors.md#attack_wall); bridge-wide validation can also reject a request.

<a id="attack"></a>
## attack

Order units to attack one enemy unit.

- **Arguments:** `target_id` is the ID of a live unit of another, non-allied player from `state()["units"]`. An enemy lord's ID is in `state()["enemy"]["lords"]`.
- **Effect:** the units pursue and attack the target. When it dies they fall back on their stance; give a new order for the next target.
- **Refused when:** the target is not a live enemy unit of a recognized type, or belongs to an ally.

```python
game.attack([12, 13], target_id=42)
# {"queued": "attack", "units": 2, "target_id": 42, "note": "they attack when game time next moves"}
```

See also: [`state`](commands/observe.md#state); [refusals](reference/errors.md#attack).

```python
attack(self, unit_ids: Iterable[int] | None, target_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `target_id` | `int` | `required` | ID of a live enemy unit from state units |

**Returns:** `CommandResult`

**Refusals:** See [errors for attack](reference/errors.md#attack); bridge-wide validation can also reject a request.

<a id="attack_building"></a>
## attack_building

Order units to attack one enemy building.

- **Arguments:** `building_id` is the `id` of an entry in `state()["enemy"]["buildings"]`.
- **Effect:** the units walk to the building and attack it until it is destroyed. A keep cannot be damaged. Catapults and trebuchets shoot buildings from range; a battering ram walks up and batters.
- **Refused when:** the ID is not a building of another, non-allied player.

```python
game.attack_building([12, 13], building_id=42)
# {"queued": "attack", "units": 2, "building_id": 42, "note": "they attack when game time next moves"}
```

See also: [`state`](commands/observe.md#state); [refusals](reference/errors.md#attack_building).

```python
attack_building(self, unit_ids: Iterable[int] | None, building_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `building_id` | `int` | `required` | ID of an enemy building from state enemy buildings |

**Returns:** `CommandResult`

**Refusals:** See [errors for attack_building](reference/errors.md#attack_building); bridge-wide validation can also reject a request.

<a id="build_siege"></a>
## build_siege

Have engineers put up a siege tent and build an engine in it.

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

See also: [siege engines](reference/units.md#siege-engines); [refusals](reference/errors.md#build_siege).

```python
build_siege(self, engineer_ids: Iterable[int] | None, engine: Literal['catapult', 'trebuchet', 'battering_ram', 'siege_tower', 'portable_shield', 'fire_ballista'], x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engineer_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live engineers; None is refused by the game driver |
| `engine` | `str` | `required` | catapult, trebuchet, battering_ram, siege_tower, portable_shield, fire_ballista |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for build_siege](reference/errors.md#build_siege); bridge-wide validation can also reject a request.

<a id="man"></a>
## man

Send engineers to crew an owned engine that is short of crew.

- **Arguments:** `engineer_ids` are free engineers; `engine_id` is an own siege engine or tower engine from `state()["units"]`.
- **Effect:** as many of the engineers as the engine still needs walk to it and board. Crew is all or nothing: an engine acts only with its full crew, so send enough engineers to complete it. The result's `crew_needed` is the number still missing when the order was given.
- **Tower engines:** a `mangonel` or `ballista` needs 2 engineers, who must be able to walk up to it: the tower has to be joined to a wall with stairs to the ground.
- **Refused when:** a listed unit is not an engineer; `engine_id` is not one of the player's engines; the engine already has its full crew; or the engineers cannot reach it.

```python
game.man([101, 102], 205)
# {"queued": "man", "engine_id": 205, "crew_needed": 2, "note": "they walk to it when game time next moves"}
```

See also: [`unman`](#unman); [refusals](reference/errors.md#man).

```python
man(self, engineer_ids: Iterable[int] | None, engine_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engineer_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live engineers; None is refused by the game driver |
| `engine_id` | `int` | `required` | ID of an own siege engine from state units |

**Returns:** `CommandResult`

**Refusals:** See [errors for man](reference/errors.md#man); bridge-wide validation can also reject a request.

<a id="unman"></a>
## unman

Take the crew off an owned engine.

- **Effect:** the engineers step off and are free for other work. The engine stays where it is and takes no orders until crewed again.
- **Refused when:** `engine_id` is not one of the player's engines, or it has no crew.

```python
game.unman(205)
# {"queued": "unman", "engine_id": 205}
```

See also: [`man`](#man); [refusals](reference/errors.md#unman).

```python
unman(self, engine_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engine_id` | `int` | `required` | ID of an own siege engine from state units |

**Returns:** `CommandResult`

**Refusals:** See [errors for unman](reference/errors.md#unman); bridge-wide validation can also reject a request.

<a id="buy_ammo"></a>
## buy_ammo

Buy 20 shots for a catapult or trebuchet for 10 stone.

- **Applies to:** own catapults and trebuchets. A catapult starts with 20 shots and uses one per shot; `State.units` shows the remaining `ammo`.
- **Cost and timing:** 10 stone from the stockpile for 20 more shots, taken when time next moves.
- **Refused when:** the unit is not an own catapult or trebuchet, or the stockpile holds fewer than 10 stone.

```python
game.buy_ammo(205)
# {"queued": "buy_ammo", "engine_id": 205, "stone": 10, "shots": 20}
```

See also: [`attack_building`](commands/military.md#attack_building); [refusals](reference/errors.md#buy_ammo).

```python
buy_ammo(self, engine_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engine_id` | `int` | `required` | ID of an own siege engine from state units |

**Returns:** `CommandResult`

**Refusals:** See [errors for buy_ammo](reference/errors.md#buy_ammo); bridge-wide validation can also reject a request.

<a id="throw_cow"></a>
## throw_cow

Order a catapult or trebuchet to throw a cow at a tile.

- **Needs:** a crewed own catapult or trebuchet, and at least one cow. Cows are the cattle of the player's dairy farms; own catapults and trebuchets show the count as `cows` in state.
- **Effect:** the crew throws one cow at `(x, y)`; the carcass lies where it lands, and the cow count drops by one. The result's `cows` is the count when the order was given.
- **Refused when:** the unit is not an own catapult or trebuchet, it has no crew, the player has no cows, or the tile is off the map.

```python
game.throw_cow(205, 80, 70)
# {"queued": "throw_cow", "engine_id": 205, "x": 80, "y": 70, "cows": 3}
```

See also: [`buy_ammo`](#buy_ammo); [refusals](reference/errors.md#throw_cow).

```python
throw_cow(self, engine_id: int, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engine_id` | `int` | `required` | ID of an own siege engine from state units |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for throw_cow](reference/errors.md#throw_cow); bridge-wide validation can also reject a request.

<a id="set_ladder"></a>
## set_ladder

Order laddermen to raise a ladder against an enemy wall tile.

- **Arguments:** `unit_ids` are laddermen; `(x, y)` is a wall tile (`^` on the map) of a player who is neither the controlled player nor an ally.
- **Effect:** the laddermen carry a ladder to the wall and raise it; soldiers ordered onto or over the wall can then climb there. Laddermen cannot fight.
- **Refused when:** a listed unit is not a ladderman, the tile is not a wall tile, or the wall is the player's own or an ally's.

```python
game.set_ladder([301], 80, 70)
# {"queued": "set_ladder", "units": 1, "x": 80, "y": 70}
```

See also: [`attack_wall`](commands/military.md#attack_wall); [refusals](reference/errors.md#set_ladder).

```python
set_ladder(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_ladder](reference/errors.md#set_ladder); bridge-wide validation can also reject a request.

<a id="dig_tunnel"></a>
## dig_tunnel

Order tunnelers to start a tunnel at a tile.

- **Arguments:** `unit_ids` are tunnelers; `(x, y)` is the top-left tile of the tunnel entrance.
- **Effect:** a tunneler digs underground from the entrance toward the nearest enemy wall or building; when the tunnel collapses under it, that wall tile is destroyed or the building damaged.
- **Placement:** the game accepts an entrance only where an enemy-built wall or a small enemy tower lies within tunnelling distance; the walls that come with an enemy keep do not count. Against an enemy who has built no walls every spot is refused.
- **Refused when:** a listed unit is not a tunneler, the tile is off the map, or the game refuses the spot (often without stating a reason).

```python
game.dig_tunnel([302], 75, 70)
# {"queued": "dig_tunnel", "units": 1, "x": 75, "y": 70}
```

See also: [`attack_wall`](commands/military.md#attack_wall); [refusals](reference/errors.md#dig_tunnel).

```python
dig_tunnel(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for dig_tunnel](reference/errors.md#dig_tunnel); bridge-wide validation can also reject a request.

<a id="repair"></a>
## repair

Repair a damaged owned tower or gatehouse to full health.

- **Applies to:** `lookout_tower`, `perimeter_tower`, `defense_turret`, `square_tower`, `round_tower`, `gatehouse` and `large_gatehouse`. Other buildings have no repair.
- **Cost:** the game computes it from the damage: the missing share of the building's health times its wood and stone cost, at least 1 of each material the building costs. The amounts are returned as `wood` and `stone`.
- **Timing:** health is restored and the cost charged when time next moves.
- **Refused when:** the building is not the player's or not repairable; it is not damaged; an enemy unit is near it (within 15 tiles in a match against computer lords, 30 otherwise); or wood or stone is short.

```python
game.repair(12)
# {"queued": "repair", "building_id": 12, "wood": 0, "stone": 9, "note": "repaired to full hp when game time next moves"}
```

See also: [`building_info`](commands/observe.md#building_info); [refusals](reference/errors.md#repair).

```python
repair(self, building_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | ID of an owned building from state buildings |

**Returns:** `CommandResult`

**Refusals:** See [errors for repair](reference/errors.md#repair); bridge-wide validation can also reject a request.

<a id="set_building_active"></a>
## set_building_active

Put a type of building to sleep or wake it.

- **Arguments:** `building_id` identifies the type; `active` is `False` to sleep and `True` to wake.
- **Effect:** the game applies sleep per type: **every** owned building of that building's type sleeps or wakes together. Workers of sleeping buildings leave for the campfire as idle peasants and the buildings produce nothing. After waking, workers have to walk back before production resumes.
- **Applies to:** staffed buildings (marked in the [buildings reference](reference/buildings.md)): woodcutter, quarry, ox tether, iron mine, pitch rig, the four farms, hunter's post, mill, bakery, brewery, inn, the five weapon workshops, chapel, church, cathedral, apothecary, well and water pot.
- **Timing:** when time next moves. Nothing is queued if the type is already in the requested state.
- **Refused when:** the ID is not one of the player's buildings, `active` is not a Boolean, or the type has no sleep control.

```python
game.set_building_active(12, False)
# {"queued": "set_building_active", "type": "woodcutter", "active": False, "note": "every woodcutter of yours sleeps from when game time next moves"}
```

See also: [`building_info`](commands/observe.md#building_info); [refusals](reference/errors.md#set_building_active).

```python
set_building_active(self, building_id: int, active: bool) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | ID of an owned building from state buildings |
| `active` | `bool` | `required` | True wakes; False puts to sleep |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_building_active](reference/errors.md#set_building_active); bridge-wide validation can also reject a request.

<a id="set_workshop_product"></a>
## set_workshop_product

Choose which weapon a workshop makes.

- **Products:** a `fletcher` makes `bows` or `crossbows`, a `poleturner` `spears` or `pikes`, a `blacksmith` `maces` or `swords`. The armourer and tanner have a single product.
- **Effect and timing:** the workshop switches from its next piece of work; a weapon already in progress is finished first. The setting applies to that one workshop.
- **Refused when:** the building is not an owned fletcher, poleturner or blacksmith; the weapon is not one of its two products; or the map does not allow that weapon to be made.

```python
game.set_workshop_product(12, "crossbows")
# {"queued": "set_workshop_product", "building_id": 12, "weapon": "crossbows", "note": "it makes this from its next piece of work"}
```

See also: [`building_info`](commands/observe.md#building_info); [refusals](reference/errors.md#set_workshop_product).

```python
set_workshop_product(self, building_id: int, weapon: Literal['bows', 'crossbows', 'spears', 'pikes', 'maces', 'swords']) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | ID of an owned building from state buildings |
| `weapon` | `str` | `required` | fletcher: bows, crossbows; poleturner: spears, pikes; blacksmith: maces, swords |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_workshop_product](reference/errors.md#set_workshop_product); bridge-wide validation can also reject a request.

<a id="set_food_allowed"></a>
## set_food_allowed

Allow or forbid the population to eat one food.

- **Arguments:** `food` is `apples`, `cheese`, `meat` or `bread`; `allowed` is a Boolean.
- **Needs:** an owned granary.
- **Effect:** a forbidden food stays in the granary and is not eaten, which lowers the number of food types eaten and so the variety bonus. It does not sell or remove the food. The change is applied on the next frame without waiting for time to move, and persists until changed back.
- **Refused when:** the food name is not one of the four, `allowed` is not a Boolean, there is no granary, or the game mode does not have the granary's food controls.

```python
game.set_food_allowed("bread", False)
# {"food": "bread", "allowed": False}
```

See also: [`report`](commands/observe.md#report); [refusals](reference/errors.md#set_food_allowed).

```python
set_food_allowed(self, food: str, allowed: bool) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `food` | `str` | `required` | apples, cheese, meat, bread |
| `allowed` | `bool` | `required` | True allows eating; False forbids it |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_food_allowed](reference/errors.md#set_food_allowed); bridge-wide validation can also reject a request.

<a id="set_gate"></a>
## set_gate

Open or close an owned gatehouse or drawbridge.

- **Arguments:** `building_id` of an owned `gatehouse`, `large_gatehouse` or `drawbridge`; `open` is a Boolean.
- **Effect:** an open gate lets units through. A closed gate, or a raised drawbridge, stops every ground unit, the player's own included. The gate starts to move when time next moves and takes a short while to finish.
- **Refused when:** the building is not the player's, is not a gatehouse or drawbridge, or `open` is not a Boolean.

```python
game.set_gate(42, False)
# {"queued": "set_gate", "building_id": 42, "open": False, "note": "when game time next moves"}
```

See also: [`build`](commands/economy.md#build); [refusals](reference/errors.md#set_gate).

```python
set_gate(self, building_id: int, open: bool) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | ID of an owned building from state buildings |
| `open` | `bool` | `required` | True opens; False closes |

**Returns:** `CommandResult`

**Refusals:** See [errors for set_gate](reference/errors.md#set_gate); bridge-wide validation can also reject a request.

<a id="plan_moat"></a>
## plan_moat

Mark, or unmark, a straight line of moat to be dug.

- **Arguments:** a horizontal or vertical line of at most 100 tiles; `dig=True` (default) marks the plan, `dig=False` removes a plan along the line.
- **Effect:** the game marks the plan with a two-tile brush on the tiles it accepts (land without buildings or walls), so the marked strip can be wider than the line. Planning costs nothing. A plan does not block anything until dug.
- **Returns:** `queued` (`"plan_moat"` or `"unplan_moat"`), `tiles` (the length of the line, not the number of tiles the game marked) and `note`.
- **Timing:** marked when time next moves.
- **Refused when:** the line is diagonal, longer than 100 tiles or leaves the map, or `dig` is not a Boolean.

```python
game.plan_moat(228, 230, 236, 230)
# {"queued": "plan_moat", "tiles": 9, "note": "marked when game time next moves"}
```

See also: [`dig_moat`](#dig_moat); [refusals](reference/errors.md#plan_moat).

```python
plan_moat(self, x1: int, y1: int, x2: int, y2: int, dig: bool=True) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `x1` | `int` | `required` | 0..399; valid map tile; line must be straight and at most 100 tiles |
| `y1` | `int` | `required` | 0..399; valid map tile; line must be straight and at most 100 tiles |
| `x2` | `int` | `required` | 0..399; valid map tile; line must be straight and at most 100 tiles |
| `y2` | `int` | `required` | 0..399; valid map tile; line must be straight and at most 100 tiles |
| `dig` | `bool` | `True` | True marks the plan; False removes it |

**Returns:** `CommandResult`

**Refusals:** See [errors for plan_moat](reference/errors.md#plan_moat); bridge-wide validation can also reject a request.

<a id="dig_moat"></a>
## dig_moat

Order units to dig out the player's moat plan.

- **Units:** archers, spearmen, pikemen, macemen, engineers and slaves.
- **Arguments:** `(x, y)` must be a tile of the moat plan, so advance at least one tick after `plan_moat` before ordering.
- **Effect:** the units walk to the plan and dig it out tile by tile, continuing along the plan. A dug tile is moat, which ground units cannot cross. Digging takes time (measured: four spearmen dug three tiles in about 600 ticks).
- **Refused when:** a listed unit cannot dig, or the tile is not part of the moat plan.

```python
game.dig_moat([101, 102], 230, 230)
# {"queued": "dig_moat", "units": 2, "x": 230, "y": 230}
```

See also: [`plan_moat`](#plan_moat); [refusals](reference/errors.md#dig_moat).

```python
dig_moat(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for dig_moat](reference/errors.md#dig_moat); bridge-wide validation can also reject a request.

<a id="fill_moat"></a>
## fill_moat

Order units to fill an enemy's dug moat tile.

- **Units:** the same diggers as `dig_moat`.
- **Arguments:** `(x, y)` must be a dug moat tile belonging to another team.
- **Effect:** the units carry earth into the moat until the tile is land again.
- **Refused when:** a listed unit cannot dig; the tile is not dug moat; or the moat is the player's own or an ally's. The player's own moat cannot be filled.

```python
game.fill_moat([101], 80, 70)
# {"queued": "fill_moat", "units": 1, "x": 80, "y": 70}
```

See also: [`dig_moat`](#dig_moat); [refusals](reference/errors.md#fill_moat).

```python
fill_moat(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for fill_moat](reference/errors.md#fill_moat); bridge-wide validation can also reject a request.

<a id="delete_wall"></a>
## delete_wall

Remove one owned wall tile.

- **Arguments:** `(x, y)` must be a wall or stairs tile owned by the player.
- **Effect and timing:** the tile is removed when time next moves and the game refunds half of its stone (half of that again for a low wall); a single tile's refund can round down to nothing.
- **Limits:** only walls. A moat plan is removed with `plan_moat(..., dig=False)`; pitch ditches, towers and gatehouses are buildings and are removed with `demolish`.
- **Refused when:** the tile is not one of the player's wall tiles.

```python
game.delete_wall(230, 210)
# {"queued": "delete_wall", "x": 230, "y": 210, "note": "removed when game time next moves; half its stone is refunded"}
```

See also: [`build_wall`](#build_wall); [refusals](reference/errors.md#delete_wall).

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

Order archers to set one of the player's pitch ditches alight.

- **Units:** archers and Arabian archers.
- **Needs:** a `pitch_ditch` tile of the player's team at `(x, y)`; a lit `brazier` (placed with `build` on a wall or tower top) within 3 tiles of the **first** unit in `unit_ids`; and the pitch tile within the game's lighting range of that unit. The range is read from the game; in version 1.41 it is 49 tiles.
- **Effect:** the archers shoot a burning arrow into the ditch. The lit tile burns, sets adjoining pitch tiles alight, and burns units standing in it.
- **Refused when:** a listed unit is not an archer or Arabian archer; there is no friendly pitch ditch at the tile; no lit brazier is beside the first unit; or the pitch is out of range.

```python
game.build("brazier", 231, 224)  # on the wall the archers stand on
game.advance(10)
game.light_pitch([101, 102], 232, 230)
# {"queued": "light_pitch", "units": 2, "x": 232, "y": 230}
```

See also: [`build`](commands/economy.md#build); [refusals](reference/errors.md#light_pitch).

```python
light_pitch(self, unit_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `unit_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live units; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for light_pitch](reference/errors.md#light_pitch); bridge-wide validation can also reject a request.

<a id="oil_duty"></a>
## oil_duty

Assign engineers to an owned oil smelter.

- **Arguments:** `engineer_ids` are engineers; `smelter_id` is an owned `oil_smelter`.
- **Effect:** one engineer works the smelter, which boils pitch from the stockpile into oil; the others wait and each receives a pot of boiling oil. The smelter needs pitch in the stockpile.
- **Limits:** pouring the oil is not available; see `pour_oil`.
- **Refused when:** a listed unit is not an engineer, or the building is not an owned oil smelter.

```python
game.oil_duty([101, 102], 42)
# {"queued": "oil_duty", "units": 2, "smelter_id": 42}
```

See also: [`pour_oil`](#pour_oil); [refusals](reference/errors.md#oil_duty).

```python
oil_duty(self, engineer_ids: Iterable[int] | None, smelter_id: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engineer_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live engineers; None is refused by the game driver |
| `smelter_id` | `int` | `required` | ID of an owned oil_smelter |

**Returns:** `CommandResult`

**Refusals:** See [errors for oil_duty](reference/errors.md#oil_duty); bridge-wide validation can also reject a request.

<a id="pour_oil"></a>
## pour_oil

Order engineers to pour boiling oil. Always refused by the game driver.

- **Status:** the driver cannot yet reproduce the game's pour action, so every call is refused rather than queue an order that would do nothing. The final refusal reads `pouring oil is not available yet`.
- **Earlier refusals:** the driver first checks that the listed units are engineers and that at least one carries an oil pot, so those messages can appear instead.

```python
game.pour_oil([101], 232, 236)  # raises CrusaderError
```

See also: [`oil_duty`](#oil_duty); [refusals](reference/errors.md#pour_oil).

```python
pour_oil(self, engineer_ids: Iterable[int] | None, x: int, y: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `engineer_ids` | `Iterable[int] \| None` | `required` | list of 1..500 distinct IDs of own live engineers; None is refused by the game driver |
| `x` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |
| `y` | `int` | `required` | 0..399; must form a valid map tile with its paired coordinate |

**Returns:** `CommandResult`

**Refusals:** See [errors for pour_oil](reference/errors.md#pour_oil); bridge-wide validation can also reject a request.

<a id="report"></a>
## report

Return one page of the game's information book.

`page` selects the figures returned:

| Page | Fields |
|---|---|
| `popularity` | `food`, `tax`, `crowding`, `fear_factor`, `religion`, `ale_coverage`: each factor's monthly popularity change in the units the game displays; `coming_month`: their sum. Optional `event_0` to `event_5` and `event_flag` appear while a scripted map event affects popularity. |
| `fear` | `good_things`, `bad_things` (counts built), `popularity_effect` (the fear level, −5 to 5), `next_level_in` (how many more are needed for the next level; absent at ±5), `efficiency_pct` (worker efficiency). |
| `religion` | `priests`, `blessed_pct`, `popularity_effect`, `next_level_at` (blessed percentage of the next step; absent from 95 %). |
| `army` | `troops`: `{unit name: count}` of the player's live troops and engines, without the lord; `fear_bonus`: combat modifier in percent, 5 per fear level. |
| `food` | `meat`, `cheese`, `bread`, `apples`: granary stock. |
| `population` | `history`: population at the end of each game month so far (at most 300 values). |
| `stores` | `wood`, `hops`, `stone`, `iron`, `pitch`, `wheat`, `ale`, `flour`: stockpile stock. |
| `weapons` | `bows`, `crossbows`, `spears`, `pikes`, `maces`, `swords`, `leather_armor`, `metal_armor`: armory stock. |
| `merit` | `lords`: one `{player, gold, troops}` per lord still in the game, the game's Order of Merit. |

- **Refused when:** `page` is not one of the nine names.

```python
game.report("popularity")
# {"food": 4, "tax": -2, "crowding": 0, "fear_factor": 0, "religion": 0, "ale_coverage": 0, "coming_month": 2}
```

The popularity factors are explained in the [mechanics primer](concepts.md#popularity).

See also: [state reference](reference/state.md); [refusals](reference/errors.md#report).

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

Return what the game's panel shows for one of the player's buildings.

- **Arguments:** `building_id` from `state()["buildings"]`. Other players' buildings have no panel.
- **Returns:** always `id` and `type`, then by building type:

| Building | Extra fields |
|---|---|
| `hovel` | `houses`: 8. |
| `granary` | `food_units` (total food), `months_supply` (`None` when the game shows none), `food_types_eaten`, `rations`, `rations_popularity` and `variety_popularity` (the two food factors, in displayed popularity units). The figures describe the whole town, not one granary. |
| `keep` | `peasants` (population) and `tax` (level −3 to 8). |
| towers and gatehouses | `hp`, `max_hp`. |
| `fletcher`, `poleturner`, `blacksmith` | `status`: the panel's status lines as text, when it shows any. |
| any staffed building | `worker`: the panel's worker line in the game's own words (for example that there is no worker, that it sleeps, or what the worker is doing). Absent when the panel has none. |

- **Refused when:** the ID is not an integer or not one of the player's buildings (`building N is not one of yours`).

```python
game.building_info(31)
# {"id": 31, "type": "granary", "food_units": 62, "months_supply": 5, "food_types_eaten": 2,
#  "rations": "normal", "rations_popularity": 0, "variety_popularity": 1}
```

See also: [buildings reference](reference/buildings.md); [refusals](reference/errors.md#building_info).

```python
building_info(self, building_id: int) -> BuildingInfo
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `building_id` | `int` | `required` | ID of an owned building from state buildings |

**Returns:** `BuildingInfo`

**Refusals:** See [errors for building_info](reference/errors.md#building_info); bridge-wide validation can also reject a request.

<a id="ally_order"></a>
## ally_order

Ask an ally to attack an enemy, defend the player's castle, or drop his orders.

- **Arguments:** `order` is `attack`, `defend` or `cancel`. `attack` needs `target`, the player number of an enemy whose lord is alive; the other orders must not pass a target.
- **Effect:** the ally decides when time next moves. A computer ally agrees only when his army is strong enough. If he agrees, his entry in `state()["allies"]["panel"]` shows `order` as `{"attack": player}` or `"defend"`; otherwise it stays `None`.
- **Refused when:** the player is not an ally or has no lord; `order` is not one of the three; an attack target is not an enemy with a living lord; or a target is given with `defend` or `cancel`.

```python
game.ally_order(2, "attack", target=3)
# {"queued": "ally_order", "ally": 2, "order": "attack", "target": 3, "note": "..."}
```

See also: [state reference](reference/state.md#allies); [refusals](reference/errors.md#ally_order).

```python
ally_order(self, ally: int, order: Literal['attack', 'defend', 'cancel'], target: int | None=None) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ally` | `int` | `required` | player number of an ally whose lord is alive |
| `order` | `str` | `required` | attack, defend, cancel |
| `target` | `int \| None` | `None` | enemy player ID with a living lord for attack; None for defend or cancel |

**Returns:** `CommandResult`

**Refusals:** See [errors for ally_order](reference/errors.md#ally_order); bridge-wide validation can also reject a request.

<a id="ally_send_goods"></a>
## ally_send_goods

Give goods or gold to an ally.

- **Arguments:** `good` is any good name including `gold`; `qty` is a positive multiple of 5.
- **Effect:** the goods leave the player's stock and enter the ally's when time next moves. For goods other than gold the ally needs a store with room, and only as much as fits is sent: the result's `qty` is the amount actually queued.
- **Refused when:** the player holds less than `qty`; the ally has no store for the good, or no room in it; or `qty` is not a positive multiple of 5.

```python
game.ally_send_goods(2, "wood", 25)
# {"queued": "ally_send_goods", "ally": 2, "good": "wood", "qty": 25, "note": "when game time next moves"}
```

See also: [goods reference](reference/goods.md); [refusals](reference/errors.md#ally_send_goods).

```python
ally_send_goods(self, ally: int, good: str, qty: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ally` | `int` | `required` | player number of an ally whose lord is alive |
| `good` | `str` | `required` | wood, hops, stone, iron, pitch, wheat, bread, cheese, meat, apples, ale, gold, flour, bows, crossbows, spears, pikes, maces, swords, leather_armor, metal_armor |
| `qty` | `int` | `required` | positive multiple of 5 |

**Returns:** `CommandResult`

**Refusals:** See [errors for ally_send_goods](reference/errors.md#ally_send_goods); bridge-wide validation can also reject a request.

<a id="ally_request_goods"></a>
## ally_request_goods

Ask an ally for goods.

- **Arguments:** `good` and `qty` as for `ally_send_goods`.
- **Effect:** the ally decides at once. He never gives gold and keeps a reserve of each good, so a request beyond what he will spare is refused immediately. If he agrees the goods arrive when time next moves.
- **Needs:** room in the player's own store for the full amount.
- **Refused when:** the player has no store for the good or too little room; the ally declines (`your ally refuses to give ...`); or `qty` is not a positive multiple of 5.

```python
game.ally_request_goods(2, "stone", 10)
# {"queued": "ally_request_goods", "ally": 2, "good": "stone", "qty": 10, "note": "when game time next moves"}
```

See also: [goods reference](reference/goods.md); [refusals](reference/errors.md#ally_request_goods).

```python
ally_request_goods(self, ally: int, good: str, qty: int) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ally` | `int` | `required` | player number of an ally whose lord is alive |
| `good` | `str` | `required` | wood, hops, stone, iron, pitch, wheat, bread, cheese, meat, apples, ale, gold, flour, bows, crossbows, spears, pikes, maces, swords, leather_armor, metal_armor |
| `qty` | `int` | `required` | positive multiple of 5 |

**Returns:** `CommandResult`

**Refusals:** See [errors for ally_request_goods](reference/errors.md#ally_request_goods); bridge-wide validation can also reject a request.

<a id="ally_answer"></a>
## ally_answer

Accept or refuse an ally's request for goods.

- **Arguments:** `accept` is a Boolean. The pending request is the `request` field (`{"good", "qty"}`) of the ally's entry in `state()["allies"]["panel"]`.
- **Effect:** accepting sends the requested goods exactly as `ally_send_goods` would, with the same stock and room checks; the result reports the `good` and the `qty` sent. Refusing tells the ally no. Either takes effect when time next moves.
- **Refused when:** the ally has no request outstanding, `accept` is not a Boolean, or on accepting the player lacks the goods or the ally lacks room.

```python
game.ally_answer(2, accept=False)
# {"queued": "ally_answer", "ally": 2, "accept": False, "note": "when game time next moves"}
```

See also: [state reference](reference/state.md#allies); [refusals](reference/errors.md#ally_answer).

```python
ally_answer(self, ally: int, accept: bool) -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ally` | `int` | `required` | player number of an ally whose lord is alive |
| `accept` | `bool` | `required` | True sends the requested goods; False refuses |

**Returns:** `CommandResult`

**Refusals:** See [errors for ally_answer](reference/errors.md#ally_answer); bridge-wide validation can also reject a request.

<a id="build_wall"></a>
## build_wall

Build a straight line of wall, stairs, low wall or crenellated wall.

- **Arguments:** `(x1, y1)` to `(x2, y2)` must be horizontal or vertical (`x1 == x2` or `y1 == y2`). `kind` is `wall` (default), `stairs`, `low_wall` or `crenel`. A line is at most 100 tiles, or 12 for stairs.
- **Kinds:** `wall` is the full-height stone wall. `low_wall` is lower and cheaper. `stairs` lead soldiers up onto a wall; the first tile of the line must be next to one of the player's wall tiles. `crenel` lays a taller crenellated wall beside existing wall: every new tile must touch a wall that is not part of a keep, and tiles that are already wall are left as they are and not charged.
- **Cost:** half a stone per tile, a quarter per tile for `low_wall`. The driver refuses a line the stock cannot pay for in full. The result's `stone` is the stone the game will take (negative) and `tiles` the tiles to be built.
- **Tiles:** every tile must be on the map, free (land without a building, unit, wall, tree, rock or farmland) and not part of a wall queued in this pause.
- **Timing:** the game builds the line and takes the stone when queued commands next run. Stone needed by buildings, ammunition or repairs queued in the same pause is not set aside, so if those leave too little the game ends the line short.
- **Refused when:** the kind is not one of the four; the line is diagonal or too long; a tile is off the map or not free; stairs do not start beside an own wall; a crenel tile does not touch a wall; or stone is short.
- **Afterwards:** a `build_refused` event with `tiles` and `built` is recorded if fewer tiles than ordered became wall.

```python
game.build_wall(230, 210, 240, 210)
# {"queued": "wall", "tiles": 11, "stone": -5, "note": "built when game time next moves"}
game.build_wall(235, 211, 235, 214, kind="stairs")
```

See also: [`delete_wall`](#delete_wall); [refusals](reference/errors.md#build_wall).

```python
build_wall(self, x1: int, y1: int, x2: int, y2: int, kind: str='wall') -> CommandResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `x1` | `int` | `required` | 0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise |
| `y1` | `int` | `required` | 0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise |
| `x2` | `int` | `required` | 0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise |
| `y2` | `int` | `required` | 0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise |
| `kind` | `str` | `'wall'` | wall, stairs, low_wall, crenel; stairs lines are at most 12 tiles |

**Returns:** `CommandResult`

**Refusals:** See [errors for build_wall](reference/errors.md#build_wall); bridge-wide validation can also reject a request.

<a id="advance"></a>
## advance

Run the game for 1 to 3000 ticks.

- **Arguments:** `ticks` is an integer from 1 to 3000. A month is 800 ticks; call `advance` repeatedly for longer spans.
- **Effect:** queued builds, trades, recruits and orders are applied as time starts to move, then the game runs. The driver stops exactly at the requested tick, or earlier if the game ends the match or a configured tick budget runs out.
- **Returns:** `tick` (the session tick now), `ticks_left` (the remaining budget, or `None` when no budget is configured) and `game_over` (`None`, `"match won"` or `"match lost"`). The call returns only these three fields; read what happened with `events` and `state`.
- **Events:** at each 800-tick boundary a `month_end` event is recorded and the lords are checked; after the call, builds and demolitions that the game did not carry out are recorded as `build_refused` and `demolish_refused`.
- **Duration:** a call returns when the ticks have run, which takes real time; the client's default request timeout is 600 seconds.
- **Refused when:** `ticks` is not an integer from 1 to 3000, the match has ended, or the tick budget is spent.

```python
result = game.advance(800)
# {"tick": 800, "ticks_left": None, "game_over": None}
for event in game.events():
    print(event["type"])
```

See also: [`events`](commands/observe.md#events); [time and pause](concepts.md#time-and-pause); [refusals](reference/errors.md#advance).

```python
advance(self, ticks: int) -> AdvanceResult
```

| Parameter | Type | Default | Constraints |
| --- | --- | --- | --- |
| `ticks` | `int` | `required` | 1..3000 |

**Returns:** `AdvanceResult`

**Refusals:** See [errors for advance](reference/errors.md#advance); bridge-wide validation can also reject a request.
