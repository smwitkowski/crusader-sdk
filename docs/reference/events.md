# Events

The driver keeps one append-only event list per session. `events(since=0)` returns the events from list offset `since` onward; `since` must be an integer from 0 through the current event count. To read only new events, remember how many have been read and pass that count:

```python
seen = 0
game.advance(800)
new = game.events(since=seen)
seen += len(new)
```

Events are produced while `advance` runs. `advance` itself returns `tick`, `ticks_left` and `game_over`; it does not return the events, so call `events` afterwards. Once the match has ended, `events` is refused like every command except `state` (`game over: ...`), so events recorded during the advance that ended the match, including `match_end`, cannot be read back; use `State.game_over` for the result.

## Common fields

Every event has:

| Field | Type | Meaning |
|---|---|---|
| `type` | `str` | The event kind, one of the headings below. `demolish_refused` is the exception described there. |
| `tick` | `int` | Session tick at which the driver recorded the event (the same clock as `State.tick`). |

The published `Event` type also declares `seq`, `month` and `message`. The driver does not set `seq` or `message`; `month` is present only on `month_end`. Use the list offset as the cursor.

## Event types

### `month_end`

Emitted when the session clock crosses each 800-tick month boundary.

| Field | Type | Meaning |
|---|---|---|
| `month` | `int` | Number of months completed in this session (1 for the first). |
| `gold` | `int` | Treasury at the boundary. |
| `popularity` | `float` | Popularity (0 to 100) at the boundary. |
| `population` | `int` | Peasants in the town. |
| `game_tick` | `int` | The game's own absolute tick counter, which differs from `tick` in a loaded save. |
| `army` | `int` | Own live soldiers, not counting the lord or siege engines. |
| `enemy_army` | `int` | Live soldiers and lords of other, non-allied players. |
| `lord_alive` | `bool` | `False` once the player's lord has died. |
| `enemy_buildings` | `int` | Skirmish only: buildings owned by the enemy lords. |
| `enemy_lords_alive` | `int` | Skirmish only: enemy lords not yet seen dead. |
| `enemy_lord_hp` | `dict[str, int]` | Mission sessions only: health per enemy lord, keyed by player number as a string. |
| `lord_hp` | `int` | Mission sessions only: the player's lord's health, 0 once dead. |

### `lord_died`

The player's starting lord is no longer a live unit with health. No extra fields. Emitted once. Lords are checked at every month boundary and when the game ends the match, so the event's `tick` can be later than the death.

### `enemy_lord_died`

| Field | Type | Meaning |
|---|---|---|
| `player` | `int` | Player number of the enemy lord that died. |

Emitted once per enemy lord the driver recorded at session start, on the same schedule as `lord_died`.

### `match_end`

The game ended the match. In a skirmish the game does this shortly after a lord dies. `State.game_over` becomes `"match won"` or `"match lost"` at the same time and further commands are refused.

| Field | Type | Meaning |
|---|---|---|
| `result` | `str` | `"won"` or `"lost"`. |
| `winner` | `int`, `list[int]` or `None` | Skirmish: `1` on a win, otherwise the sorted player numbers of the surviving enemy lords, or `None` if there are none. |
| `game_over_flag` | `int` | Mission sessions: the game's game-over flag. |
| `menu` | `int` | Mission sessions: the menu the game went to after the match. |
| `winners` | `list[int]` | Mission sessions: eight flags, one per player 1 to 8, 1 for each winner. |

### `build_refused`

A queued placement was not on the map after time moved. Checked at the end of the `advance` call that followed the command.

| Field | Type | Meaning |
|---|---|---|
| `building` | `str` | The placement name, the siege engine name for a siege tent, or the wall kind for a wall line. |
| `x`, `y` | `int` | The top-left tile ordered; for a wall line, its first tile. |
| `reason` | `str` | Buildings and tents: the game's reason, asked again at detection time, or `"the spot was not free when time moved"`. |
| `tiles` | `int` | Wall lines: tiles ordered. |
| `built` | `int` | Wall lines: tiles that became wall. A line ends short when the stone runs out. |

### `demolish_refused`

A building queued for demolition is still standing after time moved.

| Field | Type | Meaning |
|---|---|---|
| `building_id` | `int` | The building's ID. |
| `type` | `str` | The **building type** (for example `"woodcutter"`), not the string `demolish_refused`. This event's building type overwrites its kind, so recognize it as an event that has `building_id` and no `building` field. |

### `order_stalled`

Mission sessions only. A `move`, `attack` or `attack_building` order whose soldiers have all stood still for 200 ticks without arriving (within 4 tiles), losing health or hurting the target; the game usually dropped the order because the tile is unreachable or the path blocked. Emitted once per order.

| Field | Type | Meaning |
|---|---|---|
| `cmd` | `str` | `"move"` or `"attack"`. |
| `ordered_at` | `int` | Session tick of the order. |
| `units` | `int` | Number of units ordered. |
| `x`, `y` | `int` | For a move: the destination. |
| `target_id` | `int` | For an attack on a unit. |
| `building_id` | `int` | For an attack on a building. |
| `at` | `list[int]` | `[x, y]` of the first surviving unit. |
| `note` | `str` | Fixed explanatory text. |

## Session kinds

The bridge's built-in match types are a new skirmish against one computer lord, a Castle Builder match and a loaded save. Skirmish sessions emit every event above except `order_stalled` and the mission-only fields. Castle Builder and loaded-save sessions track no enemy lords: they emit `month_end` (without the skirmish fields), `lord_died`, `build_refused` and `demolish_refused`, and never `match_end`. Mission-only events and fields apply to a backend started in mission mode, which the built-in match types do not use.
