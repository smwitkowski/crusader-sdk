# Goods

`State.stock` maps each good name below to the amount the player holds; the numeric ID is the game's index for the good. Goods live in three kinds of store: food in the granary, weapons and armor in the armory, everything else in the stockpile. A good with no room in its store is not delivered (or bought), so add stores before production stalls. Gold is held in the treasury and also appears as `State.gold`.

| Good | ID | Stored in | Produced by | Used for |
|---|---:|---|---|---|
| `wood` | 2 | stockpile | `woodcutter` | Most building costs; raw material of the `fletcher` (bows, crossbows) and `poleturner` (spears, pikes); part of tower and gatehouse `repair`. |
| `hops` | 3 | stockpile | `hops_farm` | Brewed into ale by the `brewery`. |
| `stone` | 4 | stockpile | `quarry`, carried by an `ox_tether` ox | Walls (half a stone a tile, a quarter for low wall), towers, gatehouses, the barracks, `repair`, and engine ammunition (10 stone for 20 shots). |
| `iron` | 6 | stockpile | `iron_mine` | Raw material of the `blacksmith` (maces, swords) and `armourer` (metal armor); 10 iron for an `oil_smelter`. |
| `pitch` | 7 | stockpile | `pitch_rig` | One per `pitch_ditch` tile; boiled into oil by the `oil_smelter`. |
| `wheat` | 9 | stockpile | `wheat_farm` | Ground into flour by the `mill`. Not edible. |
| `bread` | 10 | granary | `bakery` | Food. |
| `cheese` | 11 | granary | `dairy_farm` | Food. |
| `meat` | 12 | granary | `hunters_post` | Food. |
| `apples` | 13 | granary | `apple_orchard` | Food. |
| `ale` | 14 | stockpile | `brewery` | Served by the `inn`; ale coverage raises popularity. |
| `gold` | 15 | treasury | taxes and market sales | Building and recruiting costs, market purchases, bribes (negative tax levels). Not tradeable. |
| `flour` | 16 | stockpile | `mill` | Baked into bread by the `bakery`. Not edible. |
| `bows` | 17 | armory | `fletcher` | One per `archer`. |
| `crossbows` | 18 | armory | `fletcher` | One per `crossbowman`. |
| `spears` | 19 | armory | `poleturner` | One per `spearman`. |
| `pikes` | 20 | armory | `poleturner` | One per `pikeman`. |
| `maces` | 21 | armory | `blacksmith` | One per `maceman`. |
| `swords` | 22 | armory | `blacksmith` | One per `swordsman` or `knight`. |
| `leather_armor` | 23 | armory | `tanner`, from dairy-farm cows | One per `crossbowman` or `maceman`. |
| `metal_armor` | 24 | armory | `armourer` | One per `pikeman`, `swordsman` or `knight`. |

Horses and cows are not goods and are not in `stock`. Horses are bred by `stables` and used up by knights; cows belong to dairy farms and appear as `cows` on own catapults and trebuchets in `State.units`.

## Food

The four foods are `apples`, `cheese`, `meat` and `bread`. Peasants eat from the granary at a rate set by the population and the ration level (`set_rations`). Eating more food types raises popularity; an empty granary lowers it as much as rations of `none`. `set_food_allowed(food, False)` stops the population eating one food, which keeps it in the granary, for example to sell. `report("food")` and `building_info(granary_id)` show the food stock and the months of supply.

## Trading

`trade(good, qty)` needs a `market`. Positive `qty` buys, negative sells; both must be multiples of 5, at most 500. Every good except gold can be named, but the map decides which are tradeable and `trade` refuses the others (`<good> cannot be traded`).

- **Prices** are per lot of 5 and are read from the game when `trade` is called; the buy price is higher than the sell price. The result's `gold` field is the gold the trade will cost (negative) or earn (positive).
- **Buying** queues one purchase per lot of 5. The driver refuses a purchase the treasury cannot cover after other spending queued in the same pause.
- **Selling** follows the game's lot sizes, which depend on the stock at the moment of each sale: all of it below 5 in stock, 5 at a time below 50, 10 below 100, 20 below 200, otherwise 50. The requested amount must be reachable exactly with those lots or the sale is refused.
- Trades execute when time next moves. Bought goods go to their store; with no room there the game buys nothing and keeps the gold.
