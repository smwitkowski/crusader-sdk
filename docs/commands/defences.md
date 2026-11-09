# Defences commands

These commands manage gates, walls, moats, pitch, and oil.

## `set_gate`

Set an owned gatehouse or drawbridge with a Boolean `open`. The change is queued for the next time movement. A closed gate or raised drawbridge stops everyone, including your own units.

```python
game.set_gate(42, False)
```

See also: [API reference](../api.md#set_gate) and [refusals](../reference/errors.md#set_gate).


## `plan_moat`

Mark a horizontal or vertical line of at most 100 tiles, or remove a plan with `dig=False`. Planning costs nothing. The game marks acceptable land with a two-tile brush; returned `tiles` is line length, not accepted tile count. Marking occurs when time moves; use `dig_moat` to excavate.

```python
game.plan_moat(40, 50, 50, 50)
```

See also: [API reference](../api.md#plan_moat) and [refusals](../reference/errors.md#plan_moat).


## `dig_moat`

Order eligible owned diggers to a tile of your existing moat plan. They dig the plan tile by tile; dug moat blocks ground units. Other units and unplanned tiles are refused.

```python
game.dig_moat([101], 40, 50)
# {"queued": "dig_moat", "units": 1, "x": 40, "y": 50}
```

See also: [API reference](../api.md#dig_moat) and [refusals](../reference/errors.md#dig_moat).


## `fill_moat`

Order eligible owned diggers to fill an enemy dug moat tile with earth. Your own or allied moat, an undug plan, and non-diggers are refused. Filling takes unit action.

```python
game.fill_moat([101], 80, 70)
```

See also: [API reference](../api.md#fill_moat) and [refusals](../reference/errors.md#fill_moat).


## `delete_wall`

Queue removal of one owned wall tile. Removal occurs when time moves; the result notes a half-stone refund, which the game halves again for a low wall. This does not remove moat plans or pitch; use `plan_moat(..., dig=False)` for a plan.

```python
game.delete_wall(40, 50)
```

See also: [API reference](../api.md#delete_wall) and [refusals](../reference/errors.md#delete_wall).


## `light_pitch`

Select archers or Arabian archers and a friendly-team pitch ditch in reach. The first selected unit must be within three tiles of a lit friendly brazier; range is checked from that unit. They shoot burning arrows to ignite the ditch.

```python
game.light_pitch([101], 45, 50)
```

See also: [API reference](../api.md#light_pitch) and [refusals](../reference/errors.md#light_pitch).


## `oil_duty`

Assign owned engineers to an owned oil smelter. They work it and can receive oil pots. Other unit or building types are refused. The separate `pour_oil` command is currently unavailable.

```python
game.oil_duty([101], 42)
```

See also: [API reference](../api.md#oil_duty) and [refusals](../reference/errors.md#oil_duty).


## `pour_oil`

The driver currently refuses this order: the game’s pour click has not been reproduced, and a direct ground order was observed to leave a carrier waiting. It first checks for engineers and at least one carried pot, so those errors may appear instead. Use `oil_duty` to assign engineers, but do not rely on this command to pour.

```python
game.pour_oil([101], 45, 50)  # currently refused
```

See also: [API reference](../api.md#pour_oil) and [refusals](../reference/errors.md#pour_oil).


## `build_wall`

Build a horizontal or vertical line; `kind` defaults to `"wall"` and can also select stairs or crenellations. Lines are limited to 100 tiles, or 12 for stairs. Ordinary wall costs half a stone per tile; low wall costs a quarter per tile. The driver checks affordability and placement before queuing. Stairs must start next to your wall; crenellations are laid beside an existing non-keep wall. The game builds and charges on the next command-processing frame. Stone promised to buildings, ammo or repair in the same pause is not reserved, so a line can end short.

```python
game.build_wall(40, 50, 50, 50)
```

See also: [API reference](../api.md#build_wall) and [refusals](../reference/errors.md#build_wall).

