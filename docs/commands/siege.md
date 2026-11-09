# Siege commands

These commands construct and crew siege engines and order specialist troops.

## `build_siege`

The 3×3 tent uses `(x, y)` as its top-left tile. Available engines are `catapult`, `trebuchet`, `battering_ram`, `siege_tower`, `portable_shield` and `fire_ballista`. Engineers walk there, build and crew the engine. Gold is charged when time moves; the driver also checks wood and stone. The mission menu, placement or resources may cause refusal. The result reports gold and crew needed; the engine later appears in `state()["units"]`.

```python
game.build_siege([101, 102], "catapult", 45, 60)
```

See also: [API reference](../api.md#build_siege) and [refusals](../reference/errors.md#build_siege).


## `man`

Selected engineers walk to an owned engine and fill its vacant crew slots. The result reports `crew_needed`; a full engine is refused. At level 5 the driver checks reachability: tower engines need access via a wall and stairs.

```python
game.man([101, 102], 205)
```

See also: [API reference](../api.md#man) and [refusals](../reference/errors.md#man).


## `unman`

Order the crew of an owned, crewed engine to step off. An engine short of its full crew takes no orders; an engine with no crew is refused.

```python
game.unman(205)
```

See also: [API reference](../api.md#unman) and [refusals](../reference/errors.md#unman).


## `buy_ammo`

A catapult or trebuchet buys 20 shots for 10 stone. Other engine types and insufficient stone are refused. The queued result reports `stone` and `shots`.

```python
game.buy_ammo(205)
# {"queued": "buy_ammo", "engine_id": 205, "stone": 10, "shots": 20}
```

See also: [API reference](../api.md#buy_ammo) and [refusals](../reference/errors.md#buy_ammo).


## `throw_cow`

A crewed catapult or trebuchet throws a dairy farm cow at an on-map tile; the carcass remains where it lands. The driver refuses other engines, no crew or no cows. Returned `cows` is the count at ordering time, not proof of impact.

```python
game.throw_cow(205, 80, 70)
```

See also: [API reference](../api.md#throw_cow) and [refusals](../reference/errors.md#throw_cow).


## `set_ladder`

Select owned laddermen and an enemy wall tile. They carry and raise a ladder for soldiers to climb. Own and allied walls, non-wall tiles and other unit types are refused.

```python
game.set_ladder([301], 80, 70)
```

See also: [API reference](../api.md#set_ladder) and [refusals](../reference/errors.md#set_ladder).


## `dig_tunnel`

Select owned tunnelers and an on-map entrance tile. A tunneler digs toward the nearest enemy building; the eventual collapse damages that building. The game may refuse placement.

```python
game.dig_tunnel([302], 75, 70)
```

See also: [API reference](../api.md#dig_tunnel) and [refusals](../reference/errors.md#dig_tunnel).

