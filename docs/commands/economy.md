# Economy commands

These commands manage construction, taxes, food, trade, recruitment and building upkeep. All of them are refused once the match has ended (`game over: ...`) or a configured tick budget is spent (`tick budget exhausted`). Unless stated otherwise a command is queued and the game applies it when time next moves, so call `advance` before reading its effect. Within one pause the driver reserves the gold, goods and peasants that queued trades and recruits will use, and treats queued building sites as occupied. IDs and coordinates in examples are illustrative.

## `build`

Place a building at the top-left tile of its footprint. [API reference](../api.md#build).

- **Arguments:** `building` is a placement name from the [buildings reference](../reference/buildings.md), which lists every footprint, cost and placement rule; `(x, y)` is the footprint's top-left tile. Use `find_sites` to get tiles the game accepts.
- **Checks, in order:** the map (every footprint tile on the map, free, level, and for farms farmable, for an iron mine on ore); the game's own placement check (adjacency, distance to the enemy and to the castle); the map's build menu; then the cost, read from the game's cost table, against the current stock of wood, stone, gold, iron and pitch. A drawbridge must also sit in front of the gate of an owned gatehouse.
- **Effect and timing:** the game takes the cost and places the building when time next moves. A staffed building then waits for a free peasant before it works.
- **Special names:** `flag_1` to `flag_4`, `heads` and `brazier` go on top of an owned wall or tower; `mangonel` and `ballista` go on a tower-top tile of an owned square or round tower that has no engine, and then need 2 engineers (`man`).
- **Refused when:** the name is not recognized; a tile fails the map check (the message names the tile and what blocks it); the game refuses the spot (the message carries the game's reason); the build menu does not offer the building; or the stock is short (the message gives the amounts needed and held).
- **Afterwards:** if the spot is no longer free when time moves, a `build_refused` event with a `reason` is recorded and nothing is charged.

```python
site = game.find_sites("woodcutter", limit=1, near=(235, 230))[0]
game.build("woodcutter", site["x"], site["y"])
# {"queued": "woodcutter", "x": 235, "y": 230, "note": "placed when game time next moves"}
```

See also: [`find_sites`](observe.md#find_sites); [buildings reference](../reference/buildings.md); [refusals](../reference/errors.md#build).


## `demolish`

Demolish an owned building. [API reference](../api.md#demolish).

- **Arguments:** `building_id` from `state()["buildings"]`.
- **Effect and timing:** the game removes the building when time next moves and refunds half of its cost. Its worker returns to the campfire.
- **Refused when:** the ID is not one of the player's buildings, or it is the keep (`the keep cannot be demolished`).
- **Afterwards:** a `demolish_refused` event is recorded if the building is still standing after time moved.

```python
game.demolish(12)
# {"queued": "demolish", "building_id": 12, "type": "woodcutter", "note": "removed when game time next moves; part of its cost is refunded"}
```

See also: [`events`](observe.md#events); [refusals](../reference/errors.md#demolish).


## `set_tax`

Set the tax level, from -3 to 8. [API reference](../api.md#set_tax).

- **Levels:** −3 to −1 are bribes paid to the population out of the treasury, 0 is no tax, 1 to 8 are increasingly heavy taxes.
- **Popularity:** each level has a fixed monthly popularity effect: −3: +7, −2: +5, −1: +3, 0: +1, 1: −2, 2: −4, 3: −6, 4: −8, 5: −12, 6: −16, 7: −20, 8: −24.
- **Gold:** tax grows with the level and the population. The game accumulates it weekly and pays it into the treasury at the end of each game month, so receipts trail a change by up to a month. Bribes are deducted the same way.
- **Timing:** the level changes when time next moves and shows as `State.tax`.
- **Refused when:** `level` is not an integer from −3 to 8.

```python
game.set_tax(1)
# {"tax": 1}
```

See also: [`report`](observe.md#report); [popularity](../concepts.md#popularity); [refusals](../reference/errors.md#set_tax).


## `set_rations`

Set the ration level: none, half, normal, extra or double. [API reference](../api.md#set_rations).

- **Popularity:** `none` −8, `half` −4, `normal` 0, `extra` +4, `double` +8 a month. With no food in the granary the effect is −8 whatever the setting.
- **Food:** higher rations empty the granary faster in proportion.
- **Timing:** the level changes when time next moves and shows as `State.rations`.
- **Refused when:** `level` is not one of the five names.

```python
game.set_rations("extra")
# {"rations": "extra"}
```

See also: [`report`](observe.md#report); [food and rations](../concepts.md#food-and-rations); [refusals](../reference/errors.md#set_rations).


## `trade`

Buy or sell goods at the market in multiples of five. Positive quantities buy; negative quantities sell. [API reference](../api.md#trade).

- **Needs:** an owned `market`, and a good the map allows to be traded. Gold itself cannot be traded.
- **Arguments:** `qty` is a non-zero multiple of 5 with an absolute value of at most 500.
- **Buying:** costs the game's current buy price per lot of 5. The driver refuses a purchase the treasury cannot cover after other spending queued in this pause. If the good's store has no room when time moves, the game buys nothing and keeps the gold.
- **Selling:** earns the current sell price per 5. The game sells in lots sized by the stock at each sale: everything below 5 in stock, 5 at a time below 50, 10 below 100, 20 below 200, otherwise 50. The requested amount must be reachable exactly with those lots; for example 15 can be sold from a stock of 40 (three lots of 5) but not from a stock of 120 (lots of 20).
- **Returns:** `queued` (`"buy"` or `"sell"`), `good`, `qty`, `gold` (negative for the cost of a purchase, positive for the proceeds of a sale) and `note`.
- **Timing:** executed when time next moves.
- **Refused when:** the good is not recognized or `cannot be traded`; `qty` is zero, not a multiple of 5 or over 500; there is no market; gold is short; or the sale cannot be made in the game's lot sizes.

```python
game.trade("wood", 10)  # buy 10 wood
game.trade("apples", -20)  # sell 20 apples
# {"queued": "sell", "good": "apples", "qty": -20, "gold": 16, "note": "sold when game time next moves"}
```

See also: [goods reference](../reference/goods.md#trading); [refusals](../reference/errors.md#trade).


## `recruit`

Recruit soldiers, mercenaries or specialists from idle peasants. [API reference](../api.md#recruit).

- **Arguments:** `unit` is a name from the [units reference](../reference/units.md), which lists every price and the goods each unit uses; `count` is 1 to 50 (default 1).
- **Needs, per recruit:** one idle peasant at the campfire (`State.idle_peasants`), the gold price, and the recruiting building: a `barracks` for archers, crossbowmen, spearmen, pikemen, macemen, swordsmen and knights; a `mercenary_post` for the seven Arabian units; an `engineers_guild` for engineers and laddermen; a `tunnelers_guild` for tunnelers; a `cathedral` for monks. Barracks troops also use one of each of their weapons and armor from the armory, and a knight uses one horse from the stables.
- **Effect and timing:** the game takes the gold and goods when time next moves. A barracks soldier appears about 40 ticks later, when his peasant has walked to the barracks; other recruits walk from the campfire to their building in the same way. The new unit then appears in `State.units`.
- **Returns:** `queued` (the unit name), `count`, `gold` (the total cost, negative) and `note`.
- **Refused when:** the unit name is not recognized; `count` is out of range; the map does not offer the unit; the building is missing; or gold, a weapon, armor, horses or idle peasants are short. The message names what is missing and how much is available after earlier commands of the same pause.

```python
game.recruit("archer", count=2)
# {"queued": "archer", "count": 2, "gold": -24, "note": "paid when game time next moves; each soldier appears at the barracks ~40 ticks later"}
```

See also: [units reference](../reference/units.md); [refusals](../reference/errors.md#recruit).


## `repair`

Repair a damaged owned tower or gatehouse to full health. [API reference](../api.md#repair).

- **Applies to:** `lookout_tower`, `perimeter_tower`, `defense_turret`, `square_tower`, `round_tower`, `gatehouse` and `large_gatehouse`. Other buildings have no repair.
- **Cost:** the game computes it from the damage: the missing share of the building's health times its wood and stone cost, at least 1 of each material the building costs. The amounts are returned as `wood` and `stone`.
- **Timing:** health is restored and the cost charged when time next moves.
- **Refused when:** the building is not the player's or not repairable; it is not damaged; an enemy unit is near it (within 15 tiles in a match against computer lords, 30 otherwise); or wood or stone is short.

```python
game.repair(12)
# {"queued": "repair", "building_id": 12, "wood": 0, "stone": 9, "note": "repaired to full hp when game time next moves"}
```

See also: [`building_info`](observe.md#building_info); [refusals](../reference/errors.md#repair).


## `set_building_active`

Put a type of building to sleep or wake it. [API reference](../api.md#set_building_active).

- **Arguments:** `building_id` identifies the type; `active` is `False` to sleep and `True` to wake.
- **Effect:** the game applies sleep per type: **every** owned building of that building's type sleeps or wakes together. Workers of sleeping buildings leave for the campfire as idle peasants and the buildings produce nothing. After waking, workers have to walk back before production resumes.
- **Applies to:** staffed buildings (marked in the [buildings reference](../reference/buildings.md)): woodcutter, quarry, ox tether, iron mine, pitch rig, the four farms, hunter's post, mill, bakery, brewery, inn, the five weapon workshops, chapel, church, cathedral, apothecary, well and water pot.
- **Timing:** when time next moves. Nothing is queued if the type is already in the requested state.
- **Refused when:** the ID is not one of the player's buildings, `active` is not a Boolean, or the type has no sleep control.

```python
game.set_building_active(12, False)
# {"queued": "set_building_active", "type": "woodcutter", "active": False, "note": "every woodcutter of yours sleeps from when game time next moves"}
```

See also: [`building_info`](observe.md#building_info); [refusals](../reference/errors.md#set_building_active).


## `set_workshop_product`

Choose which weapon a workshop makes. [API reference](../api.md#set_workshop_product).

- **Products:** a `fletcher` makes `bows` or `crossbows`, a `poleturner` `spears` or `pikes`, a `blacksmith` `maces` or `swords`. The armourer and tanner have a single product.
- **Effect and timing:** the workshop switches from its next piece of work; a weapon already in progress is finished first. The setting applies to that one workshop.
- **Refused when:** the building is not an owned fletcher, poleturner or blacksmith; the weapon is not one of its two products; or the map does not allow that weapon to be made.

```python
game.set_workshop_product(12, "crossbows")
# {"queued": "set_workshop_product", "building_id": 12, "weapon": "crossbows", "note": "it makes this from its next piece of work"}
```

See also: [`building_info`](observe.md#building_info); [refusals](../reference/errors.md#set_workshop_product).


## `set_food_allowed`

Allow or forbid the population to eat one food. [API reference](../api.md#set_food_allowed).

- **Arguments:** `food` is `apples`, `cheese`, `meat` or `bread`; `allowed` is a Boolean.
- **Needs:** an owned granary.
- **Effect:** a forbidden food stays in the granary and is not eaten, which lowers the number of food types eaten and so the variety bonus. It does not sell or remove the food. The change is applied on the next frame without waiting for time to move, and persists until changed back.
- **Refused when:** the food name is not one of the four, `allowed` is not a Boolean, there is no granary, or the game mode does not have the granary's food controls.

```python
game.set_food_allowed("bread", False)
# {"food": "bread", "allowed": False}
```

See also: [`report`](observe.md#report); [refusals](../reference/errors.md#set_food_allowed).
