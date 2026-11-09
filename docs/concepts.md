# Concepts

## Time and pause

The real driver uses a game module to pause at a target tick. `advance(ticks)` requests 1–3000 ticks, then returns the current tick, remaining budget if configured, and game-over status. A match can end before the requested interval. A game month is 800 ticks. Do not assume a command's effects are immediate: advance time and inspect state again.

## Coordinates and IDs

Map coordinates are tile `(x, y)` pairs; map rectangles are inclusive. A building's coordinates identify the top-left tile of its footprint. Use `find_sites` to find candidate positions, then handle refusal because game conditions can change. Unit and building IDs come from state; they refer to the current game, not stable identities across matches. Most orders require owned units or buildings. Enemy targets and allies have command-specific rules.

## Events and refusals

`events(since)` uses an event-list offset; after reading a batch, advance the offset by its length. The real backend checks that the offset is between zero and the current event count. Event fields vary. The published `AdvanceResult` type mentions `events` and `next_since`, but the current real backend does not return them from `advance`; use `events` separately. Similarly, the backend's events do not necessarily contain the `seq` declared by the public type. See [events](reference/events.md).

A command may be refused by validation or game conditions. The client raises `CrusaderError` for bridge error responses. A successful request does not guarantee an order will achieve its intended outcome; inspect subsequent state and events. See [errors](reference/errors.md).
