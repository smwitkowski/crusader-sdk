# Time commands

The game is paused between calls. `advance` is the only command that moves time, and the point at which every queued command takes effect.

## `advance`

Run the game for 1 to 3000 ticks. [API reference](../api.md#advance).

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

See also: [`events`](observe.md#events); [time and pause](../concepts.md#time-and-pause); [refusals](../reference/errors.md#advance).
