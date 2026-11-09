# Buildings

A player building in `State.buildings` has `id`, `type`, `x` and `y`. Enemy records additionally have `owner`, `hp` and `max_hp`. The driver defines `(x, y)` as the top-left tile of a square footprint. Names below are placement names; read-back names can differ (all three garden sizes read back as `garden`). Availability depends on driver level and game state.

Costs below were recorded from the game in the supplied import reference and findings; the driver reads costs from the running game, so check the active game for authoritative values. Unknown production does not mean the building produces nothing.

Every footprint tile must be on the map, free and level with the other tiles. The terrain column adds the driver's special checks; the game may impose additional conditions. A recognized name does not guarantee valid or affordable placement.

| Building | Footprint (tiles) | Cost | Additional terrain check | Production |
|---|---:|---|---|---|
| `woodcutter` | 3 × 3 | 3 wood | not specified beyond general checks | unknown |
| `stockpile` | 5 × 5 | free | not specified beyond general checks | unknown |
| `hovel` | 4 × 4 | 6 wood | not specified beyond general checks | unknown |
| `quarry` | 6 × 6 | 20 wood | not specified beyond general checks | unknown |
| `keep` | 7 × 7 | unknown (read from game) | not specified beyond general checks | unknown |
| `wheat_farm` | 9 × 9 | 15 wood | farmable grass | unknown |
| `hops_farm` | 9 × 9 | 15 wood | farmable grass | unknown |
| `apple_orchard` | 11 × 11 | 5 wood | farmable grass | unknown |
| `dairy_farm` | 10 × 10 | 10 wood | farmable grass | unknown |
| `mill` | 3 × 3 | 20 wood | not specified beyond general checks | wheat to flour |
| `bakery` | 4 × 4 | 10 wood | not specified beyond general checks | flour to bread |
| `brewery` | 4 × 4 | 10 wood | not specified beyond general checks | unknown |
| `market` | 5 × 5 | 5 wood | not specified beyond general checks | unknown |
| `hunters_post` | 3 × 3 | 5 wood | not specified beyond general checks | unknown |
| `granary` | 4 × 4 | 5 wood | not specified beyond general checks | unknown |
| `armory` | 4 × 4 | 5 wood | not specified beyond general checks | unknown |
| `barracks` | 4 × 4 | 15 stone | not specified beyond general checks | unknown |
| `inn` | 5 × 5 | 20 wood, 100 gold | not specified beyond general checks | unknown |
| `chapel` | 6 × 6 | 250 gold | not specified beyond general checks | unknown |
| `church` | 9 × 9 | 500 gold | not specified beyond general checks | unknown |
| `well` | 3 × 3 | 30 gold | not specified beyond general checks | unknown |
| `fletcher` | 4 × 4 | 20 wood, 100 gold | not specified beyond general checks | bows (wood) or crossbows |
| `poleturner` | 4 × 4 | 10 wood, 100 gold | not specified beyond general checks | spears (wood) or pikes |
| `blacksmith` | 4 × 4 | 20 wood, 200 gold | not specified beyond general checks | maces (iron) or swords |
| `armourer` | 4 × 4 | 20 wood, 100 gold | not specified beyond general checks | metal armor (iron) |
| `tanner` | 4 × 4 | 10 wood, 100 gold | not specified beyond general checks | leather armor (dairy cows) |
| `mercenary_post` | 4 × 4 | 10 wood | not specified beyond general checks | unknown |
| `iron_mine` | 4 × 4 | 20 wood | iron ore | unknown |
| `lookout_tower` | 3 × 3 | 10 stone | not specified beyond general checks | unknown |
| `perimeter_tower` | 4 × 4 | 10 stone | not specified beyond general checks | unknown |
| `defense_turret` | 5 × 5 | 15 stone | not specified beyond general checks | unknown |
| `square_tower` | 6 × 6 | 35 stone | not specified beyond general checks | unknown |
| `round_tower` | 6 × 6 | 40 stone | not specified beyond general checks | unknown |
| `gatehouse` | 5 × 5 | 10 stone | not specified beyond general checks | unknown |
| `large_gatehouse` | 7 × 7 | 20 stone | not specified beyond general checks | unknown |
| `engineers_guild` | 5 × 5 | 10 wood, 100 gold | not specified beyond general checks | unknown |
| `tunnelers_guild` | 5 × 5 | 10 wood, 100 gold | not specified beyond general checks | unknown |
| `stables` | 6 × 6 | 20 wood, 400 gold | not specified beyond general checks | unknown |
| `cathedral` | 13 × 13 | 1000 gold | not specified beyond general checks | unknown |
| `apothecary` | 6 × 6 | 20 wood, 150 gold | not specified beyond general checks | unknown |
| `ox_tether` | 2 × 2 | 5 wood | not specified beyond general checks | ox carries quarry stone to stockpile |
| `pitch_rig` | 4 × 4 | unknown (read from game) | marsh (game check) | unknown |
| `maypole` | 3 × 3 | unknown (read from game) | not specified beyond general checks | unknown |
| `dancing_bear` | 5 × 5 | unknown (read from game) | not specified beyond general checks | unknown |
| `small_garden` | 2 × 2 | unknown (read from game) | not specified beyond general checks | unknown |
| `medium_garden` | 3 × 3 | unknown (read from game) | not specified beyond general checks | unknown |
| `large_garden` | 4 × 4 | unknown (read from game) | not specified beyond general checks | unknown |
| `statue` | 2 × 2 | unknown (read from game) | not specified beyond general checks | unknown |
| `shrine` | 2 × 2 | unknown (read from game) | not specified beyond general checks | unknown |
| `gallows` | 2 × 2 | unknown (read from game) | not specified beyond general checks | unknown |
| `cess_pit` | 5 × 5 | unknown (read from game) | not specified beyond general checks | unknown |
| `stocks` | 3 × 3 | unknown (read from game) | not specified beyond general checks | unknown |
| `burning_stake` | 3 × 3 | unknown (read from game) | not specified beyond general checks | unknown |
| `dungeon` | 5 × 5 | unknown (read from game) | not specified beyond general checks | unknown |
| `stretching_rack` | 3 × 3 | unknown (read from game) | not specified beyond general checks | unknown |
| `gibbet` | 2 × 2 | unknown (read from game) | not specified beyond general checks | unknown |
| `chopping_block` | 3 × 3 | unknown (read from game) | not specified beyond general checks | unknown |
| `dunking_stool` | 5 × 5 | unknown (read from game) | not specified beyond general checks | unknown |
| `gatehouse_turned` | 5 × 5 | 10 stone | not specified beyond general checks | unknown |
| `large_gatehouse_turned` | 7 × 7 | 20 stone | not specified beyond general checks | unknown |
| `drawbridge` | 5 × 5 | 10 wood | not specified beyond general checks | unknown |
| `killing_pit` | 1 × 1 | 6 wood | not specified beyond general checks | unknown |
| `pitch_ditch` | 1 × 1 | 1 pitch | not specified beyond general checks | unknown |
| `dog_cage` | 3 × 3 | 10 wood, 100 gold | not specified beyond general checks | unknown |
| `oil_smelter` | 4 × 4 | 10 iron, 100 gold | not specified beyond general checks | unknown |
| `water_pot` | 4 × 4 | 60 gold | not specified beyond general checks | unknown |

The game requires a new granary to touch an existing one. A drawbridge must sit on a gatehouse gate axis. An ox tether is needed to deliver a quarry’s stone. These are game checks or behaviors beyond the general terrain checks.
