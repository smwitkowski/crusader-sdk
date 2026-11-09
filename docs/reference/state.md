# State

`state()` returns visible game state. These TypedDicts describe responses; they do not validate them at runtime.

| Field | Meaning |
| --- | --- |
| `tick`, `month` | Driver-relative elapsed ticks and completed months, respectively. |
| `ticks_per_month`, `ticks_left` | Month length (800 ticks) and remaining budget. `ticks_left` can be `None` with no budget despite its declared `int` type. |
| `game_over` | End reason or `None`. |
| `gold`, `stock` | Gold and named goods; gold also appears in `stock`. |
| `popularity`, `population`, `housing` | Current player values. |
| `tax`, `rations` | Tax is the raw value minus 3; rations is a name for recognized values, otherwise the raw number. |
| `date` | Game `month` and `year`, distinct from completed driver months. |
| `buildings` | Player-owned buildings, each with `id`, `type`, `x`, `y`. |
| `idle_peasants`, `units`, `lord_alive` | Idle peasant count, visible units and tracked player lord status. |

Each unit has `id`, `type`, `owner`, `x`, `y`, `hp`. At level 3 or higher, player-owned catapults and trebuchets include `ammo`; `cows` is included when positive. Missions exclude units with zero HP; non-missions may list them.

Mode-specific fields:

- `enemy` appears in AI games, with `lords` and `buildings`. Each enemy building has `id`, `type`, `x`, `y`, `owner`, `hp`, `max_hp`.
- `mission` appears when set.
- `allies` appears when allies exist: `players` is a sorted list of player IDs, `lords` is a list of lord records, and at level 6 or higher `panel` has one entry per ally. Each panel entry has `player`, `request` (`None` or `{good, qty}`), and `order` (`None`, `defend`, or `{attack: target}`).

Each enemy or ally lord record has `owner` and `alive`; a live lord additionally has `id`, `x`, `y`, `hp`. See [units](units.md) and [buildings](buildings.md).

`RawState` is a separate direct-memory snapshot: `tick` (absolute game tick), `paused`, `month`, `year`, `tax`, `rations`, `popularity`, `population`, `housing`, and `stock`. Tax and rations are raw, not normalized as in `State`.
