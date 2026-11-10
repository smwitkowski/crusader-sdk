# Defences commands

These commands build and operate castle defences: walls, gates, moats, pitch and oil. Towers, gatehouses, drawbridges, killing pits, pitch ditches, dog cages, braziers and tower engines are placed with [`build`](economy.md#build). Unit lists follow the rules of the [military commands](military.md): 1 to 500 distinct IDs of the player's own live units. Every command is refused after the match has ended or a tick budget is spent. IDs and coordinates in examples are illustrative.

## `set_gate`

Open or close an owned gatehouse or drawbridge. [API reference](../api.md#set_gate).

- **Arguments:** `building_id` of an owned `gatehouse`, `large_gatehouse` or `drawbridge`; `open` is a Boolean.
- **Effect:** an open gate lets units through. A closed gate, or a raised drawbridge, stops every ground unit, the player's own included. The gate starts to move when time next moves and takes a short while to finish.
- **Refused when:** the building is not the player's, is not a gatehouse or drawbridge, or `open` is not a Boolean.

```python
game.set_gate(42, False)
# {"queued": "set_gate", "building_id": 42, "open": False, "note": "when game time next moves"}
```

See also: [`build`](economy.md#build); [refusals](../reference/errors.md#set_gate).


## `build_wall`

Build a straight line of wall, stairs, low wall or crenellated wall. [API reference](../api.md#build_wall).

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

See also: [`delete_wall`](#delete_wall); [refusals](../reference/errors.md#build_wall).


## `delete_wall`

Remove one owned wall tile. [API reference](../api.md#delete_wall).

- **Arguments:** `(x, y)` must be a wall or stairs tile owned by the player.
- **Effect and timing:** the tile is removed when time next moves and the game refunds half of its stone (half of that again for a low wall); a single tile's refund can round down to nothing.
- **Limits:** only walls. A moat plan is removed with `plan_moat(..., dig=False)`; pitch ditches, towers and gatehouses are buildings and are removed with `demolish`.
- **Refused when:** the tile is not one of the player's wall tiles.

```python
game.delete_wall(230, 210)
# {"queued": "delete_wall", "x": 230, "y": 210, "note": "removed when game time next moves; half its stone is refunded"}
```

See also: [`build_wall`](#build_wall); [refusals](../reference/errors.md#delete_wall).


## `plan_moat`

Mark, or unmark, a straight line of moat to be dug. [API reference](../api.md#plan_moat).

- **Arguments:** a horizontal or vertical line of at most 100 tiles; `dig=True` (default) marks the plan, `dig=False` removes a plan along the line.
- **Effect:** the game marks the plan with a two-tile brush on the tiles it accepts (land without buildings or walls), so the marked strip can be wider than the line. Planning costs nothing. A plan does not block anything until dug.
- **Returns:** `queued` (`"plan_moat"` or `"unplan_moat"`), `tiles` (the length of the line, not the number of tiles the game marked) and `note`.
- **Timing:** marked when time next moves.
- **Refused when:** the line is diagonal, longer than 100 tiles or leaves the map, or `dig` is not a Boolean.

```python
game.plan_moat(228, 230, 236, 230)
# {"queued": "plan_moat", "tiles": 9, "note": "marked when game time next moves"}
```

See also: [`dig_moat`](#dig_moat); [refusals](../reference/errors.md#plan_moat).


## `dig_moat`

Order units to dig out the player's moat plan. [API reference](../api.md#dig_moat).

- **Units:** archers, spearmen, pikemen, macemen, engineers and slaves.
- **Arguments:** `(x, y)` must be a tile of the moat plan, so advance at least one tick after `plan_moat` before ordering.
- **Effect:** the units walk to the plan and dig it out tile by tile, continuing along the plan. A dug tile is moat, which ground units cannot cross. Digging takes time (measured: four spearmen dug three tiles in about 600 ticks).
- **Refused when:** a listed unit cannot dig, or the tile is not part of the moat plan.

```python
game.dig_moat([101, 102], 230, 230)
# {"queued": "dig_moat", "units": 2, "x": 230, "y": 230}
```

See also: [`plan_moat`](#plan_moat); [refusals](../reference/errors.md#dig_moat).


## `fill_moat`

Order units to fill an enemy's dug moat tile. [API reference](../api.md#fill_moat).

- **Units:** the same diggers as `dig_moat`.
- **Arguments:** `(x, y)` must be a dug moat tile belonging to another team.
- **Effect:** the units carry earth into the moat until the tile is land again.
- **Refused when:** a listed unit cannot dig; the tile is not dug moat; or the moat is the player's own or an ally's. The player's own moat cannot be filled.

```python
game.fill_moat([101], 80, 70)
# {"queued": "fill_moat", "units": 1, "x": 80, "y": 70}
```

See also: [`dig_moat`](#dig_moat); [refusals](../reference/errors.md#fill_moat).


## `light_pitch`

Order archers to set one of the player's pitch ditches alight. [API reference](../api.md#light_pitch).

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

See also: [`build`](economy.md#build); [refusals](../reference/errors.md#light_pitch).


## `oil_duty`

Assign engineers to an owned oil smelter. [API reference](../api.md#oil_duty).

- **Arguments:** `engineer_ids` are engineers; `smelter_id` is an owned `oil_smelter`.
- **Effect:** one engineer works the smelter, which boils pitch from the stockpile into oil; the others wait and each receives a pot of boiling oil. The smelter needs pitch in the stockpile.
- **Limits:** pouring the oil is not available; see `pour_oil`.
- **Refused when:** a listed unit is not an engineer, or the building is not an owned oil smelter.

```python
game.oil_duty([101, 102], 42)
# {"queued": "oil_duty", "units": 2, "smelter_id": 42}
```

See also: [`pour_oil`](#pour_oil); [refusals](../reference/errors.md#oil_duty).


## `pour_oil`

Order engineers to pour boiling oil. Always refused by the game driver. [API reference](../api.md#pour_oil).

- **Status:** the driver cannot yet reproduce the game's pour action, so every call is refused rather than queue an order that would do nothing. The final refusal reads `pouring oil is not available yet`.
- **Earlier refusals:** the driver first checks that the listed units are engineers and that at least one carries an oil pot, so those messages can appear instead.

```python
game.pour_oil([101], 232, 236)  # raises CrusaderError
```

See also: [`oil_duty`](#oil_duty); [refusals](../reference/errors.md#pour_oil).
