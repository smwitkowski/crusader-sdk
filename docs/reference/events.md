# Events

`events(since=0)` returns the event list from the zero-based offset `since`; it must be an integer from zero through the current event count, inclusive. Use `next_since` from an advance result as the next offset. The driver stores `type` and driver-relative `tick` on every event. It does **not** add the `seq` required by the public `Event` TypedDict; `month` and `message` are optional in that type, not universal fields. TypedDicts describe responses and do not validate them.

| `type` | Additional fields and meaning |
| --- | --- |
| `lord_died` | The player's starting lord is no longer alive; emitted once when tracked. |
| `enemy_lord_died` | `player`: owner of a starting enemy lord, emitted once per lord. |
| `match_end` | `result` is `won` or `lost`. Mission events also have `game_over_flag`, `menu`, and `winners` (eight player flags); skirmish events instead have `winner` (1 on a win, otherwise a list of surviving enemy player IDs or `None`). |
| `month_end` | `month` (completed driver months), `gold`, `popularity`, `population`, `game_tick` (absolute game tick), `army`, `enemy_army`, `lord_alive`. AI games add `enemy_buildings` and `enemy_lords_alive`; missions with AI also add `enemy_lord_hp` (player IDs as string keys) and `lord_hp`. |
| `build_refused` | `building`, `x`, `y`; ordinary builds add `reason`, while wall lines add `tiles` and `built`. Detection occurs after time moves. |
| `demolish_refused` | `building_id` and `type` identify the building still present after time moves. Here `type` overwrites the event kind in the emitted dictionary: the actual returned `type` is the building type, not `demolish_refused`. |
| `order_stalled` | `cmd`, `ordered_at`, `units` (count), target fields (`x` and `y`, `target_id`, or `building_id`), `at` (first surviving unit's coordinates), and `note`. Mission order monitoring emits it when an order appears dropped. |

The watcher docstring also mentions siege arrival and defeat, but the current emission sites do not emit those events. `AdvanceResult` declares `tick`, `ticks_left`, `game_over`, `events`, and `next_since`; as in state, an unlimited budget can make `ticks_left` null despite its declared integer type.
