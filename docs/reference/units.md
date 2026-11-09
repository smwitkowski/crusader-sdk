# Units

A `Unit` has `id`, `type`, `owner`, `x`, `y` and `hp`; `ammo` and `cows` are optional. The driver reports recognized live unit types and excludes zero-health units in missions. A lord record has `owner` and `alive`; its `id`, position and health are optional.

Costs are per unit. European troop prices and equipment below were recorded in the supplied import reference; the driver reads them from the running game, which is authoritative. Recruits require an idle peasant. Roles below list only capabilities explicitly identified in the driver, not a complete combat description. Availability and command acceptance depend on game state and driver level.

| Unit | Cost | Recruitment building | Known role or action |
|---|---|---|---|
| `archer` | 12 gold, bow | `barracks` | can dig moat; can light pitch; ranged; attack ground |
| `crossbowman` | 20 gold, crossbow, leather armor | `barracks` | ranged; attack ground |
| `spearman` | 8 gold, spear | `barracks` | can dig moat |
| `pikeman` | 20 gold, pike, metal armor | `barracks` | can dig moat |
| `maceman` | 20 gold, mace, leather armor | `barracks` | can dig moat |
| `swordsman` | 40 gold, sword, metal armor | `barracks` | unknown |
| `knight` | 40 gold, sword, metal armor; horse at level 2+ | `barracks` | unknown |
| `arabian_archer` | 75 gold | `mercenary_post` | can light pitch; ranged; attack ground |
| `slave` | 5 gold | `mercenary_post` | can dig moat |
| `slinger` | 12 gold | `mercenary_post` | ranged; attack ground |
| `assassin` | 60 gold | `mercenary_post` | unknown |
| `horse_archer` | 80 gold | `mercenary_post` | ranged; attack ground |
| `arabian_swordsman` | 80 gold | `mercenary_post` | unknown |
| `fire_thrower` | 100 gold | `mercenary_post` | ranged; attack ground |
| `engineer` | 30 gold | `engineers_guild` | can dig moat; can operate oil smelter |
| `laddermen` | 4 gold | `engineers_guild` | raise ladders against enemy walls |
| `tunneler` | 30 gold | `tunnelers_guild` | dig tunnel toward enemy wall or building |
| `monk` | 10 gold | `cathedral` | unknown |
| `lord` | unknown | `unknown` | unknown |

The driver also names siege engines when enabled. The table does not establish their recruitment costs or buildings.
