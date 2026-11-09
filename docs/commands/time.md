# Time commands

This command advances the game clock.

## `advance`

Advance by an integer from 1 to 3000 ticks. Queued actions can run and units need time to carry out orders. A finite remaining budget caps the actual advance, and a finished match can stop it early. The result contains the current `tick`, `ticks_left` (or `None` for no budget), and `game_over`; inspect state and returned `events` rather than assuming every queued action completed. `next_since` is the event sequence cursor for a later `events(since)` call, not a tick number.

```python
result = game.advance(100)
print(result["tick"], result["ticks_left"], result["game_over"])
```

See also: [API reference](../api.md#advance) and [refusals](../reference/errors.md#advance).

