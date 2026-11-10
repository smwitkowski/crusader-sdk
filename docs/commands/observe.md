# Observe commands

These commands read the game: state, map, building sites, events and the game's information panels. They are not limited by a tick budget. After the game has ended the match, only `state` still answers; the others are refused with `game over: ...`. IDs and coordinates in examples are illustrative.

## `state`

Return the current visible game state. [API reference](../api.md#state).

- **Returns:** one `State` snapshot: clock, treasury and stock, popularity, population and housing, tax and rations, the player's buildings, every recognized unit on the map, and in a skirmish the enemy lords and buildings. Every field is described in the [state reference](../reference/state.md).
- **Use:** take unit and building IDs from it immediately before ordering; unit IDs are reused after a unit dies.
- **Refusals:** none from the driver; it also answers after the match has ended.

```python
s = game.state()
archers = [u["id"] for u in s["units"] if u["owner"] == 1 and u["type"] == "archer"]
print(s["tick"], s["gold"], s["stock"]["wood"], s["popularity"], s["idle_peasants"])
```

See also: [state reference](../reference/state.md); [refusals](../reference/errors.md#state).


## `map`

Return the inclusive tile rectangle as text. [API reference](../api.md#map).

- **Arguments:** `x0, y0, x1, y1`, each 0 to 399 with `x0 <= x1` and `y0 <= y1`. The default is the whole 400 × 400 map.
- **Returns:** newline-separated rows, one character per tile. Row 0 of the result is `y0` and column 0 is `x0`, so `rows[y - y0][x - x0]` is tile `(x, y)`. The characters are explained in the [map legend](../reference/map-legend.md): `.` open ground, `,` farmable grass, `~` water, `^` blocked or wall, letters for buildings.
- **Limits:** the map shows terrain and buildings, not units, and not builds queued in the current pause.
- **Refused when:** a coordinate is not an integer in range or the rectangle is inverted (`invalid map rectangle`).

```python
rows = game.map(220, 220, 240, 240).splitlines()
tile = rows[230 - 220][235 - 220]  # tile (235, 230)
```

See also: [map legend](../reference/map-legend.md); [refusals](../reference/errors.md#map).


## `find_sites`

Find positions where the game would accept a building now, nearest first. [API reference](../api.md#find_sites).

- **Arguments:** `building` is a placement name from the [buildings reference](../reference/buildings.md), `keep`, or a siege engine name (for its 3 × 3 tent). `limit` is 1 to 50 (default 5). `near` is the tile to search around; without it the search centres on tile (235, 230), so pass a tile near the player's keep or the resource wanted.
- **Returns:** up to `limit` sites as `{"x", "y"}` top-left tiles, nearest to `near` first, none overlapping another or a build queued in this pause. Every site has passed the map checks and the game's own placement check.
- **Limits:** the driver tests at most `10 * limit` candidates against the game, so the list can be shorter than `limit`, or empty, even when valid spots exist farther away; raise `limit` or move `near`. Cost is not checked, and a site can stop being free once time moves.
- **Refused when:** the name is not a recognized placement name, `limit` is out of range, or the map's build menu does not offer the building.

```python
sites = game.find_sites("wheat_farm", limit=3, near=(235, 230))
# [{"x": 228, "y": 236}, {"x": 240, "y": 221}]
if sites:
    game.build("wheat_farm", sites[0]["x"], sites[0]["y"])
```

See also: [`build`](economy.md#build); [refusals](../reference/errors.md#find_sites).


## `look`

Centre the camera on a tile. Always refused by the game driver. [API reference](../api.md#look).

- **Refusals:** every call fails with `camera control is not supported`. The whole map is readable through `state` and `map` without moving a camera, so nothing depends on this command.

```python
game.look(235, 230)  # raises CrusaderError
```

See also: [how it works](../how-it-works.md); [refusals](../reference/errors.md#look).


## `select`

Select owned units by ID, as a drag-select in the game does. [API reference](../api.md#select).

- **Arguments:** a list of 1 to 500 distinct IDs of the player's own live units.
- **Effect:** replaces the game's current selection and groups the units. Every order command selects its own units, so `select` is never required before an order.
- **Returns:** `{"tribe": n}`, the group number the game assigned.
- **Refused when:** the list is empty, too long or has duplicates, or an ID is not one of the player's live units.

```python
game.select([12, 13])
# {"tribe": 1249}
```

See also: [`move`](military.md#move); [refusals](../reference/errors.md#select).


## `events`

Return the session's events from a list offset onward. [API reference](../api.md#events).

- **Arguments:** `since` is an offset into the event list, 0 (the default, everything) through the current number of events. It is not a tick.
- **Returns:** a list of event objects, oldest first; `[]` when nothing is new. Each has `type` and `tick` plus the fields of its type; see the [events reference](../reference/events.md).
- **Use:** keep a count of events read and pass it as `since` after each `advance`.
- **Refused when:** `since` is negative, beyond the event count or not an integer (`invalid event offset`), and after the match has ended.

```python
seen = 0
game.advance(800)
for event in game.events(since=seen):
    print(event["type"], event["tick"])
    seen += 1
```

See also: [events reference](../reference/events.md); [refusals](../reference/errors.md#events).


## `report`

Return one page of the game's information book. [API reference](../api.md#report).

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

The popularity factors are explained in the [mechanics primer](../concepts.md#popularity).

See also: [state reference](../reference/state.md); [refusals](../reference/errors.md#report).


## `building_info`

Return what the game's panel shows for one of the player's buildings. [API reference](../api.md#building_info).

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

See also: [buildings reference](../reference/buildings.md); [refusals](../reference/errors.md#building_info).
