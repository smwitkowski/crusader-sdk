# Observe commands

These commands inspect visible state, map tiles, events, reports, and owned objects. Some also change the camera or selection. IDs and coordinates below are illustrative.

## `state`

Return the current visible game state. [API reference](../api.md#state).

Returns `State`; use its owned units and buildings to choose IDs for orders. Enemy information is limited to visible state. Unit IDs can be reused after death, so read them fresh before ordering.

```python
game.state()
```

The returned `State` includes `tick`, `stock`, `units`, and `buildings`; values depend on the running game.

See also: [related reference](../reference/state.md); [refusals](../reference/errors.md#state).


## `map`

Return the inclusive tile rectangle as text. The default rectangle runs from (0, 0) through (399, 399), inclusive. [API reference](../api.md#map).

Returns a string. Invalid rectangles are refused; coordinates include both endpoints.

```python
game.map(220, 220, 240, 240)
```

The return is a newline-separated string; the result contents depend on the terrain.

See also: [related reference](../reference/map-legend.md); [refusals](../reference/errors.md#map).


## `find_sites`

Find valid building sites, optionally near a tile. The optional near tile narrows the search around a location; the default limit is 5. [API reference](../api.md#find_sites).

Returns `list[Site]`. `limit` must be 1–50; unknown or unavailable buildings are refused. Without `near`, the driver searches around the mission keep, otherwise (235, 230). Queued builds are treated as occupied, even before the map shows them. A site does not guarantee that you can afford a build.

```python
game.find_sites("woodcutter", limit=3, near=(235, 230))
```

Each returned site has `x` and `y`; the list may be empty.

See also: [related reference](economy.md#build); [refusals](../reference/errors.md#find_sites).


## `look`

Centre the camera on a tile and return its visible area. [API reference](../api.md#look).

The current real backend refuses camera control; do not rely on this command to reveal an area.

```python
game.look(235, 230)
```

See also: [related reference](../how-it-works.md); [refusals](../reference/errors.md#look).


## `select`

Select owned soldiers by ID. [API reference](../api.md#select).

Pass 1–500 distinct IDs of your live soldiers. Invalid, enemy, or dead units are refused. Selection changes the game selection.

```python
game.select([12, 13])
```

On success the return has a `tribe` field; its value is assigned by the game.

See also: [related reference](military.md#move); [refusals](../reference/errors.md#select).


## `events`

Return events with sequence numbers at or after since. The since value is inclusive and defaults to 0. [API reference](../api.md#events).

The driver treats `since` as an inclusive offset into its event list, from 0 through the current event count. An invalid offset is refused. Use `next_since` from `advance()` to fetch newer events; this is not a tick number. Event fields vary; do not assume optional fields are present.

```python
game.events(since=0)
```

If there are no events at or after the offset, the return is `[]`.

See also: [related reference](../reference/events.md); [refusals](../reference/errors.md#events).


## `report`

Return a page of the scribe's book. Pages: popularity, fear, religion, army, food, population, stores, weapons, merit. [API reference](../api.md#report).

Returns a report page; availability and fields depend on the page and game state.

```python
game.report("food")
```

Returned fields vary by page: for example the army page returns `troops` and `fear_bonus`.

See also: [related reference](../reference/state.md); [refusals](../reference/errors.md#report).


## `building_info`

Return the panel information for an owned building. [API reference](../api.md#building_info).

Pass an owned building ID from state; the panel data depends on building type. An invalid or non-owned ID is refused.

```python
game.building_info(12)
```

Returned fields include `id` and `type`, with additional fields according to the panel.

See also: [related reference](../reference/state.md); [refusals](../reference/errors.md#building_info).

