# Buildings

`build(building, x, y)` takes a placement name from the tables below; `(x, y)` is the top-left tile of a square footprint. An owned building in `State.buildings` has `id`, `type`, `x` and `y`; enemy records additionally have `owner`, `hp` and `max_hp`. A few placement names read back under another `type`, noted in the table.

## How placement is checked

`build` and `find_sites` apply the same checks, in this order. A failed check refuses the command with the reason in the error message.

1. **Map.** Every footprint tile must be on the map, be land, hold no building, unit, wall, tree, rock or farmland, not belong to a build queued earlier in the same pause, and be level with the other footprint tiles. Farms additionally need farmable grass on every tile and an iron mine needs iron ore on every tile.
2. **The game's own placement check**, the one its user interface runs. Its reasons include: a new granary, stockpile or armory must be adjacent to an existing one; too close to enemy units or buildings; too far from the castle; too close to a signpost; inaccessible land; farms need an oasis or fertile land. A spot the game refuses without a message is reported as such.
3. **Build menu.** A building the map's build menu does not offer is refused (`this mission's build menu does not offer it`).
4. **Cost.** The driver reads the cost from the game's cost table when `build` is called and refuses if the stock is short; the error states the amounts needed and held. `find_sites` does not check cost.

The costs below are the values of the supported game version (1.41); the game's table is authoritative and is what the driver charges against. The game takes the cost and places the building when time next moves. If the spot is no longer free then (usually a unit walked onto it), a `build_refused` event follows. `demolish` refunds half the cost.

## Building table

"Staffed" buildings need a peasant as worker, do nothing without one, and can be put to sleep with `set_building_active`; `building_info(id)["worker"]` reports the worker's status. "Map" is the character `map()` draws for the building. Towers and gatehouses are the only buildings with a health bar and `repair`.

| Building | Footprint | Cost | Placement | Staffed | Map | Purpose |
|---|---:|---|---|---|---|---|
| `woodcutter` | 3 × 3 | 3 wood | free flat land | yes | `w` | Its worker fells nearby trees and carries wood to the stockpile. Place it near trees (`^`). |
| `stockpile` | 5 × 5 | free | free flat land; the game requires an additional stockpile to touch an existing one | no | `s` | Stores wood, hops, stone, iron, pitch, wheat, flour and ale. More stockpiles give more room; goods with no room are not delivered. |
| `hovel` | 4 × 4 | 6 wood | free flat land | no | `h` | Housing for 8 peasants (`State.housing` rises by 8). |
| `quarry` | 6 × 6 | 20 wood | stone deposit (game check; use `find_sites`) | yes | `q` | Its workers cut stone, which stays at the quarry until an `ox_tether` ox carries it to the stockpile. A quarry without a tether delivers no stone. |
| `keep` | 7 × 7 | cannot be built | placed by the map | no | `K` | The lord's home and the campfire where idle peasants wait. It cannot be built, demolished or damaged; `find_sites("keep")` only reports where a 7 × 7 footprint fits. |
| `wheat_farm` | 9 × 9 | 15 wood | farmable grass (`,`) on every tile | yes | `f` | Grows wheat and delivers it to the stockpile; a mill turns it into flour. |
| `hops_farm` | 9 × 9 | 15 wood | farmable grass (`,`) on every tile | yes | `j` | Grows hops and delivers them to the stockpile; a brewery turns them into ale. |
| `apple_orchard` | 11 × 11 | 5 wood | farmable grass (`,`) on every tile | yes | `a` | Grows apples and delivers them to the granary (food). |
| `dairy_farm` | 10 × 10 | 10 wood | farmable grass (`,`) on every tile | yes | `d` | Raises cows and delivers cheese to the granary (food). Its cows also supply the tanner and are the ammunition of `throw_cow`. |
| `mill` | 3 × 3 | 20 wood | free flat land | yes | `n` | Grinds wheat from the stockpile into flour, returned to the stockpile. |
| `bakery` | 4 × 4 | 10 wood | free flat land | yes | `k` | Bakes flour from the stockpile into bread, delivered to the granary (food). |
| `brewery` | 4 × 4 | 10 wood | free flat land | yes | `b` | Brews hops from the stockpile into ale, returned to the stockpile. |
| `market` | 5 × 5 | 5 wood | free flat land | no | `m` | Required by `trade`. It makes nothing itself. |
| `hunters_post` | 3 × 3 | 5 wood | free flat land | yes | `p` | Its hunter delivers meat to the granary (food). The game's build menu hides it in a skirmish against computer lords, where `build` refuses it. |
| `granary` | 4 × 4 | 5 wood | free flat land; the game requires a new granary to touch an existing one | no | `g` | Stores apples, cheese, meat and bread. Food counts, and is eaten, only from a granary; rations and the food toggles are its panel. |
| `armory` | 4 × 4 | 5 wood | free flat land; the game requires an additional armory to touch an existing one | no | `B` | Stores weapons and armor. Barracks recruits take their equipment from it. |
| `barracks` | 4 × 4 | 15 stone | free flat land | no | `B` | Required to recruit archers, crossbowmen, spearmen, pikemen, macemen, swordsmen and knights. |
| `inn` | 5 × 5 | 20 wood, 100 gold | free flat land | yes | `i` | Its innkeeper fetches ale from the stockpile and serves it; ale coverage of 25 % or more of the population raises popularity. |
| `chapel` | 6 × 6 | 250 gold | free flat land | yes | `c` | Its priest blesses people; the blessed share of the population raises popularity (religion). |
| `church` | 9 × 9 | 500 gold | free flat land | yes | `c` | As a chapel, and the game adds a further religion bonus while one stands. |
| `well` | 3 × 3 | 30 gold | free flat land | yes | `o` | Fire fighting: its worker draws water to put out burning buildings. |
| `fletcher` | 4 × 4 | 20 wood, 100 gold | free flat land | yes | `B` | Makes bows or crossbows from wood and delivers them to the armory; choose with `set_workshop_product`. |
| `poleturner` | 4 × 4 | 10 wood, 100 gold | free flat land | yes | `B` | Makes spears or pikes from wood and delivers them to the armory; choose with `set_workshop_product`. |
| `blacksmith` | 4 × 4 | 20 wood, 200 gold | free flat land | yes | `B` | Makes maces or swords from iron and delivers them to the armory; choose with `set_workshop_product`. |
| `armourer` | 4 × 4 | 20 wood, 100 gold | free flat land | yes | `B` | Makes metal armor from iron and delivers it to the armory. |
| `tanner` | 4 × 4 | 10 wood, 100 gold | free flat land | yes | `B` | Makes leather armor from dairy-farm cows and delivers it to the armory. |
| `mercenary_post` | 4 × 4 | 10 wood | free flat land | no | `B` | Required to hire Arabian mercenaries, who cost gold and an idle peasant but no weapons. |
| `iron_mine` | 4 × 4 | 20 wood | iron ore on every tile | yes | `B` | Mines iron and delivers it to the stockpile. |
| `lookout_tower` | 3 × 3 | 10 stone | free flat land | no | `B` | Tall, narrow tower for a few ranged troops. Repairable. |
| `perimeter_tower` | 4 × 4 | 10 stone | free flat land | no | `B` | Small wall tower. Repairable. |
| `defense_turret` | 5 × 5 | 15 stone | free flat land | no | `B` | Medium wall tower. Repairable. |
| `square_tower` | 6 × 6 | 35 stone | free flat land | no | `B` | Large tower; its top can carry a `mangonel` or `ballista`. Repairable. |
| `round_tower` | 6 × 6 | 40 stone | free flat land | no | `B` | Large tower; its top can carry a `mangonel` or `ballista`. Repairable. |
| `gatehouse` | 5 × 5 | 10 stone | free flat land | no | `B` | Gate through a wall line, opened and closed with `set_gate`. Repairable. |
| `large_gatehouse` | 7 × 7 | 20 stone | free flat land | no | `B` | Larger gate, opened and closed with `set_gate`. Repairable. |
| `engineers_guild` | 5 × 5 | 10 wood, 100 gold | free flat land | no | `B` | Required to recruit engineers and laddermen. |
| `tunnelers_guild` | 5 × 5 | 10 wood, 100 gold | free flat land | no | `B` | Required to recruit tunnelers. |
| `stables` | 6 × 6 | 20 wood, 400 gold | free flat land | no | `B` | Breeds horses for knights: about one every 400 ticks, at most four waiting per stables. |
| `cathedral` | 13 × 13 | 1000 gold | free flat land | yes | `B` | As a church with a larger religion bonus; also required to recruit monks. |
| `apothecary` | 6 × 6 | 20 wood, 150 gold | free flat land | yes | `B` | Its healer treats disease in the town (game manual). |
| `ox_tether` | 2 × 2 | 5 wood | free flat land | yes | `B` | Its ox carries stone from a quarry to the stockpile, about 12 stone a load. Place it near the quarry. |
| `pitch_rig` | 4 × 4 | wood, charged from the game's cost table (20 wood in the game manual) | marsh (game check; refused elsewhere) | yes | `B` | Draws pitch and delivers it to the stockpile. |
| `maypole` | 3 × 3 | 25 gold | free flat land | no | `B` | Good thing: counts toward the fear factor's good side. |
| `dancing_bear` | 5 × 5 | 20 gold | free flat land | no | `B` | Good thing. |
| `small_garden` | 2 × 2 | 30 gold | free flat land | no | `B` | Good thing. Reads back as `garden`. |
| `medium_garden` | 3 × 3 | 30 gold | free flat land | no | `B` | Good thing. Reads back as `garden`. |
| `large_garden` | 4 × 4 | 30 gold | free flat land | no | `B` | Good thing. Reads back as `garden`. |
| `statue` | 2 × 2 | 30 gold | free flat land | no | `B` | Good thing. |
| `shrine` | 2 × 2 | 30 gold | free flat land | no | `B` | Good thing. |
| `gallows` | 2 × 2 | 50 gold | free flat land | no | `B` | Bad thing: counts toward the fear factor's bad side. |
| `cess_pit` | 5 × 5 | 40 gold | free flat land | no | `B` | Bad thing. |
| `stocks` | 3 × 3 | 45 gold | free flat land | no | `B` | Bad thing. |
| `burning_stake` | 3 × 3 | 45 gold | free flat land | no | `B` | Bad thing. |
| `dungeon` | 5 × 5 | 40 gold | free flat land | no | `B` | Bad thing. |
| `stretching_rack` | 3 × 3 | 45 gold | free flat land | no | `B` | Bad thing. |
| `gibbet` | 2 × 2 | 50 gold | free flat land | no | `B` | Bad thing. |
| `chopping_block` | 3 × 3 | 45 gold | free flat land | no | `B` | Bad thing. |
| `dunking_stool` | 5 × 5 | 40 gold | free flat land | no | `B` | Bad thing. |
| `gatehouse_turned` | 5 × 5 | 10 stone | free flat land | no | `B` | A gatehouse with its gate on the other axis. Reads back as `gatehouse`. |
| `large_gatehouse_turned` | 7 × 7 | 20 stone | free flat land | no | `B` | A large gatehouse with its gate on the other axis. Reads back as `large_gatehouse`. |
| `drawbridge` | 5 × 5 | 10 wood | in front of the gate of an owned gatehouse, on its gate axis | no | `B` | Bridges a moat in front of a gate; raised and lowered with `set_gate`. |
| `killing_pit` | 1 × 1 | 6 wood | free flat land | no | `B` | Hidden trap that wounds enemies who walk over it. |
| `pitch_ditch` | 1 × 1 | 1 pitch | free flat land | no | `B` | One tile of pitch that burns when lit with `light_pitch`, spreading to adjoining pitch and burning units in it. |
| `dog_cage` | 3 × 3 | 10 wood, 100 gold | free flat land | no | `B` | Holds war dogs, which it releases by itself when an enemy comes near. No command controls it. |
| `oil_smelter` | 4 × 4 | 10 iron, 100 gold | free flat land | no | `B` | Boils pitch from the stockpile into oil for engineers assigned with `oil_duty`. |
| `water_pot` | 4 × 4 | 60 gold | free flat land | yes | `B` | Fire-fighting station whose workers put out fires. |

## Other placement names

These names are accepted by `build` but are not buildings: they do not appear in `State.buildings`, have no footprint, and skip the map and cost-table checks above.

| Name | Where `(x, y)` must be | Cost | Purpose |
|---|---|---|---|
| `flag_1`, `flag_2`, `flag_3`, `flag_4` | top of an owned wall or tower, with no decoration there yet | free | Decoration only; it does not change the fear factor. |
| `heads` | top of an owned wall or tower, with no decoration there yet | free | Heads on spikes; decoration only. |
| `brazier` | top of an owned wall or tower, with no decoration there yet | none charged through the driver's checks | Fire source: archers within 3 tiles of a lit brazier can `light_pitch`. |
| `mangonel` | a tower-top tile of an owned `square_tower` or `round_tower` that carries no engine and has no unit on the tile | 50 gold | Tower engine that lobs stones; appears as a unit and needs 2 engineers (`man`). |
| `ballista` | as `mangonel` | 50 gold | Tower engine that shoots bolts; appears as a unit and needs 2 engineers (`man`). |

`find_sites` also accepts the six siege engine names (`catapult`, `trebuchet`, `battering_ram`, `siege_tower`, `portable_shield`, `fire_ballista`) and returns sites for the 3 × 3 siege tent that `build_siege` places. Walls, stairs and moats are not buildings; see `build_wall` and `plan_moat` in the [defences commands](../commands/defences.md).

## Production chains

| Result | Chain |
|---|---|
| Wood | `woodcutter` → stockpile |
| Stone | `quarry` → `ox_tether` → stockpile |
| Iron | `iron_mine` (on ore) → stockpile |
| Pitch | `pitch_rig` (on marsh) → stockpile |
| Apples, cheese, meat | `apple_orchard`, `dairy_farm`, `hunters_post` → granary |
| Bread | `wheat_farm` → stockpile → `mill` → stockpile → `bakery` → granary |
| Ale | `hops_farm` → stockpile → `brewery` → stockpile → `inn` |
| Bows, crossbows, spears, pikes | wood → `fletcher` or `poleturner` → armory |
| Maces, swords, metal armor | iron → `blacksmith` or `armourer` → armory |
| Leather armor | `dairy_farm` cows → `tanner` → armory |

Each step is carried on foot by the building's worker, so distance to the stockpile, granary or armory sets the output rate, and a full store stops deliveries. See the [goods reference](goods.md) and the mechanics primer in [concepts](../concepts.md#game-mechanics-primer).
