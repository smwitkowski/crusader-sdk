# Units

`State.units` lists every recognized live unit on the map, yours and other players': soldiers, lords and siege engines. A `Unit` has `id`, `type`, `owner`, `x`, `y` and `hp`. `owner` is the player number (1 is the player the driver controls). `hp` is the game's raw health value, not a percentage, and differs widely by type. Peasants and workers are not listed; `State.idle_peasants` counts the peasants available for recruiting. Unit IDs are reused after a unit dies, so read them fresh before each order.

## Recruiting

`recruit(unit, count)` turns idle peasants into troops. Every recruit needs one idle peasant waiting at the campfire, the gold price, and the recruiting building. Barracks troops also take one of each listed good from the armory. The game takes the gold and goods when time next moves; a barracks soldier appears about 40 ticks later, when his peasant has walked to the barracks. Gold prices of barracks troops and their equipment are read from the game at recruit time; the values below are those of the supported game version (1.41). A map can withhold a troop type, in which case `recruit` refuses it.

| Unit | Gold | Goods used | Recruited at | Role | Orders beyond move and attack |
|---|---:|---|---|---|---|
| `archer` | 12 | 1 bows | `barracks` | Light ranged infantry | `attack_ground`, `dig_moat`, `fill_moat`, `light_pitch` |
| `crossbowman` | 20 | 1 crossbows, 1 leather_armor | `barracks` | Armored ranged infantry; slower shots that pierce armor (game manual) | `attack_ground` |
| `spearman` | 8 | 1 spears | `barracks` | Cheap light melee infantry | `dig_moat`, `fill_moat` |
| `pikeman` | 20 | 1 pikes, 1 metal_armor | `barracks` | Slow, heavily armored defensive infantry | `dig_moat`, `fill_moat` |
| `maceman` | 20 | 1 maces, 1 leather_armor | `barracks` | Fast assault infantry | `dig_moat`, `fill_moat` |
| `swordsman` | 40 | 1 swords, 1 metal_armor | `barracks` | Slow, strongest melee infantry | none |
| `knight` | 40 | 1 swords, 1 metal_armor, 1 horse | `barracks` | Mounted heavy cavalry; the horse comes from a `stables` | none |
| `arabian_archer` | 75 | none | `mercenary_post` | Ranged infantry | `attack_ground`, `light_pitch` |
| `slave` | 5 | none | `mercenary_post` | Cheapest, weakest melee unit; sets buildings alight (game manual) | `dig_moat`, `fill_moat` |
| `slinger` | 12 | none | `mercenary_post` | Short-range ranged infantry | `attack_ground` |
| `assassin` | 60 | none | `mercenary_post` | Melee infantry that scales walls without ladders (game manual) | none |
| `horse_archer` | 80 | none | `mercenary_post` | Mounted archer that shoots on the move | `attack_ground` |
| `arabian_swordsman` | 80 | none | `mercenary_post` | Heavy melee infantry | none |
| `fire_thrower` | 100 | none | `mercenary_post` | Short-range unit that throws fire | `attack_ground` |
| `engineer` | 30 | none | `engineers_guild` | Builds and crews siege engines, mans tower engines, works the oil smelter | `build_siege`, `man`, `oil_duty`, `dig_moat`, `fill_moat` |
| `laddermen` | 4 | none | `engineers_guild` | Carry a ladder to an enemy wall so soldiers can climb it | `set_ladder` |
| `tunneler` | 30 | none | `tunnelers_guild` | Digs under an enemy wall or tower to collapse it | `dig_tunnel` |
| `monk` | 10 | none | `cathedral` | Cheap melee unit | none |
| `lord` | not recruitable | none | one per player, placed by the game | The player's leader. In a skirmish the match ends when a lord dies. | cannot be disbanded |

Every unit above accepts `move`, `patrol`, `stop`, `set_stance`, `attack`, `attack_building` and `attack_wall`; every unit except the lord accepts `disband`, which returns it to the campfire as a peasant with no refund. In a historical campaign the lord can only be moved back to his keep or ordered to attack.

## Siege engines

Engines are units: they appear in `State.units` under the names below and take `move`, `attack`, `attack_building` and `attack_wall` like soldiers. An engine with fewer engineers than its full crew takes no orders, does not move and does not shoot. Field engines are built by engineers with `build_siege`; the engineers who build one become its crew, and the engine appears on its tent a few hundred ticks later (roughly 300 to 600, depending on how far the engineers walk). Tower engines are placed with `build`. Gold is read from the game's cost table when ordered; the values below are those of game version 1.41.

| Engine | Gold | Crew | Built with | Behavior |
|---|---:|---:|---|---|
| `catapult` | 150 | 2 | `build_siege` | Mobile stone thrower for buildings and walls. Starts with 20 shots; `buy_ammo` adds 20 for 10 stone; `throw_cow`. Own catapults report `ammo` in state. |
| `trebuchet` | 150 | 3 | `build_siege` | Long-range stone thrower that cannot move once built. Uses ammunition like a catapult: `buy_ammo`, `throw_cow`. Own trebuchets report `ammo` in state. |
| `battering_ram` | 150 | 4 | `build_siege` | Walks to an ordered building or gatehouse and batters it. |
| `siege_tower` | 150 | 4 | `build_siege` | Ordered at an enemy wall tile with `attack_wall`, it rolls up and docks; soldiers then climb onto the wall over it. |
| `portable_shield` | 5 | 1 | `build_siege` | Mobile cover that shelters soldiers behind it from arrows. |
| `fire_ballista` | 150 | 2 | `build_siege` | Shoots fire bolts at enemies in range by itself once crewed. |
| `mangonel` | 50 | 2 | `build("mangonel", x, y)` on a square or round tower | Tower-mounted stone thrower. Its engineers must be able to walk up: a wall joined to the tower with stairs to the ground. |
| `ballista` | 50 | 2 | `build("ballista", x, y)` on a square or round tower | Tower-mounted bolt thrower; crewed like a mangonel. |

While the player owns cows (from a `dairy_farm`), own catapults and trebuchets also report `cows` in state.

## Capability sets

The driver enforces these sets and refuses other unit types:

- **Ranged** (`attack_ground`): `archer`, `crossbowman`, `arabian_archer`, `slinger`, `horse_archer`, `fire_thrower`.
- **Diggers** (`dig_moat`, `fill_moat`): `archer`, `spearman`, `pikeman`, `maceman`, `engineer`, `slave`.
- **Pitch lighters** (`light_pitch`): `archer`, `arabian_archer`.
- **Engineers only**: `build_siege`, `man`, `oil_duty`, `pour_oil`.
- **Laddermen only**: `set_ladder`. **Tunnelers only**: `dig_tunnel`.
- **Catapult and trebuchet only**: `buy_ammo`, `throw_cow`.

Stances (`set_stance`): `stand_ground` holds position, `defensive` engages enemies that come close and returns, `aggressive` pursues enemies that come near.
