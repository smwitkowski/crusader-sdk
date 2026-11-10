# State

`state()` returns one snapshot of the game as the player sees it. It is the only command that still answers after the match has ended. The `State` TypedDict describes the response; it is not validated at runtime.

## Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `tick` | `int` | Ticks elapsed in this session (0 when the session starts, also for a loaded save). |
| `month` | `int` | Months completed in this session; a month is 800 ticks. |
| `ticks_per_month` | `int` | Always 800. |
| `ticks_left` | `int` or `None` | Remaining tick budget. `None` when the backend was started without a budget, which is the case for the bridge's built-in match types. |
| `game_over` | `str` or `None` | `None` while the match runs; `"match won"` or `"match lost"` once the game has ended it. After that every other command is refused. |
| `gold` | `int` | Treasury. Same value as `stock["gold"]`. |
| `popularity` | `float` | 0 to 100. Peasants arrive while it is 50 or more and leave below 50. |
| `population` | `int` | Peasants in the town, working or idle. |
| `housing` | `int` | Room for peasants; each hovel adds 8. |
| `tax` | `int` | Tax level, -3 to 8: negative levels are bribes, 0 is no tax. |
| `rations` | `str` | `"none"`, `"half"`, `"normal"`, `"extra"` or `"double"`. (An unrecognized raw value would be returned as an integer.) |
| `stock` | `dict[str, int]` | Amount held of every good; see [goods](goods.md). |
| `date` | `{month, year}` | The in-game calendar: `month` 0 to 11 (0 is January) and the year. Independent of the session's `month` counter. |
| `buildings` | `list[Building]` | The player's buildings. |
| `idle_peasants` | `int` | Peasants at the campfire who could be recruited now. Peasants still walking in from the map edge do not count. |
| `units` | `list[Unit]` | Every recognized live unit on the map, of all players. |
| `lord_alive` | `bool` | `False` once the player's lord has been seen dead. |
| `enemy` | `Enemy` | Skirmish sessions only; see below. |
| `allies` | `Allies` | Present only when the session has allied players; see below. |
| `mission` | `str` | Present only for a backend started in mission mode. |

## `Building`

| Field | Type | Meaning |
|---|---|---|
| `id` | `int` | Building ID for `demolish`, `repair`, `building_info`, `set_gate` and the other building commands. |
| `type` | `str` | Building name; see [buildings](buildings.md). Gardens read back as `garden` and turned gatehouses as `gatehouse` or `large_gatehouse`. |
| `x`, `y` | `int` | Top-left tile of the footprint. |

The keep is listed with type `keep`. Walls, moats, braziers and flags are not buildings and are not listed; walls show as `^` on the map.

## `Unit`

| Field | Type | Meaning |
|---|---|---|
| `id` | `int` | Unit ID for orders. IDs are reused after a unit dies. |
| `type` | `str` | Unit or siege engine name; see [units](units.md). |
| `owner` | `int` | Player number; 1 is the controlled player. |
| `x`, `y` | `int` | Tile position. |
| `hp` | `int` | Raw health. A unit with `hp` 0 is dying and disappears within a few ticks. |
| `ammo` | `int` | Own catapults and trebuchets only: shots left. |
| `cows` | `int` | Own catapults and trebuchets only, and only while the player has cows: the number of cows available to `throw_cow`. |

The player's own lord is in this list (`type` `"lord"`, `owner` 1). Peasants, workers, animals and other map creatures are not listed.

## `enemy`

Present in skirmish sessions, where the whole map is visible.

| Field | Type | Meaning |
|---|---|---|
| `lords` | `list[Lord]` | One record per enemy lord the driver recorded when the session began. |
| `buildings` | `list[EnemyBuilding]` | Buildings owned by those lords: `id`, `type`, `x`, `y`, `owner`, `hp`, `max_hp`. Use `id` with `attack_building`. A keep has `hp` and `max_hp` 0 and cannot be damaged; a lord is beaten by killing him. |

A `Lord` record has `owner` (player number) and `alive`. While the lord is alive it also has `id`, `x`, `y` and `hp`; use `id` as the `target_id` of `attack`.

## `allies`

Present only when the session has allied players. The bridge's built-in match types start without allies, so this key is absent and the ally commands are refused.

| Field | Type | Meaning |
|---|---|---|
| `players` | `list[int]` | Sorted allied player numbers. |
| `lords` | `list[Lord]` | One `Lord` record per ally, as above. |
| `panel` | `list[AllyPanel]` | Per ally: `player`; `request`, the goods the ally has asked the player for (`{"good", "qty"}` or `None`); and `order`, the ally's current order (`None`, `"defend"`, or `{"attack": player}`). |

## Related results

- `advance(ticks)` returns `{"tick", "ticks_left", "game_over"}` with the same meanings as above. The published `AdvanceResult` type also declares `events` and `next_since`; the driver does not return them, so read events with [`events`](events.md).
- `report(page)` and `building_info(building_id)` return the figures of the game's information panels; their fields are listed with those commands in the [observe commands](../commands/observe.md).
- `RawState` is the driver's internal memory snapshot and is not returned by any bridge command: `tick` (the game's absolute tick), `paused`, `month`, `year`, `tax` (raw 0 to 11, where 3 is no tax), `rations` (raw 0 to 4), `popularity`, `population`, `housing` and `stock`.
