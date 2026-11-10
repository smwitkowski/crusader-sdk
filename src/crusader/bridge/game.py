"""Real Stronghold Crusader 1.41 backend: reads and drives a running game through /proc/<pid>/mem.

Exe: Crusader 1.41 HD, sha256 3bb0a8c1...ac5a, the same build OpenSHC targets (SHC_3BB0A8C1), so its
struct layouts and addresses apply directly. Time control and commands need the crusader-bridge UCP3
module (bridge/ucp3): it pauses the game once the tick counter reaches a target we write, and runs a
per-frame mailbox that hands our commands to the game's own GameSynchronyState::queueCommand.
Addresses below were checked live against the screen on 2026-10-28; see the public documentation.

  python3 real_game.py               # current state as JSON (run as root next to the game)
  python3 real_game.py start         # drive the menus into a fresh, paused Castle Builder match
  python3 real_game.py advance N     # run exactly N ticks
"""

import array
import contextlib
import heapq
import json
import os
import re
import struct
import subprocess
import sys
import time
from dataclasses import dataclass

from .memory import MAX_READ, ProcessMemory

# Player 1 record (OpenSHC PlayerData, base 0x0115F7EC, stride 0x39F4)
PLAYER = 0x0115F7EC
POPULARITY_X100 = PLAYER + 0x60  # the book shows it rounded down
HOUSING = PLAYER + 0x74
POPULATION = PLAYER + 0x78
TAXES = PLAYER + 0x2188  # 0..11; 3 = no tax, 0..2 bribes
LAST_MONTHS_TAX = PLAYER + 0x2154  # lastMonthsIncomeTax: tax gold paid at the last game-month edge
LAST_MONTHS_BRIBE = PLAYER + 0x2140  # lastMonthsBribeTax: bribe charged at the last game-month edge
RATIONS = PLAYER + 0x218C  # 0 none .. 4 double; 2 = normal
STOCK = 0x0115FCBC  # int32 per good, same indices as UCP3's startResources table
GOODS = {
    "wood": 2,
    "hops": 3,
    "stone": 4,
    "iron": 6,
    "pitch": 7,
    "wheat": 9,
    "bread": 10,
    "cheese": 11,
    "meat": 12,
    "apples": 13,
    "ale": 14,
    "gold": 15,
    "flour": 16,
    "bows": 17,
    "crossbows": 18,
    "spears": 19,
    "pikes": 20,
    "maces": 21,
    "swords": 22,
    "leather_armor": 23,
    "metal_armor": 24,
}
FOODS = ("apples", "cheese", "meat", "bread")

# GameCore 0x01FE7D10
TICK = 0x01FE7DA8  # mapTimeInTicks
PAUSED = 0x01FEA054  # gamePausedLogical
SPEED = 0x01FE7DD8  # gameSpeedLevel: ~ticks per second; the UI caps it at 90, the loop accepts more
MENU = 0x01FE7D1C  # currentMenuViewType
MENU_ENTER_NAME, MENU_MAIN, MENU_MAP_CHOICE = 40, 41, 35
# Date (GameState.mapAndTime); a month is exactly 800 ticks (4 weeks of 200)
MONTH, YEAR = 0x0117CAB4, 0x0117CAB8
TICKS_PER_MONTH = 800

# Tile map (TileMapState 0x01A93208): tile = rowStart[y] + x, row y valid for tiles [end(y-1), end(y))
TMS = 0x01A93208
ROWS = 0x02337300  # 12-byte entries: (rowStart, xOffset, endTile)
N_TILES, MAP_SIDE = 80400, 400
LOGIC, LOGIC2, BUILDING_LAYER, HEIGHT, ORGANISM, UNIT_LAYER = 0x165160, 0x1B3FE0, 0x2029B0, 0x29FA30, 0x1DB590, 0x23D7E0
L_LAND, L_BUILDING, L_TREES, L_FARMLAND = 0x8000, 0x400, 0x3000, 0x4
# tile logic bits isBuildingPlacementAllowedAtTile (0x004F9A60) rejects outright
# plus 0x80: ground soldiers cannot walk on and the game refuses buildings on (trail-22's ridges; live 2026-11-03)
L_BLOCKED = 0x1 | 0x30 | 0x80 | 0x100000 | 0x200000 | 0x10000400 | 0xF000000 | L_FARMLAND | L_TREES
FARMABLE = 0x80 | 0x10  # Logic2 bits farms need: game accepted farms on 128 and 16, refused 0 and 2 (2026-10-28)
FARMS = {"wheat_farm", "hops_farm", "apple_orchard", "dairy_farm"}
L_IRON = 0x80000  # iron ore: the only tiles an iron mine was accepted on (live; the AI's iron heat map counts them)
L_WALL, L_STAIRS = 0x100, 0x800  # wall and stair tiles (GCT_PLACE_WALL sets 0x100, stairs 0x900; live)
WALL_OWNER = 0x2C6E50  # TileMapState.WallOwnerLayer (byte): owner - 1 in the low 3 bits on wall tiles

# Buildings (OpenSHC BuildingsState 0x00F98520): record i at BUILDINGS_BASE + i*0x32C
BUILDINGS_BASE, BUILDING_SIZE = 0x00F98534, 0x32C
B_TYPE, B_OWNER, B_UID, B_HP = 0xD2, 0xD6, 0xD8, 0x10C  # B_HP: currentHealth, maxHealth (shorts)
BT_NAMES = {
    1: "hovel",
    3: "woodcutter",
    5: "iron_mine",
    7: "hunters_post",
    8: "mercenary_post",
    9: "barracks",
    10: "stockpile",
    11: "armory",
    12: "fletcher",
    13: "blacksmith",
    14: "poleturner",
    15: "armourer",
    16: "tanner",
    17: "bakery",
    18: "brewery",
    19: "granary",
    20: "quarry",
    22: "inn",
    26: "market",
    27: "well",
    30: "wheat_farm",
    31: "hops_farm",
    32: "apple_orchard",
    33: "dairy_farm",
    34: "mill",
    36: "chapel",
    37: "church",
    45: "large_gatehouse",
    46: "gatehouse",
    74: "lookout_tower",
    75: "perimeter_tower",
    76: "defense_turret",
    77: "square_tower",
    78: "round_tower",
}
BARRACKS_ID, MARKET_ID = PLAYER + 0x15C, PLAYER + 0x1AC  # the player's barracks / marketplace building id (0 = none)

# Units (OpenSHC UnitsState 0x01387F38; unit i at UNITS + i*UNIT_SIZE, slots 1..[UNITS_STATE]-1)
UNITS_STATE, UNITS, UNIT_SIZE = 0x01387F38, 0x0138854C, 0x490
U_STATE, U_TYPE, U_OWNER, U_UID, U_X, U_Y, U_HP = 0x8C, 0x8E, 0x96, 0x98, 0xC4, 0xC6, 0x3C8  # U_STATE 2 = alive
U_TILE, PATH_REGION, REACHABLE, REACH_THIS = 0xD4, 0x01DF70D8, 0x004A5320, 0x012BB8C8  # man cursor's reach test
U_JOB = 0x2A0  # zero for a unit free to take orders (the pour cursor's and order executor's test)
U_OIL_POT = 0x388  # an engineer's carried oil pot (short; a union field other unit types reuse)
SELECTION = 0x01387FAC  # UnitsState.selectedUnitsBitFlags[400]: unit i = byte i>>3, bit i&7
UNIT_NAMES = {
    5: "tunneler",
    22: "archer",
    23: "crossbowman",
    24: "spearman",
    25: "pikeman",
    26: "maceman",
    27: "swordsman",
    28: "knight",
    29: "laddermen",
    30: "engineer",
    37: "monk",
    55: "lord",
    70: "arabian_archer",
    71: "slave",
    72: "slinger",
    73: "assassin",
    74: "horse_archer",
    75: "arabian_swordsman",
    76: "fire_thrower",
}
UNIT_TYPE = {n: t for t, n in UNIT_NAMES.items()}
PEASANT = 1  # an idle peasant at the campfire; recruiting turns one into a soldier
# European troops come from the barracks: gold per unit (int table 0x00AB9114) and the goods it uses up (4 ints per
# type at 0x00B55260; -1 = a horse), both indexed by type - 22 and read from the game.
RECRUITABLE = ("archer", "crossbowman", "spearman", "pikeman", "maceman", "swordsman", "knight")
RECRUIT_GOLD, RECRUIT_GOODS = 0x00AB9114, 0x00B55260
LORD_ID, LORD_UID = PLAYER + 0x21F8, PLAYER + 0x21FC
GAME_OVER = 0x0117D500  # MapAndTimeState.gameOver: set when a skirmish ends (a lord died; live)
# Mercenaries come from the mercenary post for gold and an idle peasant only (UnitsState::nonEuroRecruit 0x52EC10, whose
# prices are immediates in its code): Arabian units 70..76.
MERCENARIES = {
    "arabian_archer": 75,
    "slave": 5,
    "slinger": 12,
    "assassin": 60,
    "horse_archer": 80,
    "arabian_swordsman": 80,
    "fire_thrower": 100,
}
MERC_POST_ID = PLAYER + 0x24C
# recruits, also UnitsState::nonEuroRecruit: gold from its code (0x52EC10..0x52EC8B computes it per
# type), building from the player record: engineers and laddermen at the engineers' guild (+0x1FC), tunnelers at the
# tunnelers' guild (+0x224), monks at the cathedral the UI has selected (p1; the player record keeps no cathedral id).
G2_RECRUITS = {"engineer": 30, "laddermen": 4, "tunneler": 30, "monk": 10}
G2_HOME = {"engineer": PLAYER + 0x1FC, "laddermen": PLAYER + 0x1FC, "tunneler": PLAYER + 0x224}
HORSES = PLAYER + 0x2252  # availableHorses (short): stables breed them (~1 per 400 ticks, up to 4 per stables, live)
STRIDE = 0x39F4  # player records
HALF_STONE = PLAYER + 0x2150  # wall stone carry in quarter stones, 0..3 (0x41C190; non-zero = the 0x457E80 cap drops 1)
WALL_KINDS = {"wall": 25, "stairs": 27}  # GCT_PLACE_WALL (25) p4: high stone wall / stairs (live)
# the castle menu's low wall (46, +60 height) and crenellated wall (26: dragged over your existing walls;
# wall bit and
# 0x200, alternate tiles 0x400000) are the same command with another kind (wall executor 0x502F30; UI drags recorded)
G5_WALL_KINDS = {**WALL_KINDS, "low_wall": 46, "crenel": 26}
L_CRENEL = 0x200
# Market (MapAndTimeState 0x0117C78C): price per lot of 5 (buy, sell) at +0x848 + res*8; tradeable flags at +0x9D8
PRICES, TRADEABLE = 0x0117CFD4, 0x0117D164
# Scenario invasions (MapPropertiesState 0x01653858): events at +0x5B0, 0xE4 each, count at +0x5AC; an event of type 1
# spawns units[k] (k: the game's invasion categories) for player invader + 2 at signpost `point` when the date comes.
EVENTS, EVENT_COUNT, EVENT_SIZE = 0x01653858 + 0x5B0, 0x01653858 + 0x5AC, 0xE4
INVASION_SLOT = {"archer": 0, "crossbowman": 1, "spearman": 2, "pikeman": 3, "maceman": 4, "swordsman": 5, "knight": 6}

# Commands (OpenSHC Commands/GameCommandType.hpp)
PLACE_BUILDING, DESTROY_BUILDING, CHANGE_TAXES, CHANGE_RATIONS, BUY_OR_SELL, SAVE = 28, 29, 34, 35, 38, 39
MOVE, RECRUIT, ATTACK, PLACE_WALL = (
    17,
    31,
    36,
    25,
)  # GCT_UNITS_MOVE, GCT_RECRUIT_UNIT, GCT_DISBAND_AND_ATTACK_UNITS, GCT_PLACE_WALL
# every tuple recorded from the real UI:
#   stance buttons (70, tribe, 0 stand ground | 1 defensive | 2 aggressive), queued at 0x522C0F;
#   stop (36, tribe, 31) and disband (36, tribe, 30) from the unit panel;
#   a map click (17, tribe, x, y, p3, 1): p3 = 1 after the patrol button, -1 when Shift is held from the first click
#   (waypoints), else 0; each further Shift+click adds a marker (71, tribe, x, y, n), n = 2..9 (the UI keeps at most 9);
#   attack here (17, tribe, x, y, 0, 0) then (36, tribe, 5, x, y, 15); a click on an enemy wall (36, tribe, 23,
# tile index).
STANCE, MARKER = 70, 71
STANCES = {"stand_ground": 0, "defensive": 1, "aggressive": 2}
I_ATTACK_GROUND, I_ATTACK_WALL, I_DISBAND, I_STOP = 5, 23, 30, 31
GROUND_RADIUS = 15  # the "attack here" order's last value as the UI sends it (0x01FE7C10, recorded live)
MAX_MARKERS = 9  # the UI's marker count tops out at 9 (asm 0x4372CA: a 10th Shift+click replaces the 9th)
RANGED = {22, 23, 70, 72, 74, 76}  # archer, crossbowman, Arabian archer, slinger, horse archer, fire thrower
DEMOLISH_REFUND = 50  # percent of the cost refunded, as the game's map demolish tool sends (asm 0x438AD3)
# In single player the save writer (0x495800 -> 0x4950B0) takes the file name from slot 2 of the save
# dialog's text box at 0x01652740 (it selects slot 2 at 0x495102, then reads box + 0x150 + 0xFA * slot).
SAVE_NAME = 0x01652740 + 0x150 + 0xFA * 2
# Command building type (OpenSHC MappersEnum) and footprint side from the exe's size table (0x004FA550).
# (x, y) is the footprint's top-left tile.
BUILDINGS = {
    "woodcutter": (51, 3),
    "stockpile": (52, 5),
    "hovel": (54, 4),
    "quarry": (56, 6),
    "keep": (60, 7),
    "wheat_farm": (70, 9),
    "hops_farm": (71, 9),
    "apple_orchard": (72, 11),
    "dairy_farm": (73, 10),
    "mill": (74, 3),
    "bakery": (75, 4),
    "brewery": (76, 4),
    "market": (77, 5),
    "hunters_post": (78, 3),
    "granary": (80, 4),
    "armory": (81, 4),
    "barracks": (87, 4),
    "inn": (92, 5),
    "chapel": (95, 6),
    "church": (96, 9),
    "well": (330, 3),
    # military economy and defenses (mappers: OpenSHC MappersEnum; sides: the exe's size table)
    "fletcher": (50, 4),
    "poleturner": (82, 4),
    "blacksmith": (83, 4),
    "armourer": (84, 4),
    "tanner": (85, 4),
    "mercenary_post": (86, 4),
    "iron_mine": (90, 4),
    "lookout_tower": (110, 3),
    "perimeter_tower": (111, 4),
    "defense_turret": (112, 5),
    "square_tower": (113, 6),
    "round_tower": (114, 6),
    "gatehouse": (144, 5),
    "large_gatehouse": (146, 7),
}
BASE_BUILDINGS = tuple(BUILDINGS)
# mapper and side recorded from UI placements (castle menu > military: engineers' guild, stables,
# tunnelers' guild; town menu: cathedral, apothecary), BuildingType read back from the placed building.
G2_BUILDINGS = {
    "engineers_guild": (88, 5),
    "tunnelers_guild": (89, 5),
    "stables": (65, 6),
    "cathedral": (97, 13),
    "apothecary": (93, 6),
}
G2_BT = {23: "apothecary", 24: "engineers_guild", 25: "tunnelers_guild", 35: "stables", 38: "cathedral"}
BUILDINGS.update(G2_BUILDINGS)
G3_BUILDINGS = tuple(BUILDINGS)
# every mapper recorded from the real build menu: industry's
# ox tether
# and pitch rig, and the town menu's good and bad things. The UI's mapper for one item changes with its rotation key
# (cosmetic: same BuildingType, size and cost); these are the ones it sends before any rotation.
G4_BUILDINGS = {
    "ox_tether": (55, 2),
    "pitch_rig": (91, 4),
    "maypole": (175, 3),
    "dancing_bear": (324, 5),
    "small_garden": (160, 2),
    "medium_garden": (166, 3),
    "large_garden": (169, 4),
    "statue": (314, 2),
    "shrine": (318, 2),
    "gallows": (176, 2),
    "cess_pit": (301, 5),
    "stocks": (177, 3),
    "burning_stake": (305, 3),
    "dungeon": (307, 5),
    "stretching_rack": (308, 3),
    "gibbet": (306, 2),
    "chopping_block": (310, 3),
    "dunking_stool": (311, 5),
}
G4_BT = {
    4: "ox_tether",
    6: "pitch_rig",
    62: "gallows",
    63: "stocks",
    65: "maypole",
    66: "garden",
    91: "cess_pit",
    92: "burning_stake",
    93: "gibbet",
    94: "dungeon",
    95: "stretching_rack",
    97: "chopping_block",
    98: "dunking_stool",
    100: "statue",
    101: "shrine",
    103: "dancing_bear",
}
BUILDINGS.update(G4_BUILDINGS)
G4_OFFERED = tuple(BUILDINGS)
# every mapper recorded from the real castle and town menus.
# The gates
# page's gatehouse icons open a second page with the two orientations; the UI sends them with PLACE_BUILDING p4
# 81 (first
# icon) or 80 (second) instead of 15, which placeBuilding (0x5162FA) turns into the footprint check's variant (p4 / 2).
G5_BUILDINGS = {
    "gatehouse_turned": (145, 5),
    "large_gatehouse_turned": (147, 7),
    "drawbridge": (105, 5),
    "killing_pit": (98, 1),
    "pitch_ditch": (99, 1),
    "dog_cage": (312, 3),
    "oil_smelter": (180, 4),
    "water_pot": (342, 4),
}
G5_BT = {28: "oil_smelter", 49: "drawbridge", 67: "killing_pit", 68: "pitch_ditch", 70: "water_pot", 99: "dog_cage"}
GATEHOUSE_P4 = {144: 81, 145: 80, 146: 81, 147: 80}
# A drawbridge goes on the gate axis of one of your gatehouses: the UI asks TileMapState 0x4FA2D0(x, y) (the top-left
# tile), which looks for the gatehouse's 5 (7) tiles along each side (offsets 0xB4AE20), allows only the sides its gate
# opens to (the gatehouse's +0x102 = its 81/80), and leaves TMS+0x554934 = 0 and TMS+0x554940 = 2 * the side, which the
# UI sends as PLACE_BUILDING p4 (0x4ED79D; recorded: 0 south, 4 north).
DRAWBRIDGE_SIDE, DB_REFUSED, DB_SIDE = 0x004FA2D0, TMS + 0x554934, TMS + 0x554940
BUILDINGS.update(G5_BUILDINGS)
# Flags and heads on spikes are not buildings: their icon, then a click on the top of one of your walls or
# towers, queues
# GCT 69 (player, x*8, y*8, the spot's height from TileMapState 0x4FFBA0, kind, p5) at 0x4467BC / 0x445751. Flag kinds
# 10..13 (mappers 120..123), p5 = player; heads kind 15, p5 = the UI's variant counter (0x01FE7C24, cosmetic).
DECORATE, DECORATIONS = 69, {"flag_1": 10, "flag_2": 12, "flag_3": 13, "flag_4": 11, "heads": 15}
BRAZIER = 14  # the gates page's brazier goes on a wall or tower top the same way: GCT 69 kind 14 (recorded; the UI
# leaves p5 as it was, 0x4458B4, the SDK sends 0), checked by 0x4FFF10 and with the height from 0x4FFB10 (0x44577C)
BRAZIER_SPOT, BRAZIER_HEIGHT = 0x004FFF10, 0x004FFB10
TOP_HEIGHT, DECO_VARIANT = 0x004FFBA0, 0x01FE7C24
# Upkeep (): a building panel's buttons and the granary's food toggles
REPAIR, SLEEP, PRODUCT = 68, 43, 33  # GCT_REPAIR (id, wood, stone, uid) 0x466160; sleep (BuildingType) 0x4660B0;
#                                      workshop product (id, weapon good, uid) 0x465200
REPAIR_COST, ENEMY_NEAR, AI_MATCH = 0x00410320, 0x004A15B0, 0x0191DD80  # the UI's repair checks (0x466160)
REPAIR_WOOD, REPAIR_STONE = 0x0112658C, 0x01126590  # where 0x410320 leaves the price it computed
# Only the tower and gatehouse panels have the Repair button (the handler is in 2 panel layouts; a damaged hovel's panel
# shows none, live)
REPAIRABLE = {
    "lookout_tower",
    "perimeter_tower",
    "defense_turret",
    "square_tower",
    "round_tower",
    "gatehouse",
    "large_gatehouse",
}
ASLEEP = PLAYER + 0x2194  # byte per BuildingType (< 91): 1 = every building of that type sleeps (0x4660F0, 0x40F750)
# the panels that carry the sleep button (group record with click 0x4660B0 in the menu table 0x5FA5A8;
# sections chosen
# by the building-select switch 0x463864/0x463990 on the building type). Every other type has no zz button, although
# 0x4660F0 itself only checks type < 91
SLEEPABLE = {3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23, 27, 30, 31, 32, 33, 34, 36, 37, 38, 70}
WEAPON_UI = {
    18: 0x01FE7E70,
    20: 0x01FE7E74,
    22: 0x01FE7E78,
    17: 0x01FE7E7C,
    19: 0x01FE7E80,
    21: 0x01FE7E84,
}  # button on
WORKSHOP_PRODUCTS = {
    12: ("bows", "crossbows"),
    14: ("spears", "pikes"),
    13: ("maces", "swords"),
}  # fletcher, poleturner, blacksmith
LAST_WEAPON = PLAYER + 0x10  # the UI writes the chosen weapon here after queueing (0x465292)
FOOD_BANNED = PLAYER + 0x2280  # short per granary food slot; the UI toggles it directly (0x43FBB0), no command
FOOD_SLOT = {"bread": 0, "cheese": 1, "meat": 2, "apples": 3}  # granary slot = good - 10 (its stores at +0x148, live)
# gates: a gatehouse's or drawbridge's panel button (0x465480) queues GCT 45 (id, state,
# uid) and then
# notes the state in your player record (+0x4); the executor 0x4654F0 keeps it at building +0x2A3 (10 or 11)
# and opens or
# shuts it (0x41C570). State values recorded from the panel's buttons. +0x2A3 is
# the request
# (10 close, 11 open; the building's update 0x423AB7 consumes it to 12), +0x2A2 the gate's phase: 0 open, 1 closing,
# 2 closed, 3 opening (a close request acts only on an open gate, an open request only on a closed one).
SET_GATE, GATE_STATE, GATE_PHASE, LAST_GATE = 45, 0x2A3, 0x2A2, PLAYER + 0x4
GATE_PHASES = {0: "open", 1: "closing", 2: "closed", 3: "opening"}
GATE_OPEN, GATE_CLOSED = 11, 10
GATES = {"gatehouse", "large_gatehouse", "drawbridge"}
# Tower engines: the military page's mangonel (mapper 210) or ballista (211) icon, then a click on your square or round
# tower (BT 77/78) on a tower-top tile (logic 0x10000000) with no unit on it, the tower carrying no engine yet
# (+0x295), where
# the UI checks the price (0x457B80) and queues GCT 42
# ((tower x + 2) * 8 + 4, (tower y + 2) * 8 + 4, the height there, unit type) (0x4453A0); engineers then man() it.
MOUNT, MOUNT_TOWERS, L_TOWER_TOP, TOWER_ENGINE = 42, {77, 78}, 0x10000000, 0x295
MOUNTS = {"mangonel": (210, 41), "ballista": (211, 61)}
MOUNTED_ENGINES = {41: "mangonel", 61: "ballista"}
CAN_PAY = 0x00457B80  # GameState (0x0112B0B8) thiscall (mapper, player, 0): non-zero if the player can pay for it
# The oil smelter: engineers selected, a click on it (click action 2) -> instruction 15 (id, uid) (0x4370F5);
# an engineer
# carrying oil, a click on the ground -> instruction 20 (x, y) (0x437684). (light cursor 12, 0x43550A-0x4355C8):
# archers or Arabian archers selected (0x535560), the mouse over a pitch-ditch tile of your team, the selection's lead
# unit within 3 tiles of a lit brazier (0x401A50 on the entity manager 0x2350300: kind 14, state 2, height within 45),
# and the pitch tile within the squared distance at 0x4355C2 (49 tiles) of the lead -> instruction 34 (pitch index,
# serial) (0x437098). The archers shoot a burning arrow at the ditch; a lit tile burns 20 ticks, lights its pitch
# neighbours, then burns 200 more (0x511540).
I_OIL_DUTY, I_POUR_OIL, I_LIGHT = 15, 20, 34
POUR_KNOWN = False  # see pour_oil
DELETE_WALL = 41
LIGHTERS = {22, 70}
# The pitch-ditch list (TileMapState +0x53F084, records 1..count of 20 bytes: tile, serial, owner, x, y, ..., state)
FIRE_SPOTS, FIRE_SPOT_SIZE, FIRE_SPOTS_N = 0x01FD2290, 20, 2000  # read from +4: (serial int, owner short, x, y)
PITCH_COUNT, BRAZIER_NEAR, ENTITIES, TEAM = TMS + 0x552904, 0x00401A50, 0x02350300, 0x0117D548
U_HEIGHT_A, U_HEIGHT_B = 0xBA, 0xBC  # a unit's height is the sum of these two shorts (the light cursor's 0x435565)
LIGHT_RANGE2 = 0x004355C2  # the UI's own squared-distance limit, read from the game's code
# The gates page's moat button, then a drag: GCT 21 (x, y, brush 2, 0x40000000, 0) at every other tile of the
# drag (executor
# 0x4813C0 -> the map brush 0x512940, which marks the moat plan bit 0x40000000 on the tiles it accepts).
BRUSH, MOAT_BIT, MOAT_BRUSH = 21, 0x40000000, 2
UNPLAN_FLAG = 1  # the "don't dig" button's drag: the same stamps with p4 = 1 (recorded)
L_MOAT_PLAN, L_MOAT = 0x4000, 0x40000000  # the logic bits of a planned and of a dug moat tile (live)
# Diggers selected, then a click on a moat plan tile: GCT 36 instruction 6 (tribe, 6, x, y, 1000)
# (UIT_DIG_MOAT; recorded)
I_DIG_MOAT, DIG_P4 = 6, 1000
# Diggers over a moat tile the UI lets them fill (its hover 0x4E85E0: moat bit set and FILLABLE(tile) != 0, the tile in
# TileMapState's list at +0x500880): instruction 7 (x, y, 1000) (0x437229).
I_FILL_MOAT, FILLABLE = 7, 0x00500250
# the moat list (TileMapState +0x500870, 16-byte records: tile int, x, y, ..., owner byte +0xC, depth
# +0xD, kind +0xE
# 1 plan / 2 dug, claims +0xF; count at +0x53F070). Units fill (0x5111D0 mode 2) only another team's dug entries.
MOAT_LIST, MOAT_COUNT, MOAT_REC = TMS + 0x500870, TMS + 0x53F070, 16
DIGGERS = {
    22,
    24,
    25,
    26,
    30,
    71,
}  # archers, spearmen, pikemen, macemen, engineers, slaves (manual; the UI taps check two)
DIGGER_NAMES = "archers, spearmen, pikemen, macemen, engineers and slaves"
# the Allies panel, read from its handlers: GCT 113 with p0 = kind
ALLY_REQUEST, ALLY_ORDER, ALLY_ASK, ALLY_SEND, ALLY_REFUSE = 113, 0, 1, 2, 3
STORE_ROOM, STORE_ROOM_THIS = 0x0040C1F0, 0x00F98520  # free room for a good in a player's stores (-1: no store)
ALLY_WILLING, AI_PERSONALITIES = 0x004D0520, 0x023FC8E8  # will the AI ally give (ally, good, qty)? 0 = no
REQ_GOOD, REQ_QTY, REQ_STRIDE = 0x0115F61C, 0x0115F630, 0x1CFA  # word pairs: slot (asked player*0x1CFA + asker)*2
ALLY_ORDER_KIND, ALLY_ORDER_TARGET = 0x0115F644, 0x0115F648  # + player*STRIDE: 0 none / 1 attack (target) / 2 defend
# information panels (scribe pages 72-79 drawn by 0x43E6C0.. via table 0x449994; merit 0x4AE0F0)
REC0 = 0x0115BDF8  # player 0's record; player p at REC0 + p*STRIDE (player 1 = 0x0115F7EC)
GAME_CORE, ALE_COVERAGE = 0x0112B0B8, 0x00458E20  # ale coverage % of a player (thiscall core, player)
POP_MONTHS, POP_HISTORY, MERIT_ACTIVE = (
    0x0117EAA8,
    0x0117D590,
    0x01A27056,
)  # graph length, shorts [player*0x258], byte per player
GAME_TEXT, GAME_TEXT_THIS = 0x0046A050, 0x02157578  # (group, id) -> the string a panel draws
HP_BAR_PANELS = frozenset(
    (
        "large_gatehouse",
        "gatehouse",
        "lookout_tower",
        "perimeter_tower",
        "defense_turret",
        "square_tower",
        "round_tower",
    )
)  # the only panels with a health bar (0x43E350)
WORKER_CASES, WORKER_CLASSIFY = (
    0x00447A0C,
    0x00537F60,
)  # widget case per (type - 5); the worker classifier (thiscall UNITS_STATE)
WORKER_GOOD_SLOT = (
    0x01997FCC  # the classifier's out-int: the game's own command-parameter scratch (p5), rewritten per command
)
WORKSHOP_LINE1 = {17: 7, 18: 8, 19: 9, 20: 10, 21: 6, 22: 5}  # building +0x2A2 state -> text id (table 0x4396F8)
WORKSHOP_LINE2 = {17: 5, 18: 6, 19: 7, 20: 8, 21: 9, 22: 10}  # building +0x2A4 state -> text id (table 0x439710)
TAX_POP = (
    175,
    125,
    75,
    25,
    -50,
    -100,
    -150,
    -200,
    -300,
    -400,
    -500,
    -600,
)  # popularity per tax level (0..11, 3 = none)
REPORT_PAGES = ("popularity", "fear", "religion", "army", "food", "population", "stores", "weapons", "merit")
STORE_GOODS = ("wood", "hops", "stone", "iron", "pitch", "wheat", "ale", "flour")
WEAPON_GOODS = ("bows", "crossbows", "spears", "pikes", "maces", "swords", "leather_armor", "metal_armor")
ARMY_PAGE_TYPES = frozenset((22, 24, 26, 23, 25, 27, 28, 30, 37, 29, 60, 59, 58, 39, 40, 41, 61, 5, *range(70, 78)))


def RELIGION_POP(blessed):
    return 0 if blessed < 25 else 50 if blessed < 50 else 100 if blessed < 75 else 150 if blessed < 95 else 200


def _pop_drawn(v):
    """0x433C20 draws a popularity amount as trunc(v*4/100), i.e. v/25 rounded toward zero."""
    return -((-v * 4) // 100) if v < 0 else (v * 4) // 100


# siege engines, recorded from the real UI: with engineers
# selected, the
# unit panel's mallet opens six engine icons; an icon then a map click queues PLACE_BUILDING (28, x, y, mapper,
# 3, 15, the
# engineers' tribe). The selected engineers walk to the tent, build the engine (a unit) there and crew it. Price: the
# game's cost table (COSTS) at the BuildingType the mapper maps to (0x409370). name: (mapper, BuildingType, unit type).
SIEGE_ENGINES = {
    "catapult": (190, 80, 39),
    "trebuchet": (191, 81, 40),
    "battering_ram": (193, 83, 59),
    "siege_tower": (192, 82, 58),
    "portable_shield": (194, 84, 60),
    "fire_ballista": (358, 54, 77),
}
ENGINE_NAMES = {t: n for n, (_, _, t) in SIEGE_ENGINES.items()}
TENT_SIDE = 3
# Crew an engine needs: UnitsState 0x5334A0 returns this size minus its crew (+0x3B4; their ids at +0x314).
# Immediates in
# that code: catapult 2, trebuchet 3, ram 4 (also siege tower 4, shield 1, fire ballista 2). With no crew an
# engine takes
# no order (0x5287F6) and a moving engine moves only with its full crew (0x526856).
CREW_SIZE = {39: 2, 40: 3, 59: 4, 58: 4, 60: 1, 77: 2, 41: 2, 61: 2}  # tower mangonel 41, ballista 61 (0x533525)
U_CREW, U_AMMO = 0x3B4, 0x362  # shorts: engineers crewing it now; shots left (a catapult starts with 20)
I_MAN, I_UNMAN = (
    16,
    17,
)  # GCT 36 instructions: man (engine id, uid) for engineers; unman (engine id, uid, 0) for the engine
BUY_AMMO = 86  # GCT 86 (engine id): the engine panel's ammo button -> 0x465F20: 10 stone (stock index 4) for 20 shots
AMMO_STONE, AMMO_SHOTS, AMMO_ENGINES = (
    10,
    20,
    (39, 40),
)  # immediates at 0x465F2C / 0x465F53; the button is on these panels
# "Launch Cow" on a catapult's or trebuchet's panel (0x446ABB: only with cows and crew), then a map click:
# instruction
# 22 (x, y, 15). The handler (0x528756) keeps 22 only for types 39/40 with cows, else it makes it a plain shot
# (5). A cow
# is a dairy farm's cattle (unit 51); the throw takes one (0x569066) and the count (int, player +0x2278) drops by 1.
COWS, I_THROW_COW = PLAYER + 0x2278, 22
# Laddermen (29): with them selected, an enemy wall shows the ladder cursor (click action 5); a click queues
# instruction 24
# with the wall tile's index (0x537159), handled at 0x52951B for laddermen only.
I_SET_LADDER = 24
# Tunnelers (5): the unit panel's "Dig Tunnel Here", then a map click, places a tunnel entrance like a siege tent:
# PLACE_BUILDING (x, y, mapper 66, 3, 15, the tunnelers' tribe) at 0x44608B; the tunneler then digs towards the enemy.
TUNNEL = (66, 3)


def footprint(name):
    """(mapper, side) of a building, or of an engine's siege tent."""
    if name == "tunnel":
        return TUNNEL
    return BUILDINGS[name] if name in BUILDINGS else (SIEGE_ENGINES[name][0], TENT_SIDE)


MAP_CHARS = {
    "hovel": "h",
    "woodcutter": "w",
    "market": "m",
    "chapel": "c",
    "apple_orchard": "a",
    "dairy_farm": "d",
    "hunters_post": "p",
    "wheat_farm": "f",
    "mill": "n",
    "bakery": "k",
    "granary": "g",
    "stockpile": "s",
    "quarry": "q",
    "brewery": "b",
    "inn": "i",
    "well": "o",
    "hops_farm": "j",
    "church": "c",
    "keep": "K",
}

CONTAINER = os.environ.get("CRUSADER_CONTAINER")
IN_CONTAINER = os.path.exists("/opt/crusader")


class RealGameError(Exception):
    pass


def _proc(pid, name):
    """/proc/<pid>/<name>, or "" when the process exited after pgrep listed it (another container stopping)."""
    try:
        return open(f"/proc/{pid}/{name}").read()
    except (FileNotFoundError, ProcessLookupError):
        return ""


def game_pid(process_name="Stronghold Crusader.exe"):
    pids = subprocess.run(["pgrep", "-f", process_name], capture_output=True, text=True).stdout.split()
    pids = [p for p in pids if _proc(p, "statm")]
    if not pids:
        raise RealGameError("game is not running")
    # the game is the largest process with that name; the others are Wine launcher stubs
    return max(pids, key=lambda p: int((_proc(p, "statm").split() or [0, 0])[1]))


def i32(pid, addr):
    with pid.memory.file() as mem:
        mem.seek(addr)
        return int.from_bytes(mem.read(4), "little", signed=True)


def read_bytes(pid, addr, n):
    with pid.memory.file() as mem:
        mem.seek(addr)
        return mem.read(n)


def write_i32(pid, addr, value):
    with pid.memory.file() as mem:
        mem.seek(addr)
        mem.write(int(value).to_bytes(4, "little", signed=True))


_GAME_DIRS = {}


def _ucp_log(pid):
    game_dir = _GAME_DIRS.get(pid, "/opt/crusader")
    try:
        return open(f"/proc/{pid}/root/{os.fspath(game_dir).lstrip('/')}/ucp3.log", errors="replace").read()
    except FileNotFoundError as exc:
        raise RealGameError("bridge log not available") from exc


def _hook_address(pid, label, size):
    if label not in pid.hooks:
        address = int(re.findall(rf"{re.escape(label)} at 0x([0-9A-F]+)", _ucp_log(pid))[-1], 16)
        pid.memory.register_region(address, size)
        pid.hooks[label] = address
    return pid.hooks[label]


def target_address(pid):
    return _hook_address(pid, "advance target", 4)


def mailbox_address(pid):
    return _hook_address(pid, "command mailbox", 28)


def wait_for(pred, timeout, what, every=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if pred():
                return
        except (RealGameError, IndexError):
            pass  # game still starting
        time.sleep(every)
    raise RealGameError(f"timed out waiting for {what}")


# ---- menus


def _xdo(*args):
    cmd = ["xdotool", *map(str, args)]
    if not IN_CONTAINER:
        if not CONTAINER:
            raise RealGameError("CRUSADER_CONTAINER must be set when running outside the game container")
        cmd = ["docker", "exec", CONTAINER, *cmd]
    subprocess.run(cmd, check=True)


def click(x, y):
    """The game ignores instant clicks, so press and release separately."""
    _xdo("mousemove", x, y)
    _xdo("mousedown", 1)
    time.sleep(0.15)
    _xdo("mouseup", 1)


def start_match(speed=1000, timeout=180, *, process_lookup=None):
    """From a freshly started game, reach a running Castle Builder match on the first map
    ("A Mighty Oasis"), paused by the hook. Every step waits on the game's own menu state."""
    lookup = process_lookup or game_pid
    wait_for(lambda: mailbox_address(lookup()) and i32(lookup(), MENU) == MENU_ENTER_NAME, timeout, "title screen")
    pid = lookup()
    for screen, (x, y), nxt in (
        (MENU_ENTER_NAME, (509, 357), MENU_MAIN),  # Start Game
        (MENU_MAIN, (430, 367), MENU_MAP_CHOICE),  # Castle Builder
        (MENU_MAP_CHOICE, (825, 660), None),
    ):  # next arrow: start the map
        for _ in range(10):
            if i32(pid, MENU) != screen:
                break
            click(x, y)
            try:
                wait_for(lambda: i32(pid, MENU) != screen, 5, f"menu {screen} to change")  # noqa: B023
            except RealGameError:
                continue
        if nxt is not None and i32(pid, MENU) != nxt:
            raise RealGameError(f"expected menu {nxt} after {screen}, got {i32(pid, MENU)}")
    wait_for(lambda: i32(pid, MENU) == MENU_IN_GAME and i32(pid, PAUSED) == 1, timeout, "match to start, paused")
    write_i32(pid, SPEED, speed)
    return pid


# Skirmish setup (main menu "Crusader" -> skirmish -> setup screen, menu view 20). The lobby lives in
# GameSynchronyState (0x0191D768): currentAIArray int[9] at +0x714 (0 = no AI; 1 = the Rat ... in the AI picker's
# portrait order). The map list shows ResourceManager names in LOAD_ORDER order, like the Load dialog; its scroll
# offset and selected row are at 0x01A24A64 / 0x01A24A6C (SkirmishLobbySetupStructure::commitSkirmishSettings
# 0x486C40 copies them), the selected map's name at 0x01A22F9C.
MENU_CRUSADER, MENU_SKIRMISH = 55, 20
AI_SLOTS = 0x0191D768 + 0x714
SK_SCROLL, SK_SELECTED, SK_MAP_NAME = 0x01A24A64, 0x01A24A6C, 0x01A22F9C
SK_ROWS, SK_ROW0_Y, SK_ROW_H = 8, 465, 20
# The picker shows 16 portraits in two rows of 8 (screenshot 2026-11-05); portrait i (0-based, row-major) puts AI number
# i + 1 in the slot, which start_skirmish checks from game state. Names in the game's own order.
AI_ORDER = [
    "rat",
    "snake",
    "pig",
    "wolf",
    "saladin",
    "caliph",
    "sultan",
    "richard",
    "frederick",
    "philip",
    "wazir",
    "emir",
    "nizar",
    "sheriff",
    "marshal",
    "abbot",
]
AI_PORTRAITS = {n: (172 + round(76.2 * (i % 8)), 345 + 77 * (i // 8)) for i, n in enumerate(AI_ORDER)}
AI_PICKER_OPEN = 0x01FE7D08  # 1 while the lord picker is up (seen live: 0 -> 1 -> 0 around open/close)


def _cstr(pid, addr, n=80):
    with pid.memory.file() as mem:
        mem.seek(addr)
        return mem.read(n).split(b"\0")[0].decode("latin-1")


def start_skirmish(map_name="Inches Apart", ai="rat", speed=1000, timeout=180, *, process_lookup=None):
    """From a freshly started game, start a skirmish on `map_name` against one CPU lord (`ai`) through the game's
    own setup screen, checking every step against game state; the match pauses on its first tick."""
    lookup = process_lookup or game_pid
    wait_for(lambda: mailbox_address(lookup()) and i32(lookup(), MENU) == MENU_ENTER_NAME, timeout, "title screen")
    pid = lookup()
    _click_until(pid, (509, 357), lambda: i32(pid, MENU) == MENU_MAIN, "main menu")
    _click_until(pid, (430, 227), lambda: i32(pid, MENU) == MENU_CRUSADER, "Crusader game types")
    _click_until(pid, (650, 380), lambda: i32(pid, MENU) == MENU_SKIRMISH, "skirmish setup")
    _click_until(pid, (612, 140), lambda: i32(pid, AI_PICKER_OPEN) == 1, "AI picker")
    n = AI_ORDER.index(ai) + 1
    _click_until(pid, AI_PORTRAITS[ai], lambda: i32(pid, AI_SLOTS + 8) == n, f"{ai} (AI {n}) in slot 2")
    _click_until(pid, (731, 620), lambda: i32(pid, AI_PICKER_OPEN) == 0, "AI picker to close")
    if [i32(pid, AI_SLOTS + 4 * i) for i in range(9)] != [0, 0, n, 0, 0, 0, 0, 0, 0]:
        raise RealGameError("expected exactly one AI lord, in slot 2")
    names = save_names(pid)
    if names.count(map_name) != 1:
        raise RealGameError(f"map {map_name!r} is not in the skirmish list exactly once")
    row = names.index(map_name)
    write_i32(pid, SK_SCROLL, row)  # scroll the list so the map is the top visible row (UI state only)
    _click_until(pid, (760, SK_ROW0_Y), lambda: _cstr(pid, SK_MAP_NAME) == map_name, f"map {map_name!r} selected")
    if i32(pid, SK_SCROLL) + i32(pid, SK_SELECTED) != row:
        raise RealGameError("the selected map row is not the one asked for")
    _click_until(pid, (820, 655), lambda: i32(pid, MENU) == MENU_IN_GAME, "skirmish to start", tries=3)
    wait_for(lambda: i32(pid, PAUSED) == 1, timeout, "match to start, paused")
    write_i32(pid, SPEED, speed)
    return pid


# Built-in missions (observed live). Crusader Trail: main menu "Crusader" (menu 55) -> the upper map tile
# (menu 57, the trail map; TRAIL_SELECT 0 = the Crusader Trail, 1 = the Warchest trail whose first mission is "51. First
# Step") -> right hand (menu 56, the mission card) -> right hand: the match starts in game mode 3. Historical campaigns:
# main menu (menu 42) -> "The Call to Arms" (menu 38, mission list) -> row 1 -> right hand -> two briefing book pages
# (menus 52, 50, 51) -> objectives (menu 28) -> right hand: the match starts in game mode 0. A mission's scenario events
# live in MapPropertiesState (EVENTS); event 0 of campaign mission 1 is its "Acquire Gold: 450" goal (short at +0x2C).
GAME_MODE = 0x01FE7D78  # 2 Castle Builder, 3 Crusader Trail / skirmish-style mission, 0 historical campaign
TRAIL_SELECT = 0x01FE9CAC
MENU_TRAIL, MENU_TRAIL_CARD, MENU_CAMPAIGNS, MENU_CAMPAIGN_LIST = 57, 56, 42, 38
MENU_BOOK, MENU_OBJECTIVES = (52, 50, 51), 28
MENU_NEXT_MISSION = 50  # a won campaign mission goes straight to the next mission's book page (live: mission 2 card)
WINNERS = 0x0117EF40  # short per player (index = player): 1 for the winners when the game ends a match (0x486600)
MISSIONS = {
    # name: the game state start_mission checks once the match has started
    "trail-1": {"mode": 3, "date": (0, 1100), "ai_slots": [0, 0, 7, 0, 0, 0, 0, 0, 0]},
    "campaign-1": {"mode": 0, "date": (3, 1094), "goal_gold": 450},
}


def start_mission(name, speed=1000, timeout=180):
    """From a freshly started game, start built-in mission `name` (trail-1 or campaign-1) through the game's own menus,
    checking every step against game state; the match pauses on its first tick. Returns pid."""
    m = MISSIONS[name]
    wait_for(lambda: mailbox_address(game_pid()) and i32(game_pid(), MENU) == MENU_ENTER_NAME, timeout, "title screen")
    pid = _require_game_pid(game_pid())

    def menu(v):
        return lambda: i32(pid, MENU) == v

    _click_until(pid, (509, 357), menu(MENU_MAIN), "main menu")
    if name == "trail-1":
        _click_until(pid, (430, 227), menu(MENU_CRUSADER), "Crusader game types")
        _click_until(pid, (315, 350), menu(MENU_TRAIL), "Crusader Trail map")
        if i32(pid, TRAIL_SELECT) != 0:
            raise RealGameError("the trail map is not the Crusader Trail")
        _click_until(pid, (828, 640), menu(MENU_TRAIL_CARD), "mission card")
        _click_until(pid, (828, 640), menu(MENU_IN_GAME), "mission to start", tries=3)
    else:
        _click_until(pid, (430, 297), menu(MENU_CAMPAIGNS), "historical campaigns")
        _click_until(pid, (430, 227), menu(MENU_CAMPAIGN_LIST), "The Call to Arms missions")
        click(500, 283)  # row 1 "Nicaea, Arrival in The Holy Land" (the only row before the campaign is played)
        _click_until(pid, (828, 645), lambda: i32(pid, MENU) in MENU_BOOK, "mission book")
        _click_until(pid, (600, 650), menu(MENU_OBJECTIVES), "objectives", tries=20)
        _click_until(pid, (828, 600), menu(MENU_IN_GAME), "mission to start", tries=3)
    wait_for(lambda: i32(pid, PAUSED) == 1, timeout, "match to start, paused")
    got = {"mode": i32(pid, GAME_MODE), "date": (i32(pid, MONTH), i32(pid, YEAR))}
    if "ai_slots" in m:
        got["ai_slots"] = [i32(pid, AI_SLOTS + 4 * i) for i in range(9)]
    if "goal_gold" in m:
        with pid.memory.file() as mem:
            mem.seek(EVENTS + 0x2C)
            got["goal_gold"] = int.from_bytes(mem.read(2), "little")
    if got != m:
        raise RealGameError(f"{name}: expected {m}, the game has {got}")
    write_i32(pid, SPEED, speed)
    return pid


# Load dialog (main menu key icon -> Game Options -> Load). The modal id says which dialog is up; the list
# shows ResourceManager file names in the order of LOAD_ORDER (row -> file index), and a click on a row
# sets LOAD_SEL_INDEX (+ the scroll offset LOAD_SEL_OFFSET).
MODAL = 0x01126604
MODAL_NONE, MODAL_OPTIONS, MODAL_LOAD = 0, 44, 9
RESOURCES = 0x011BF130  # ResourceManager: +0 file count, +0xBC8 names char[500][1001]
LOAD_ORDER, LOAD_SEL_INDEX, LOAD_SEL_OFFSET = 0x01126E28, 0x01126624, 0x01126628
LOAD_ROWS, LOAD_ROW0_Y, LOAD_ROW_H = (
    16,
    244,
    20,
)  # visible rows (16: the 20th save, at the end, sits on row 16 fully scrolled) and their screen layout at 1024x768
MENU_IN_GAME = 14
LAST_LOAD_LIST = []  # the load dialog's rows at the last load_save, for checks


def save_names(pid):
    """File names in the load dialog, top row first."""
    with pid.memory.file() as mem:

        def name(i):
            mem.seek(RESOURCES + 0xBC8 + 1001 * i)
            return mem.read(1001).split(b"\0")[0].decode("latin-1")

        return [name(i32(pid, LOAD_ORDER + 4 * row)) for row in range(i32(pid, RESOURCES))]


def _click_until(pid, xy, done, what, tries=10):
    for _ in range(tries):
        if done():
            return
        click(*xy)
        try:
            wait_for(done, 3, what)
        except RealGameError:
            continue
    if not done():
        raise RealGameError(f"gave up waiting for {what}")


def seed_slot_address(pid):
    return _hook_address(pid, "rng seed slot", 4)


def load_save(name, speed=1000, timeout=180, seed=None, *, process_lookup=None):
    """From a freshly started game, load the save called `name` through the game's own menus, checking
    every step against game state, and stop paused before the first tick after loading (at the saved
    tick). With a seed (> 0), crusader-bridge re-seeds the game's RNG at the start of that first tick, so
    identical commands give identical games."""
    lookup = process_lookup or game_pid
    wait_for(lambda: mailbox_address(lookup()) and i32(lookup(), MENU) == MENU_ENTER_NAME, timeout, "title screen")
    pid = lookup()
    _click_until(pid, (509, 357), lambda: i32(pid, MENU) == MENU_MAIN, "main menu")
    _click_until(pid, (640, 632), lambda: i32(pid, MODAL) == MODAL_OPTIONS, "Game Options dialog")
    _click_until(pid, (509, 305), lambda: i32(pid, MODAL) == MODAL_LOAD and i32(pid, RESOURCES) > 0, "Load dialog")
    global LAST_LOAD_LIST
    names = LAST_LOAD_LIST = save_names(pid)
    if names.count(name) != 1:
        raise RealGameError(f"save {name!r} is not in the load list exactly once: {names}")
    row = names.index(name)
    while row - i32(pid, LOAD_SEL_OFFSET) >= LOAD_ROWS:  # scroll down one row at a time
        off = i32(pid, LOAD_SEL_OFFSET)
        _click_until(pid, (812, 545), lambda: i32(pid, LOAD_SEL_OFFSET) > off, "load list to scroll")  # noqa: B023
    y = LOAD_ROW0_Y + LOAD_ROW_H * (row - i32(pid, LOAD_SEL_OFFSET))
    _click_until(
        pid, (560, y), lambda: i32(pid, LOAD_SEL_INDEX) + i32(pid, LOAD_SEL_OFFSET) == row, f"row {row} selected"
    )
    if save_names(pid)[i32(pid, LOAD_SEL_INDEX) + i32(pid, LOAD_SEL_OFFSET)] != name:
        raise RealGameError(f"selected row is not {name!r}")
    if seed:
        write_i32(pid, seed_slot_address(pid), seed)
    _click_until(pid, (306, 503), lambda: i32(pid, MODAL) != MODAL_LOAD, "Load to start")
    wait_for(
        lambda: i32(pid, MENU) == MENU_IN_GAME and i32(pid, TICK) > 0 and i32(pid, PAUSED) == 1,
        timeout,
        "loaded match to pause before its first tick",
    )
    write_i32(pid, SPEED, speed)
    return pid


# ---- terrain


class Terrain:
    """One snapshot of the tile layers."""

    def __init__(self, pid):
        with pid.memory.file() as mem:
            mem.seek(ROWS)
            rows = [struct.unpack("<iii", mem.read(12)) for _ in range(MAP_SIDE)]

            def layer(off, code, size):
                mem.seek(TMS + off)
                return array.array(code, mem.read(N_TILES * size))

            self.logic = layer(LOGIC, "i", 4)
            self.logic2 = layer(LOGIC2, "B", 1)
            self.building = layer(BUILDING_LAYER, "h", 2)
            self.height = layer(HEIGHT, "B", 1)
            self.unit = layer(UNIT_LAYER, "h", 2)
        self.row_start = [r[0] for r in rows]
        self.row_lo = [rows[y - 1][2] if y else 0 for y in range(MAP_SIDE)]
        self.row_hi = [r[2] for r in rows]

    def tile(self, x, y):
        if 0 <= y < MAP_SIDE and 0 <= x < MAP_SIDE:
            i = self.row_start[y] + x
            if self.row_lo[y] <= i < self.row_hi[y]:
                return i
        return None

    def free(self, i):
        lg = self.logic[i]
        return bool(lg & L_LAND) and not lg & (L_BLOCKED | L_WALL) and self.building[i] == 0 and self.unit[i] == 0

    def blocker(self, i):
        """What stops a building on tile i (None: nothing the map shows)."""
        lg = self.logic[i]
        return (
            "a building"
            if self.building[i]
            else "a unit"
            if self.unit[i]
            else "water or off-limits ground"
            if not lg & L_LAND
            else "a wall"
            if lg & L_WALL
            else "farmland"
            if lg & L_FARMLAND
            else "trees"
            if lg & L_TREES
            else "rock or another obstacle"
            if lg & L_BLOCKED
            else None
        )

    def char(self, x, y, names):
        i = self.tile(x, y)
        if i is None:
            return " "
        lg = self.logic[i]
        if self.building[i]:
            return MAP_CHARS.get(names.get(self.building[i]), "B")
        if not lg & L_LAND:
            return "~"
        if lg & L_FARMLAND:
            return "f"
        if lg & (L_BLOCKED | L_WALL):
            return "^"
        return "," if self.logic2[i] & FARMABLE else "."

    def site_error(self, building, x, y, taken=None):
        """None if the map allows `building` at (x, y), else why not. taken: {(x, y): what} for tiles of builds queued
        but not yet on the map."""
        _kind, size = footprint(building)
        h = None
        for dy in range(size):
            for dx in range(size):
                i = self.tile(x + dx, y + dy)
                if i is None:
                    return "off the map"
                if taken and (x + dx, y + dy) in taken:
                    return f"tile ({x + dx},{y + dy}) is taken by {taken[(x + dx, y + dy)]}"
                if not self.free(i):
                    return f"tile ({x + dx},{y + dy}) is not free: {self.blocker(i)}"
                if building == "iron_mine" and not self.logic[i] & L_IRON:
                    return f"tile ({x + dx},{y + dy}) is not iron ore"
                if building in FARMS and not self.logic2[i] & FARMABLE:
                    return f"tile ({x + dx},{y + dy}) is not farmable grass"
                h = self.height[i] if h is None else h
                if self.height[i] != h:
                    return f"ground is not flat at ({x + dx},{y + dy})"
        return None

    def find_sites(self, building, limit=5, near=(235, 230), taken=None, accept=None, region=None):
        """Up to `limit` top-left corners where the map allows `building`, nearest to `near` first, no two overlapping.
        taken: tiles of queued builds (as site_error). accept(x, y): a further check (the game's own), tried on at most
        10 * limit candidates. region {y: (x0, x1)}: the whole footprint inside these tiles."""
        size = side = footprint(building)[1]
        need_grass = building in FARMS
        need_iron = building == "iron_mine"
        logic, logic2, bld, unit = self.logic, self.logic2, self.building, self.unit
        # Each row as one big int, one byte per tile (1 = usable), so "size tiles in a row are usable" is size
        # shifted ANDs and "size rows" is size ANDs: whole rows at a time instead of tile by tile.
        rows = []
        for y in range(MAP_SIDE):
            start = self.row_start[y]
            lo, hi = max(self.row_lo[y], start), min(self.row_hi[y], start + MAP_SIDE)
            ok = bytearray(MAP_SIDE)
            ok[lo - start : hi - start] = bytes(
                1
                if lg & L_LAND
                and not lg & (L_BLOCKED | L_WALL)
                and b == 0
                and u == 0
                and (g & FARMABLE or not need_grass)
                and (lg & L_IRON or not need_iron)
                else 0
                for lg, b, u, g in zip(logic[lo:hi], bld[lo:hi], unit[lo:hi], logic2[lo:hi], strict=False)
            )
            for tx, ty in taken or ():
                if ty == y and 0 <= tx < MAP_SIDE:
                    ok[tx] = 0
            if region is not None:  # only tiles x0..x1 of each row y in region (the camera view)
                a, b = region.get(y, (MAP_SIDE, MAP_SIDE - 1))
                ok[:a] = bytes(min(a, MAP_SIDE))
                ok[b + 1 :] = bytes(max(MAP_SIDE - b - 1, 0))
            r = h = int.from_bytes(ok, "little")
            for k in range(1, size):
                h &= r >> (8 * k)
            rows.append(h)
        cx, cy = near
        spots = []
        for y in range(MAP_SIDE - size + 1):
            v = rows[y]
            for k in range(1, size):
                v &= rows[y + k]
            if v:
                dy2 = (y - cy) ** 2
                spots += [
                    ((m.start() - cx) ** 2 + dy2, m.start(), y)
                    for m in re.finditer(b"\x01", v.to_bytes(MAP_SIDE, "little"))
                ]
        heapq.heapify(spots)  # same order as sorting them, popped only as far as needed
        out, tries = [], 10 * limit
        while spots and len(out) < limit and tries:  # flatness is rare to fail; check it only on candidates
            _, x, y = heapq.heappop(spots)
            if any(abs(x - o["x"]) < side and abs(y - o["y"]) < side for o in out):
                continue
            if self.site_error(building, x, y) is None:
                if accept:
                    tries -= 1
                    if not accept(x, y):
                        continue
                out.append({"x": x, "y": y})
        return out


def buildings(pid, terrain, names=None):
    """Buildings with a name in `names` (BuildingType -> name; default BT_NAMES): id, type name, top-left tile."""
    names = BT_NAMES if names is None else names
    first = {}
    for y in range(MAP_SIDE):
        for i in range(terrain.row_lo[y], terrain.row_hi[y]):
            b = terrain.building[i]
            if b > 0:
                x = i - terrain.row_start[y]
                fx, fy = first.get(b, (x, y))
                first[b] = (min(fx, x), min(fy, y))
    out = []
    with pid.memory.file() as mem:
        for b, (x, y) in sorted(first.items()):
            mem.seek(BUILDINGS_BASE + b * BUILDING_SIZE + B_TYPE)
            kind, _, owner, uid = struct.unpack("<hhhi", mem.read(10))
            name = "keep" if 40 <= kind <= 44 else names.get(kind)
            if name:  # skip keep doors, signposts, the campfire and other map furniture
                mem.seek(BUILDINGS_BASE + b * BUILDING_SIZE + B_HP)
                hp, max_hp = struct.unpack("<hh", mem.read(4))
                out.append(
                    {"id": b, "type": name, "x": x, "y": y, "owner": owner, "uid": uid, "hp": hp, "max_hp": max_hp}
                )
    return out


def ascii_map(pid, terrain=None):
    terrain = terrain or Terrain(pid)
    names = {b["id"]: b["type"] for b in buildings(pid, terrain)}
    return "\n".join("".join(terrain.char(x, y, names) for x in range(MAP_SIDE)) for y in range(MAP_SIDE))


# ---- commands and time


def queue_command(command_type, *params, pid=None, timeout=5):
    """Hand a command to the game's own command queue (crusader-bridge picks it up on the next frame).
    It runs when game time next moves, like a click in the UI."""
    pid = _require_game_pid(pid)
    box = mailbox_address(pid)
    for i, v in enumerate((list(params) + [0] * 6)[:6]):
        write_i32(pid, box + 4 + 4 * i, v)
    write_i32(pid, box, command_type)
    wait_for(lambda: i32(pid, box) == 0, timeout, "the game to pick up the command", every=0.002)


def ui_taps(pid, since=0):
    """Commands queued since tap number `since` (crusader-bridge's ring of every queueCommand call, UI, AI or mailbox):
    (n, [type, p0..p5], return address). The ring keeps the last 64."""
    ring = int(re.findall(r"ui tap at 0x([0-9A-F]+)", _ucp_log(pid))[-1], 16)
    with pid.memory.file() as mem:
        mem.seek(ring)
        n = struct.unpack("<i", mem.read(4))[0]
        out = []
        for k in range(max(since, n - 64), n):
            mem.seek(ring + 32 + 32 * (k % 64))
            *tup, ret = struct.unpack("<7iI", mem.read(32))
            out.append((k, tup, ret))
    return n, out


def ui_write(addr, value, size=4, pid=None):
    """Write `value` (size 1, 2 or 4 bytes) at `addr` inside the next frame, at the mailbox point, the way a UI handler
    that writes state directly does (crusader-bridge op 0x7F000003); never a host write in the middle of a frame."""
    if size not in (1, 2, 4):
        raise RealGameError("size must be 1, 2 or 4")
    queue_command(0x7F000003, addr, value, size, pid=pid)


def game_call(fn, this=0, *args, pid=None):
    """Call the game's own function `fn` (ecx = this, up to 4 stack args) inside the next frame at the mailbox point,
    where UI handlers run (crusader-bridge op 0x7F000004), and return its eax as a signed int."""
    if len(args) > 4:
        raise RealGameError("at most 4 arguments")
    pid = _require_game_pid(pid)
    queue_command(0x7F000004, fn, this, *args, pid=pid)
    return i32(pid, int(re.findall(r"game call at 0x([0-9A-F]+)", _ucp_log(pid))[-1], 16))


def build(name, x, y, pid=None, p4=15):
    kind, size = BUILDINGS[name]
    queue_command(PLACE_BUILDING, x, y, kind, size, p4, 0, pid=pid)


_PLACE_SLOT = {}
# checkPlacement's reason codes: the index of the message the game's UI shows for it (cr.tex, text group 77)
PLACE_REASONS = {
    0: "the game refuses the spot without giving a reason",
    2: "workshops must be placed against the castle wall",
    3: "needs to be placed adjacent to the stockpile",
    4: "needs to be placed adjacent to the armory",
    5: "iron mine must be built on iron ore",
    7: "needs to be placed adjacent to the granary",
    8: "needs to be placed adjacent to the barracks",
    9: "this area is too close to the enemy to build on",
    13: "farms must be placed on the valley floor",
    14: "this land is inaccessible",
    15: "too far from your castle to build",
    16: "you must build adjacent to your castle walls",
    17: "too close to enemy units or buildings to build",
    18: "too far from your castle to build",
    19: "must be placed next to an existing wall",
    21: "too close to a signpost to build",
    22: "farms must be placed on an oasis",
    23: "this land is not fertile enough",
}


HIDDEN = -1  # game_refuses(..., menu=True): the map's build menu does not offer the building (isMapperAvailable == 0)
PLACE_REASONS[HIDDEN] = "this mission's build menu does not offer it"
# Per-map troop availability (MapPropertiesState 0x01653858, OpenSHC): barracks troops archer..knight (shorts, index
# type - 22) at +0x582, mercenaries (index type - 70, OpenSHC order; INFERRED, no map hides one yet) at +0x590.
# The recruit
# executors never read them (G1 S2); the barracks and mercenary post panels do.
TROOP_FLAGS, MERC_FLAGS = 0x01653858 + 0x582, 0x01653858 + 0x590


def troop_offered(unit, pid):
    t = UNIT_TYPE[unit]
    addr = TROOP_FLAGS + 2 * (t - 22) if 22 <= t <= 28 else MERC_FLAGS + 2 * (t - 70) if 70 <= t <= 76 else None
    return addr is None or i32(pid, addr) & 0xFFFF != 0


def place_reason(code):
    return PLACE_REASONS.get(code, f"game reason code {code}")


def game_refuses(name, x, y, pid=None, menu=False):
    """The game's own placement check, the one placeBuilding runs before it places anything (crusader-bridge probe
    0x7F000002, on the next frame; nothing is queued): None if the game would place `name` at (x, y) now, else the
    game's reason code (PLACE_REASONS). With menu=True, HIDDEN first when the map's build menu does not offer `name`
    (the game's isMapperAvailable, which only the UI checks)."""
    pid = _require_game_pid(pid)
    if pid not in _PLACE_SLOT:
        _PLACE_SLOT[pid] = int(re.findall(r"placement check at 0x([0-9A-F]+)", _ucp_log(pid))[-1], 16)
    kind, size = footprint(name)
    queue_command(0x7F000002, x, y, kind, size, pid=pid)
    slot = _PLACE_SLOT[pid]
    if menu and i32(pid, slot + 8) == 0:
        return HIDDEN
    return i32(pid, slot + 4) if i32(pid, slot) else None


def save_game(name, pid=None):
    """Save the match as <SAVES_DIR>/<name>.sav with the game's own SAVE command, as its save dialog does
    (crusader-bridge fills in the tick and unit hash). Like every command it runs when time next moves."""
    pid = _require_game_pid(pid)
    raw = name.encode("ascii") + b"\0"
    if len(raw) > 0xFA or "/" in name:
        raise RealGameError("save name must be at most 249 ASCII bytes and contain no slash")
    with pid.memory.file() as mem:
        mem.seek(SAVE_NAME)
        mem.write(raw)
    queue_command(SAVE, 0, 0, 0, pid=pid)


def _unit_records(pid):
    n = i32(pid, UNITS_STATE)
    records_per_read = MAX_READ // UNIT_SIZE
    with pid.memory.file() as mem:
        for start in range(1, n, records_per_read):
            count = min(records_per_read, n - start)
            mem.seek(UNITS + start * UNIT_SIZE)
            blob = mem.read(count * UNIT_SIZE)
            for offset in range(count):
                yield start + offset, blob, offset * UNIT_SIZE


def units(pid):
    """Every live unit (logical state 2): {id, type (game type id), owner, uid, x, y, hp}."""
    out = []
    for i, blob, b in _unit_records(pid):
        state, kind = struct.unpack_from("<hh", blob, b + U_STATE)
        if state == 2:
            (owner,) = struct.unpack_from("<h", blob, b + U_OWNER)
            (uid,) = struct.unpack_from("<i", blob, b + U_UID)
            x, y = struct.unpack_from("<hh", blob, b + U_X)
            (hp,) = struct.unpack_from("<i", blob, b + U_HP)
            out.append({"id": i, "type": kind, "owner": owner, "uid": uid, "x": x, "y": y, "hp": hp})
    return out


def idle_peasants(pid, player=1):
    """Peasants the game would turn into a recruit (UnitsState::euroRecruit's search, asm 0x52EAA7..0x52EAF3):
    type 1 of the
    player, alive (+0x8C == 2), +0x2A0 == 0, state +0x2C0 not 4, 5, 0x6A or 0x6D, and when the state is 0, +0x372 == 0.
    Peasants still walking in from the map edge do not qualify."""
    count = 0
    for _, blob, b in _unit_records(pid):
        state, kind = struct.unpack_from("<hh", blob, b + U_STATE)
        if kind != PEASANT or state != 2 or struct.unpack_from("<h", blob, b + U_OWNER)[0] != player:
            continue
        (busy,) = struct.unpack_from("<h", blob, b + 0x2A0)
        (task,) = struct.unpack_from("<H", blob, b + 0x2C0)
        if (
            busy == 0
            and task not in (4, 5, 0x6A, 0x6D)
            and (task != 0 or struct.unpack_from("<h", blob, b + 0x372)[0] == 0)
        ):
            count += 1
    return count


# The game's own skirmish score (ComputeSkMasterScore 0x004D5780, shown on its end screen): per player, gold earned (tax
# and market sales, 0x01A27060), points for enemy buildings destroyed (0x01A27360, x100; 1..20 per building type, table
# 0x5BBAC8), the troop value of enemy units killed (0x01A2733C), a byte counting lord kills (0x01A272E9: +1/4 each), and
# the months from the start date (0x01A27438 year, 0x01A2743C month) to the current one (0x01A27440, 0x01A27444).


def lord_alive(pid, uid, live=None, player=1):
    """The lord whose uid is `uid` is still a live unit with hp left (the game's own check compares
    units[lordID].uid with lordUID; Castle Builder respawns a dead lord as a new unit with a new uid)."""
    lid = i32(pid, LORD_ID + STRIDE * (player - 1))
    if lid <= 0 or i32(pid, LORD_UID + STRIDE * (player - 1)) != uid:
        return False
    u = next((u for u in (live if live is not None else units(pid)) if u["id"] == lid), None)
    return u is not None and u["uid"] == uid and u["hp"] > 0


def select(unit_ids, pid=None):
    """GCT_ESCAPE (15) deselects the player's units, then GCT_UNITS_SELECT (16) makes a tribe of exactly
    unit_ids; crusader-bridge takes the tribe id the way the UI does and leaves it in its tribe slot."""
    pid = _require_game_pid(pid)
    queue_command(15, pid=pid)  # without it, units selected earlier would join the new tribe
    bits = bytearray(400)
    for i in unit_ids:
        bits[i >> 3] |= 1 << (i & 7)
    with pid.memory.file() as mem:
        mem.seek(SELECTION)
        mem.write(bytes(bits))
    queue_command(16, 0, pid=pid)
    return i32(pid, int(re.findall(r"selected tribe at 0x([0-9A-F]+)", _ucp_log(pid))[-1], 16))


def demolish(building_id, uid, pid=None):
    """GCT_DESTROY_BUILDING: the game checks only that uid matches the building; ownership is ours to check."""
    queue_command(DESTROY_BUILDING, building_id, DEMOLISH_REFUND, uid, pid=pid)


def set_tax(level, pid=None):
    queue_command(CHANGE_TAXES, level, pid=pid)


def set_rations(level, pid=None):
    queue_command(CHANGE_RATIONS, level, pid=pid)


def advance(ticks, pid=None, timeout=600):
    """Run exactly `ticks` game ticks. The game must be in a match and paused by the hook. Only the target is written:
    crusader-bridge's tick decision unpauses and pauses the game itself, once per frame (a pause flag cleared
    from here at
    an arbitrary moment could split a frame). Done when the target is reached (or the game ended a skirmish) and the
    game is paused again; the tick is read before the flag, which is still clear right after the last tick runs."""
    pid = _require_game_pid(pid)
    start = i32(pid, TICK)
    write_i32(pid, target_address(pid), start + ticks)
    wait_for(
        lambda: (
            ((i32(pid, TICK) >= start + ticks or i32(pid, GAME_OVER)) and i32(pid, PAUSED) == 1)
            or i32(pid, MENU) != MENU_IN_GAME
        ),
        timeout,  # a campaign mission the game ended leaves the match
        f"tick {start + ticks}",
        every=0.001,
    )  # ~1 ms of ticks
    return i32(pid, TICK)


def read_state(pid=None):
    pid = _require_game_pid(pid)
    with pid.memory.file() as mem:

        def rd(addr):
            mem.seek(addr)
            return int.from_bytes(mem.read(4), "little", signed=True)

        return {
            "tick": rd(TICK),
            "paused": bool(rd(PAUSED)),
            "month": rd(MONTH),
            "year": rd(YEAR),
            "tax": rd(TAXES),
            "rations": rd(RATIONS),
            "popularity": rd(POPULARITY_X100) / 100,
            "population": rd(POPULATION),
            "housing": rd(HOUSING),
            "stock": {g: rd(STOCK + 4 * i) for g, i in GOODS.items()},
        }


# ---- bridge backend: same interface as sim.Game, so server.py, the SDK and MCP work unchanged

COSTS = 0x00F98520 + 0x18C7D4  # BuildingsState.buildingCosts: (wood, stone, iron, pitch, gold) per BuildingType
BT_OF = {name: bt for bt, name in {**BT_NAMES, **G2_BT, **G4_BT, **G5_BT}.items()}
BT_OF.update({"gatehouse_turned": 46, "large_gatehouse_turned": 45})
BT_OF.update({n: 66 for n in ("small_garden", "medium_garden", "large_garden")})
RATION_NAMES = ["none", "half", "normal", "extra", "double"]


@dataclass(frozen=True)
class Skirmish:
    map_name: str = "Inches Apart"
    ai: str = "rat"
    seed: int = 1


@dataclass(frozen=True)
class CastleBuilder:
    seed: int = 1


@dataclass(frozen=True)
class LoadSave:
    name: str


def _layout_sanity(memory):
    menu = memory.read_i32(MENU)
    paused = memory.read_i32(PAUSED)
    return 0 <= menu <= 100 and paused in (0, 1)


class _GamePid(str):
    memory: ProcessMemory
    hooks: dict[str, int]

    def __new__(cls, pid, memory):
        obj = super().__new__(cls, pid)
        obj.memory = memory
        obj.hooks = {}
        return obj


def _require_game_pid(pid) -> _GamePid:
    if not isinstance(pid, _GamePid):
        raise RealGameError("a verified Game process is required")
    return pid


class Game:
    """A paused game controlled through the bridge."""

    pid: _GamePid

    def __init__(self, match, *, game_dir=None, process_lookup=None, tick_budget=None):
        self.memory: ProcessMemory | None = None
        self._game_pid: _GamePid | None = None
        try:
            self._initialize(match, game_dir=game_dir, process_lookup=process_lookup, tick_budget=tick_budget)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.memory is not None:
            self.memory.close()

    def _initialize(self, match, *, game_dir=None, process_lookup=None, tick_budget=None):
        self.game_dir = os.fspath(game_dir) if game_dir is not None else "/opt/crusader"
        if not os.path.isabs(self.game_dir):
            raise RealGameError("game_dir must be an absolute path inside the game process")

        def lookup():
            pid = game_pid(process_lookup) if process_lookup is not None else game_pid()
            if self.memory is None:
                executable = f"/proc/{pid}/root/{self.game_dir.lstrip('/')}/Stronghold Crusader.exe"
                self.memory = ProcessMemory(int(pid), executable, sanity=_layout_sanity)
                self._game_pid = _GamePid(pid, self.memory)
                _GAME_DIRS[self._game_pid] = self.game_dir
            elif pid != self._game_pid:
                raise RealGameError("game process changed during startup")
            assert self._game_pid is not None
            return self._game_pid

        configured_lookup = lookup
        if tick_budget is not None and (type(tick_budget) is not int or tick_budget <= 0):
            raise RealGameError("tick_budget must be a positive integer")
        if isinstance(match, (Skirmish, CastleBuilder)):
            if type(match.seed) is not int or not 0 < match.seed < 2**31:
                raise RealGameError("seed must be in 1..2^31-1")
            if isinstance(match, Skirmish):
                self.pid = _require_game_pid(start_skirmish(match.map_name, match.ai, process_lookup=configured_lookup))
            else:
                self.pid = _require_game_pid(start_match(process_lookup=configured_lookup))
            write_i32(self.pid, seed_slot_address(self.pid), match.seed)
        elif isinstance(match, LoadSave):
            self.pid = _require_game_pid(load_save(match.name, process_lookup=configured_lookup))
        else:
            raise RealGameError("match must be Skirmish, CastleBuilder, or LoadSave")
        self.budget = tick_budget
        self._events, self.game_over = [], None
        self.start_tick = i32(self.pid, TICK)
        self.gold = self._stock()["gold"]
        self._months_done = 0
        self._pending, self._pending_demolish, self._pending_walls = [], [], []
        self._reserved = {}
        self.lord_uid = i32(self.pid, LORD_UID)
        self.lord_died = False
        self.check_every = TICKS_PER_MONTH
        self.skirmish = isinstance(match, Skirmish)
        self.mission = None
        self.vs_ai = self.skirmish
        self.allies = set()
        self.menu = True
        self.level = 7
        self.bt_names = {**BT_NAMES, **G2_BT, **G4_BT, **G5_BT}
        self.wall_kinds = G5_WALL_KINDS
        self.building_names = sorted(b for b in BUILDINGS if b != "keep")
        self.decorations = {**DECORATIONS, "brazier": BRAZIER}
        self.engine_names = {**ENGINE_NAMES, **MOUNTED_ENGINES}
        self.unit_names = {**UNIT_NAMES, **self.engine_names}
        lords = {
            p: i32(self.pid, LORD_UID + STRIDE * (p - 1))
            for p in range(2, 9)
            if self.vs_ai
            and i32(self.pid, LORD_ID + STRIDE * (p - 1)) > 0
            and lord_alive(self.pid, i32(self.pid, LORD_UID + STRIDE * (p - 1)), player=p)
        }
        self.enemy_lords = lords
        self.ally_lords = {}
        self._orders = []
        self.enemy_lords_died = set()
        self.match_over = False

    @property
    def tick(self):
        return i32(self.pid, TICK) - self.start_tick

    def _stock(self):
        return read_state(self.pid)["stock"]

    def _check(self, cond, msg):
        if self.game_over:
            raise RealGameError(f"game over: {self.game_over}")
        if not cond:
            raise RealGameError(msg)

    def _check_budget(self):
        """Commands are refused once the tick budget is spent (they could only run in unscored time)."""
        self._check(self.budget is None or self.tick < self.budget, "tick budget exhausted")

    def _emit(self, kind, **data):
        self._events.append({"type": kind, "tick": self.tick, **data})

    # commands
    def build(self, building, x, y):
        self._check_budget()
        if building in self.decorations:
            return self._decorate(building, x, y)
        if self.level >= 5 and building in MOUNTS:
            return self._mount(building, x, y)
        self._check(building in self.building_names, f"unknown building {building!r}; one of {self.building_names}")
        self._check(type(x) is int and type(y) is int, "x and y must be integers")
        err = Terrain(self.pid).site_error(building, x, y, self._taken())
        self._check(err is None, f"cannot place {building} at ({x},{y}): {err}")
        reason = game_refuses(building, x, y, self.pid, menu=self.menu)
        self._check(reason != HIDDEN, f"cannot build {building}: this mission's build menu does not offer it")
        self._check(
            reason is None, f"cannot place {building} at ({x},{y}): the game refuses it ({place_reason(reason)})"
        )
        with self.pid.memory.file() as mem:
            mem.seek(COSTS + BT_OF[building] * 20)
            wood, stone, iron, pitch, gold = struct.unpack("<5i", mem.read(20))
        stock = self._stock()
        if self.level >= 5:  # the oil smelter takes iron and a pitch ditch pitch (the cost table's other columns)
            self._check(
                stock["iron"] >= iron and stock["pitch"] >= pitch,
                f"{building} needs {iron} iron and {pitch} pitch; have {stock['iron']}, {stock['pitch']}",
            )
        self._check(
            stock["wood"] >= wood and stock["stone"] >= stone and stock["gold"] >= gold,
            f"{building} needs {wood} wood, {stone} stone, {gold} gold; "
            f"have {stock['wood']}, {stock['stone']}, {stock['gold']}",
        )
        mapper = BUILDINGS[building][0]
        p4 = GATEHOUSE_P4[mapper] if self.level >= 5 and mapper in GATEHOUSE_P4 else 15
        if self.level >= 5 and building == "drawbridge":
            game_call(DRAWBRIDGE_SIDE, TMS, x, y, pid=self.pid)
            self._check(
                i32(self.pid, DB_REFUSED) == 0,
                f"a drawbridge goes in front of the gate of one of your gatehouses; ({x},{y}) is not such a spot",
            )
            p4 = i32(self.pid, DB_SIDE)
        build(building, x, y, self.pid, p4)
        self._pending.append((building, x, y))
        return {"queued": building, "x": x, "y": y, "note": "placed when game time next moves"}

    def demolish(self, building_id):
        self._check_budget()
        self._check(type(building_id) is int, "building_id must be an integer")
        own = {b["id"]: b for b in buildings(self.pid, Terrain(self.pid), self.bt_names) if b["owner"] == 1}
        b = own.get(building_id)
        self._check(b is not None, f"no building of yours has id {building_id}; see state()['buildings']")
        assert b is not None
        self._check(b["type"] != "keep", "the keep cannot be demolished")
        demolish(building_id, b["uid"], self.pid)
        self._pending_demolish.append((building_id, b["uid"], b["type"]))
        return {
            "queued": "demolish",
            "building_id": building_id,
            "type": b["type"],
            "note": "removed when game time next moves; part of its cost is refunded",
        }

    def set_tax(self, level):
        self._check_budget()
        self._check(type(level) is int and -3 <= level <= 8, "tax level must be in -3..8")
        set_tax(level + 3, self.pid)
        return {"tax": level}

    # flags and heads, and the building and granary panels' buttons
    def _decorate(self, name, x, y, queue=True):
        """A flag or heads-on-spikes icon, then a click on top of one of your walls or towers: GCT 69 with the spot's
        height, which the UI takes from TileMapState 0x4FFBA0 (negative: not a spot the UI accepts)."""
        self._check(type(x) is int and type(y) is int, "x and y must be integers")
        t = Terrain(self.pid)
        i = t.tile(x, y)
        self._check(i is not None, f"({x},{y}) is off the map")
        assert i is not None
        if (
            name == "brazier"
        ):  # its own check (0x4457EC): BRAZIER_SPOT > 0 on your wall or tower top, height from BRAZIER_HEIGHT
            ok = game_call(BRAZIER_SPOT, TMS, i, 1, pid=self.pid) > 0
            height = game_call(BRAZIER_HEIGHT, TMS, i, pid=self.pid) if ok else -1
        else:
            height = game_call(TOP_HEIGHT, TMS, i, 1, pid=self.pid)
        with self.pid.memory.file() as mem:
            mem.seek(TMS + 0x301C80 + 2 * i)
            blocked = struct.unpack("<h", mem.read(2))[0] & 0x1000
        self._check(
            height >= 0 and not blocked,
            f"cannot put {name} at ({x},{y}): it goes on top of one of your walls or towers",
        )
        p5 = i32(self.pid, DECO_VARIANT) if name == "heads" else 0 if name == "brazier" else 1
        tup = (DECORATE, 1, x * 8, y * 8, height, self.decorations[name], p5)
        if not queue:
            return tup
        queue_command(*tup, pid=self.pid)
        return {"queued": name, "x": x, "y": y, "note": "put up when game time next moves"}

    def _own_building(self, building_id, kinds=None, what="building"):
        self._check(type(building_id) is int, "building_id must be an integer")
        b = next(
            (
                b
                for b in buildings(self.pid, Terrain(self.pid), self.bt_names)
                if b["id"] == building_id and b["owner"] == 1
            ),
            None,
        )
        self._check(b is not None, f"no building of yours has id {building_id}; see state()['buildings']")
        assert b is not None
        self._check(kinds is None or b["type"] in kinds, f"building {building_id} is a {b['type']}, not a {what}")
        return b

    def repair(self, building_id):
        """The repair button of one of your damaged buildings (0x466160): the game's own price for the damage
        (0x410320, wood and stone), refused while an enemy is near it (0x4A15B0: 15 tiles in a match against computer
        lords, 30 otherwise) or when you lack the wood or stone. GCT 68 (id, wood, stone, uid)."""
        self._check_budget()
        b = self._own_building(building_id)
        self._check(b["type"] in REPAIRABLE, f"a {b['type']} has no repair button; towers and gatehouses do")
        damaged = game_call(REPAIR_COST, 0x00F98520, building_id, pid=self.pid) != 0
        self._check(damaged and b["hp"] < b["max_hp"], f"{b['type']} {building_id} is not damaged")
        with self.pid.memory.file() as mem:
            mem.seek(BUILDINGS_BASE + building_id * BUILDING_SIZE + 0xEE)
            bx, by = struct.unpack("<hh", mem.read(4))
        radius = 30 if i32(self.pid, AI_MATCH) == 0 else 15
        self._check(
            game_call(ENEMY_NEAR, 0x012BB8C8, 1, bx, by, radius, pid=self.pid) == 0,
            f"cannot repair while the enemy is near (within {radius} tiles)",
        )
        wood, stone = i32(self.pid, REPAIR_WOOD), i32(self.pid, REPAIR_STONE)
        stock = self._stock()
        self._check(stock["wood"] >= wood, f"repairing needs {wood} wood; you have {stock['wood']}")
        self._check(stock["stone"] >= stone, f"repairing needs {stone} stone; you have {stock['stone']}")
        queue_command(REPAIR, building_id, wood, stone, b["uid"], pid=self.pid)
        return {
            "queued": "repair",
            "building_id": building_id,
            "wood": wood,
            "stone": stone,
            "note": "repaired to full hp when game time next moves",
        }

    def set_building_active(self, building_id, active):
        """The sleep button of one of your buildings (0x4660B0): GCT 43 with its BuildingType. The game puts
        EVERY building
        of yours of that type to sleep, or wakes them all (a flag per type, 0x4660F0); sleeping buildings stop
        working."""
        self._check_budget()
        b = self._own_building(building_id)
        self._check(type(active) is bool, "active must be true or false")
        bt = BT_OF.get(b["type"], 0) if b["type"] != "keep" else 99
        self._check(bt in SLEEPABLE, f"a {b['type']} cannot be put to sleep (its panel has no sleep button)")
        with self.pid.memory.file() as mem:
            mem.seek(ASLEEP + bt)
            asleep = mem.read(1)[0] != 0
        if asleep == active:  # the button toggles; only press it when the state differs
            queue_command(SLEEP, bt, pid=self.pid)
        return {
            "queued": "set_building_active",
            "type": b["type"],
            "active": active,
            "note": f"every {b['type']} of yours {'works' if active else 'sleeps'} from when game time next moves",
        }

    def set_workshop_product(self, building_id, weapon):
        """A workshop panel's weapon button (0x465200): GCT 33 (id, weapon good, uid); then the UI notes the
        choice in your
        player record (+0x10). Only the two weapons of that workshop, and only those this map's panel offers."""
        self._check_budget()
        b = self._own_building(
            building_id, {"fletcher", "poleturner", "blacksmith"}, "fletcher, poleturner or blacksmith"
        )
        pair = WORKSHOP_PRODUCTS[BT_OF[b["type"]]]
        self._check(weapon in pair, f"a {b['type']} makes {pair[0]} or {pair[1]}")
        good = GOODS[weapon]
        self._check(i32(self.pid, WEAPON_UI[good]) != 0, f"this map does not let you make {weapon}")
        queue_command(PRODUCT, building_id, good, b["uid"], pid=self.pid)
        ui_write(LAST_WEAPON, good, pid=self.pid)
        return {
            "queued": "set_workshop_product",
            "building_id": building_id,
            "weapon": weapon,
            "note": "it makes this from its next piece of work",
        }

    def set_food_allowed(self, food, allowed):
        """A granary panel's food toggle (0x43FBB0): the UI flips your "do not eat" flag for that food itself, with no
        command; the bridge makes the same write inside a frame."""
        self._check_budget()
        self._check(food in FOOD_SLOT, f"food must be one of {sorted(FOOD_SLOT)}")
        self._check(type(allowed) is bool, "allowed must be true or false")
        self._check(i32(self.pid, AI_MATCH) in (0, 99), "the granary's food toggles are not available here")
        self._check(
            any(b["owner"] == 1 and b["type"] == "granary" for b in buildings(self.pid, Terrain(self.pid))),
            "you need a granary: its panel has the food toggles",
        )
        addr = FOOD_BANNED + 2 * FOOD_SLOT[food]
        with self.pid.memory.file() as mem:
            mem.seek(addr)
            banned = struct.unpack("<h", mem.read(2))[0] != 0
        if banned == allowed:
            ui_write(addr, 0 if allowed else 1, size=2, pid=self.pid)
        return {"food": food, "allowed": allowed}

    # castle defences
    def set_gate(self, building_id, open):
        """A gatehouse's or drawbridge's panel button (0x465480): GCT 45 (id, state, uid), then the UI notes
        the state in
        your player record. Open lets units through; closed (raised, for a drawbridge) stops everyone, yours too."""
        self._check_budget()
        b = self._own_building(building_id, GATES, "gatehouse or drawbridge")
        self._check(type(open) is bool, "open must be true or false")
        state = GATE_OPEN if open else GATE_CLOSED
        queue_command(SET_GATE, building_id, state, b["uid"], pid=self.pid)
        ui_write(LAST_GATE, state, pid=self.pid)
        return {"queued": "set_gate", "building_id": building_id, "open": open, "note": "when game time next moves"}

    # the Allies panel. Every button is GCT 113 (kind, ...),
    # executed by
    # 0x486140; the checks below are the ones the panel's own handlers (0x4B1410, 0x4B14C0) make before queuing.
    def _ally(self, ally):
        self._check(ally in self.allies, f"player {ally} is not your ally; allies: {sorted(self.allies)}")
        self._check(
            any(lord["owner"] == ally and lord["alive"] for lord in self._lords(self.ally_lords, units(self.pid))),
            f"your ally (player {ally}) has no lord left",
        )

    def _goods_amount(self, good, qty):
        self._check(good in GOODS, f"unknown good {good!r}; one of {sorted(GOODS)}")
        # the panel's amount buttons add 5, 10, 25, 100 or 500: every multiple of 5 and nothing else
        self._check(
            type(qty) is int and 0 < qty <= 2147483645 and qty % 5 == 0,
            "qty must be a positive multiple of 5 no greater than 2147483645",
        )
        return GOODS[good]

    def ally_order(self, ally, order, target=None):
        """Set Orders (0x4B1410): attack an enemy lord (his portrait), defend my castle (11) or cancel orders
        (10). The ally
        answers when time next moves (0x4AD2F0: an AI agrees only when its army is strong enough); state()["allies"]
        shows his order if he agreed."""
        self._check_budget()
        self._ally(ally)
        self._check(order in ("attack", "defend", "cancel"), "order must be 'attack', 'defend' or 'cancel'")
        if order == "attack":
            alive = [lord["owner"] for lord in self._lords(self.enemy_lords, units(self.pid)) if lord["alive"]]
            self._check(target in alive, f"target must be an enemy player with a lord; one of {sorted(alive)}")
            button, target = sorted(alive).index(target) + 1, target  # the Set Orders portraits, one per enemy lord
        else:
            self._check(target is None, "only an attack order takes a target")
            button, target = (11 if order == "defend" else 10), 0
        queue_command(ALLY_REQUEST, ALLY_ORDER, target, ally, 1, button, pid=self.pid)
        return {
            "queued": "ally_order",
            "ally": ally,
            "order": order,
            **({"target": target} if order == "attack" else {}),
            "note": "your ally answers when game time next moves; state()['allies'] shows his order if he agreed",
        }

    def _room(self, player, gid):
        return game_call(STORE_ROOM, STORE_ROOM_THIS, player, gid, pid=self.pid)

    def _send(self, ally, gid, qty, what):
        if gid == GOODS["gold"]:
            self._check(self._stock()["gold"] >= qty, f"you have {self._stock()['gold']} gold, not {qty}")
        else:
            have = self._stock()[what]  # 0x115C2C8 + (me*0xE7D + good)*4, as the panel reads it
            self._check(have >= qty, f"you have {have} {what}, not {qty}")
            room = self._room(ally, gid)
            self._check(room >= 0, f"your ally has no store for {what}")
            self._check(room > 0, f"your ally has no room for {what}")
            qty = min(qty, room)  # the panel sends only what fits (0x4B1870)
        queue_command(ALLY_REQUEST, ALLY_SEND, ally, gid, qty, 1, pid=self.pid)
        return qty

    def ally_send_goods(self, ally, good, qty):
        """Send Goods (0x4B14C0, thumbs up): goods leave your stock and enter your ally's when time next moves,
        as much as
        his stores can take."""
        self._check_budget()
        self._ally(ally)
        gid = self._goods_amount(good, qty)
        sent = self._send(ally, gid, qty, good)
        return {
            "queued": "ally_send_goods",
            "ally": ally,
            "good": good,
            "qty": sent,
            "note": "when game time next moves",
        }

    def ally_request_goods(self, ally, good, qty):
        """Request Goods (0x4B14C0 on the request modal): your stores need room for them, then the ally decides at once
        (0x4D0520: he never gives gold, and keeps a reserve of each good); if he agrees they arrive when time
        next moves."""
        self._check_budget()
        self._ally(ally)
        gid = self._goods_amount(good, qty)
        if gid != GOODS["gold"]:
            room = self._room(1, gid)
            self._check(room >= 0, f"you have no store for {good}")
            self._check(room >= qty, f"you have room for {room} {good}, not {qty}")
        self._check(
            game_call(ALLY_WILLING, AI_PERSONALITIES, ally, gid, qty, pid=self.pid) != 0,
            f"your ally refuses to give {qty} {good}",
        )
        queue_command(ALLY_REQUEST, ALLY_ASK, ally, gid - 1, qty, 1, pid=self.pid)
        return {
            "queued": "ally_request_goods",
            "ally": ally,
            "good": good,
            "qty": qty,
            "note": "when game time next moves",
        }

    def _ally_request(self, ally):
        """The goods this ally asked us for (word pair 0x115F61C/0x115F630, slot us*0x1CFA + ally), or None."""
        at = 2 * (1 * REQ_STRIDE + ally)
        gid, qty = i32(self.pid, REQ_GOOD + at) & 0xFFFF, i32(self.pid, REQ_QTY + at) & 0xFFFF
        name = next((n for n, i in GOODS.items() if i == gid), None)
        return {"good": name, "qty": qty} if gid >= 2 and name else None

    def ally_answer(self, ally, accept):
        """Answer the ally's goods request: accept sends what he asked for (as Send Goods does), refuse tells him no
        (0x4AE010)."""
        self._check_budget()
        self._ally(ally)
        self._check(type(accept) is bool, "accept must be true or false")
        req = self._ally_request(ally)
        self._check(req is not None, f"your ally (player {ally}) has not asked you for anything")
        assert req is not None
        if accept:
            sent = self._send(ally, GOODS[req["good"]], req["qty"], req["good"])
            return {
                "queued": "ally_answer",
                "ally": ally,
                "accept": True,
                "good": req["good"],
                "qty": sent,
                "note": "when game time next moves",
            }
        queue_command(ALLY_REQUEST, ALLY_REFUSE, ally, 0, 0, 1, pid=self.pid)
        return {"queued": "ally_answer", "ally": ally, "accept": False, "note": "when game time next moves"}

    def _allies_panel(self):
        """What the Allies panel shows per ally (0x4ACA98..0x4ACE50): his goods request of you and his current order."""
        out = []
        for p in sorted(self.allies):
            kind, target = i32(self.pid, ALLY_ORDER_KIND + STRIDE * p), i32(self.pid, ALLY_ORDER_TARGET + STRIDE * p)
            order = {"attack": target} if kind == 1 else "defend" if kind == 2 else None
            out.append({"player": p, "request": self._ally_request(p), "order": order})
        return out

    # information panels: each scribe page's draw function recomputes its
    # numbers from raw
    # player state (it does not read the weekly stored factors); these mirror that arithmetic field for field.
    def _rec(self, off, p=1):
        return i32(self.pid, REC0 + STRIDE * p + off)

    def _popularity_page(self):
        r = self._rec
        gated = r(0x2180) != 0  # food, tax and crowding show 0 until the town has started (0x43E6C0)
        food = (-200 if r(0x20A0) == 0 else {0: -200, 1: -100, 2: 0, 3: 100, 4: 200}.get(r(0x218C), 0)) + {
            2: 25,
            3: 50,
            4: 75,
        }.get(r(0x20A8), 0)
        tax = 25 if r(0x14) < 3 and r(0x50C) <= 0 else TAX_POP[min(max(r(0x2188), 0), 11)]
        crowd = r(0x80)
        crowding = 0 if crowd <= 100 else -50 * min((crowd - 81) // 20, 5)
        blessed = r(0x240)
        religion = RELIGION_POP(blessed) + (25 if r(0x28C) else 0) + (50 if r(0x290) else 0)
        ale_pct = game_call(ALE_COVERAGE, GAME_CORE, 1, pid=self.pid)
        ale = 0 if ale_pct < 25 else 50 * min(ale_pct // 25, 4)
        factors = {
            "food": food if gated else 0,
            "tax": tax if gated else 0,
            "crowding": crowding if gated else 0,
            "fear_factor": 25 * r(0x2134),
            "religion": religion,
            "ale_coverage": ale,
        }
        raw = dict(factors)
        for i, off in enumerate((0x2318, 0x231A, 0x2310, 0x2312, 0x2314, 0x2316)):  # optional event lines (shorts)
            v = struct.unpack("<h", struct.pack("<i", r(off))[:2])[0]
            if v:
                raw[f"event_{i}"] = v
        if r(0x2228):
            raw["event_flag"] = 400
        out = {k: _pop_drawn(v) for k, v in raw.items()}
        out["coming_month"] = _pop_drawn(sum(raw.values()))
        return out

    def report(self, page):
        """One scribe page, the numbers it draws (overview book, then a page button). Pages: popularity, fear, religion,
        army, food, population, stores, weapons; and 'merit' (the crown's Order of Merit)."""
        self._check(page in REPORT_PAGES, f"unknown page {page!r}; one of {list(REPORT_PAGES)}")
        r = self._rec
        if page == "popularity":
            return self._popularity_page()
        if page == "fear":
            lvl = r(0x2134)
            return {
                "good_things": r(0x212C),
                "bad_things": r(0x2130),
                "popularity_effect": lvl,
                **({"next_level_in": r(0x2138)} if abs(lvl) < 5 else {}),
                "efficiency_pct": r(0x211C),
            }
        if page == "religion":
            b = r(0x240)
            return {
                "priests": r(0x2298),
                "blessed_pct": b,
                "popularity_effect": RELIGION_POP(b) // 25,
                **({"next_level_at": 25 if b < 25 else 50 if b < 50 else 75 if b < 75 else 100} if b < 95 else {}),
            }
        if page == "food":
            st = self._stock()
            return {f: st[f] for f in ("meat", "cheese", "bread", "apples")}  # 0x43FAC0: stock indexes 12, 11, 10, 13
        if page in ("stores", "weapons"):
            st = self._stock()
            return {k: st[k] for k in (STORE_GOODS if page == "stores" else WEAPON_GOODS)}
        if page == "army":
            mine = [u for u in units(self.pid) if u["owner"] == 1 and u["hp"] > 0]
            counts = {}
            for u in mine:
                name = self.unit_names.get(u["type"])
                if name and name not in ("lord", "peasant") and u["type"] in ARMY_PAGE_TYPES:
                    counts[name] = counts.get(name, 0) + 1
            return {"troops": counts, "fear_bonus": 5 * r(0x2134)}
        if page == "population":  # a graph of the population, one point per month (0x43F6A0)
            n = min(i32(self.pid, POP_MONTHS), 300)
            raw = read_bytes(self.pid, POP_HISTORY + 0x258, 2 * n) if n else b""
            return {"history": list(struct.unpack(f"<{n}h", raw))}
        return self._merit()

    def _game_text(self, group, idx):
        """A string from the game's own text table (0x46A050, thiscall on 0x2157578), as the panels draw it."""
        ptr = game_call(GAME_TEXT, GAME_TEXT_THIS, group, idx, pid=self.pid) & 0xFFFFFFFF
        return read_bytes(self.pid, ptr, 200).split(b"\0")[0].decode("latin-1") if ptr else None

    def building_info(self, building_id):
        """What one of your buildings' panel prints (select it): its numbers and status lines, per panel
        . Other players' buildings have no panel."""
        self._check(type(building_id) is int, "building_id must be an integer")
        b = next((b for b in buildings(self.pid, Terrain(self.pid), self.bt_names) if b["id"] == building_id), None)
        self._check(b is not None and b["owner"] == 1, f"building {building_id} is not one of yours")
        assert b is not None
        kind, r = b["type"], self._rec
        out = {"id": building_id, "type": kind}
        if kind == "hovel":  # 0x43BD60: a fixed text
            out["houses"] = 8
        elif kind == "granary":  # 0x43B3B0: the town's food, not this granary's
            months = r(0x2190)
            out.update(
                food_units=r(0x209C),
                months_supply=None if months < 0 else months,
                food_types_eaten=r(0x20A8),
                rations=RATION_NAMES[r(0x18)] if 0 <= r(0x18) <= 4 else r(0x18),
                # the panel's two popularity faces, the food factor's parts as the scribe's
                # popularity page computes them (_popularity_page), in the panel's units (1 = 25)
                rations_popularity=(
                    -200 if r(0x20A0) == 0 else {0: -200, 1: -100, 2: 0, 3: 100, 4: 200}.get(r(0x218C), 0)
                )
                // 25,
                variety_popularity={2: 25, 3: 50, 4: 75}.get(r(0x20A8), 0) // 25,
            )
        elif kind == "keep":  # 0x43A9F0
            out.update(peasants=r(0x2180), tax=r(0x14) - 3)
        elif kind in HP_BAR_PANELS:  # 0x43E350: "cur/max", gatehouses and towers only
            out.update(hp=b["hp"], max_hp=b["max_hp"])
        worker = self._worker_line(building_id)
        if worker:
            out["worker"] = worker
        if kind in ("fletcher", "blacksmith", "poleturner"):  # 0x439440: two status lines by state shorts
            # ponytail: the product-icon branch (a type-8 worker the game says is busy) is not mirrored
            base = BUILDINGS_BASE - 0x14 + building_id * BUILDING_SIZE  # the record proper starts 0x14 earlier
            for label, off, table in ((3, 0x2A2, WORKSHOP_LINE1), (4, 0x2A4, WORKSHOP_LINE2)):
                st = struct.unpack("<h", read_bytes(self.pid, base + off, 2))[0]
                if st in table:
                    out.setdefault("status", []).append(
                        f"{self._game_text(0x21, label)} {self._game_text(0x21, table[st])}"
                    )
        return out

    def _worker_line(self, building_id):
        """The panel's "Worker:" line (widget 0x4476B0, drawn under every building panel), branch for branch; the
        activity comes from the game's own classifier of the worker (0x537F60 -> text group 0x56). Branches the widget
        dispatches elsewhere (its cases 0..3) are not mirrored and return None."""
        base = BUILDINGS_BASE - 0x14 + building_id * BUILDING_SIZE

        def h(off):
            return struct.unpack("<h", read_bytes(self.pid, base + off, 2))[0]

        bt = h(0xE6)
        if 0x24 <= bt <= 0x26 or 0x28 <= bt <= 0x2C or h(0x1AC) <= 0:
            return None

        def text(grp, i):
            return self._game_text(grp, i)

        if h(0x2D0) == 0:
            return text(0x12, 9)
        if read_bytes(self.pid, base + 0x2C7, 1)[0]:
            return text(0x12, 7)
        if h(0x1B0):
            return text(0x12, 3 if h(0x1AE) == 0 else 4 + h(0x1B0))
        n = h(0x1AE)
        workers = [h(0x1B2 + 2 * i) for i in range(max(n, 0))]
        if n > 0 and any(
            struct.unpack("<h", read_bytes(self.pid, UNITS + u * UNIT_SIZE + 0x8E, 2))[0] == 1 for u in workers
        ):
            return text(0x12, 4)
        case = read_bytes(self.pid, WORKER_CASES + bt - 5, 1)[0] if 0 <= bt - 5 <= 0x1D else 4
        if case != 4 or not workers:
            return None
        ui_write(WORKER_GOOD_SLOT, 0, pid=self.pid)
        code = game_call(WORKER_CLASSIFY, UNITS_STATE, workers[-1], WORKER_GOOD_SLOT, pid=self.pid)
        if code <= 0:
            return text(0x12, 0xA)
        good = i32(self.pid, WORKER_GOOD_SLOT)
        if code in (10, 6, 9) and good > 0:
            act = f"{text(0x56, {10: 0x65, 6: 0x64, 9: 0x67}[code])} {text(2, good)}" + (
                f" {text(0x56, 0x66)}" if code == 10 else ""
            )
        else:
            act = text(0x56, code)
        return f"{text(0x12, 0xA)} {act}"

    def _merit(self):
        """The Order of Merit (0x4AE0F0): per lord still in the game, his treasury (never below 0) and troops."""
        rows = []
        for p in range(1, 9):
            if not read_bytes(self.pid, MERIT_ACTIVE + p, 1)[0]:
                continue
            rows.append({"player": p, "gold": max(0, self._rec(0x50C, p)), "troops": self._rec(0x53C, p)})
        return {"lords": rows}

    def _line(self, x1, y1, x2, y2, most=100):
        self._check(all(type(v) is int for v in (x1, y1, x2, y2)), "x1, y1, x2, y2 must be integers")
        self._check(x1 == x2 or y1 == y2, "a line runs straight: x1 == x2 or y1 == y2")
        n = max(abs(x2 - x1), abs(y2 - y1)) + 1
        self._check(n <= most, f"a line is at most {most} tiles")
        dx, dy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
        t = Terrain(self.pid)
        line = [(x1 + k * dx, y1 + k * dy) for k in range(n)]
        for x, y in line:
            self._check(t.tile(x, y) is not None, f"({x},{y}) is off the map")
        return line

    def dig_moat(self, unit_ids, x, y):
        """Diggers selected, then a click on a tile of your moat plan: GCT 36 instruction 6 (x, y, 1000). They dig the
        plan out tile by tile; a dug tile is moat, which ground units cannot cross."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._check(all(live[i]["type"] in DIGGERS for i in unit_ids), f"only {DIGGER_NAMES} dig moats")
        self._check(type(x) is int and type(y) is int, "x and y must be integers")
        t = Terrain(self.pid)
        i = t.tile(x, y)
        self._check(
            i is not None and t.logic[i] & L_MOAT_PLAN, f"({x},{y}) is not a tile of your moat plan; plan_moat first"
        )
        self._order(unit_ids, I_DIG_MOAT, x, y, DIG_P4)
        self._drop_orders(unit_ids)
        return {"queued": "dig_moat", "units": len(unit_ids), "x": x, "y": y}

    def _mount(self, name, x, y):
        """The military page's mangonel or ballista icon, then a click on one of your square or round towers:
        the UI checks
        the price with the game's own 0x457B80 and queues GCT 42 at the tower's mount spot (its corner + 2)."""
        self._check(type(x) is int and type(y) is int, "x and y must be integers")
        t = Terrain(self.pid)
        i = t.tile(x, y)
        self._check(i is not None, f"({x},{y}) is off the map")
        assert i is not None
        bid = t.building[i]
        b = next((b for b in buildings(self.pid, t) if b["id"] == bid), None) if bid > 0 else None
        with self.pid.memory.file() as mem:
            mem.seek(BUILDINGS_BASE + bid * BUILDING_SIZE + B_TYPE)
            bt = struct.unpack("<h", mem.read(2))[0] if bid > 0 else 0
            mem.seek(BUILDINGS_BASE + bid * BUILDING_SIZE + TOWER_ENGINE)
            has_engine = mem.read(1)[0] if bid > 0 else 0
        self._check(
            b is not None and b["owner"] == 1 and bt in MOUNT_TOWERS and t.logic[i] & L_TOWER_TOP,
            f"a {name} goes on top of one of your square or round towers; ({x},{y}) is not one",
        )
        assert b is not None
        self._check(not has_engine, f"tower {bid} already carries an engine")
        self._check(t.unit[i] == 0, f"a unit stands on ({x},{y}); click a free spot on the tower top")
        mapper, unit = MOUNTS[name]
        self._check(game_call(CAN_PAY, 0x0112B0B8, mapper, 1, 0, pid=self.pid) != 0, f"you cannot pay for a {name}")
        mx, my = b["x"] + 2, b["y"] + 2
        mount_tile = t.tile(mx, my)
        self._check(mount_tile is not None, "tower mount spot is off the map")
        assert mount_tile is not None
        queue_command(MOUNT, mx * 8 + 4, my * 8 + 4, t.height[mount_tile], unit, pid=self.pid)
        return {"queued": name, "tower_id": bid, "note": "put up when game time next moves; engineers man it (man())"}

    def oil_duty(self, engineer_ids, smelter_id):
        """Engineers selected, then a click on your oil smelter: instruction 15 (id, uid). They work it and
        carry its oil
        pots to where you send them (pour_oil)."""
        self._check_budget()
        live = self._own_army(engineer_ids)
        self._check(
            all(live[i]["type"] == UNIT_TYPE["engineer"] for i in engineer_ids), "only engineers work an oil smelter"
        )
        b = self._own_building(smelter_id, {"oil_smelter"}, "oil smelter")
        self._order(engineer_ids, I_OIL_DUTY, smelter_id, b["uid"])
        self._drop_orders(engineer_ids)
        return {"queued": "oil_duty", "units": len(engineer_ids), "smelter_id": smelter_id}

    def pour_oil(self, engineer_ids, x, y):
        """Engineers carrying oil selected, then a click on the ground: instruction 20 (x, y). They walk there and pour
        the boiling oil in front of them."""
        self._check_budget()
        live = self._own_army(engineer_ids)
        self._check(all(live[i]["type"] == UNIT_TYPE["engineer"] for i in engineer_ids), "only engineers pour oil")
        # The UI's pour cursor (click action 11, 0x535680): only engineers selected and at least one of them
        # carrying a pot
        self._check(
            any(self._carries_oil(i) for i in engineer_ids),
            "an engineer pours oil only while he carries a pot; oil_duty first",
        )
        # the UI pours by a click on an ENEMY UNIT in the carrier's reach (cursor 11 is in the attack-unit branch,
        # 0x4357FD), through 0x537160 and then an aiming mode (20); that click was not recorded live, and instruction 20
        # (x, y) on a carrier leaves him waiting with his pot (the order is never taken up), so the SDK refuses rather
        # than queue an order that does nothing
        self._check(
            POUR_KNOWN, "pouring oil is not available yet (the game's pour click is not reproduced); see the docs"
        )
        self._check(
            type(x) is int and type(y) is int and Terrain(self.pid).tile(x, y) is not None, f"({x},{y}) is off the map"
        )
        self._order(engineer_ids, I_POUR_OIL, x, y)
        self._drop_orders(engineer_ids)
        return {"queued": "pour_oil", "units": len(engineer_ids), "x": x, "y": y}

    def _carries_oil(self, unit_id):
        # unit +0x388 (short) is the engineer's oil pot; the smelter's worker fills it for an engineer
        # waiting on oil
        # duty (state 9) at the end of its pour animation (0x4161F0), one pot per oil, and the pour clears it
        # (0x565BE7).
        # The pour cursor (0x535680) and the order (0x52892F) also need +0x2A0 == 0 (+0x388 is a union field:
        # the smelter's
        # worker carrying pitch reads 1 there too)
        return self._unit_short(unit_id, U_OIL_POT) != 0 and self._unit_short(unit_id, U_JOB) == 0

    def _fire_spots(self):
        """The game's pitch-ditch list: {index: (owner, x, y, serial)}."""
        n = min(i32(self.pid, PITCH_COUNT), 4000)
        with self.pid.memory.file() as mem:
            mem.seek(FIRE_SPOTS)
            blob = mem.read(FIRE_SPOT_SIZE * n)
        out = {}
        for k in range(1, n):
            v, owner, x, y = struct.unpack_from("<ihhh", blob, k * FIRE_SPOT_SIZE)
            if owner:
                out[k] = (owner, x, y, v)
        return out

    def _team(self, player):
        return i32(self.pid, TEAM + 4 * player)

    def light_pitch(self, unit_ids, x, y):
        """Archers selected, their lead (the first id) beside a lit brazier, then a click on a pitch-ditch tile of yours
        within the UI's reach: instruction 34. They shoot burning arrows into the ditch, which burns."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._check(all(live[i]["type"] in LIGHTERS for i in unit_ids), "only archers and Arabian archers light pitch")
        self._check(type(x) is int and type(y) is int, "x and y must be integers")
        spot = next(
            (
                (k, v)
                for k, (owner, bx, by, v) in self._fire_spots().items()
                if (bx, by) == (x, y) and self._team(owner) == self._team(1)
            ),
            None,
        )
        self._check(spot is not None, f"there is no pitch ditch of yours at ({x},{y})")
        assert spot is not None
        lead = live[unit_ids[0]]
        h = self._unit_short(unit_ids[0], U_HEIGHT_A) + self._unit_short(unit_ids[0], U_HEIGHT_B)
        self._check(
            game_call(BRAZIER_NEAR, ENTITIES, lead["x"], lead["y"], h, pid=self.pid) != 0,
            "no brazier of yours is lit beside your archers (their first unit must stand within 3 tiles of one)",
        )
        reach2 = i32(self.pid, LIGHT_RANGE2)
        self._check(
            (lead["x"] - x) ** 2 + (lead["y"] - y) ** 2 <= reach2,
            f"the pitch at ({x},{y}) is too far from your archers",
        )
        self._order(unit_ids, I_LIGHT, *spot)
        self._drop_orders(unit_ids)
        return {"queued": "light_pitch", "units": len(unit_ids), "x": x, "y": y}

    def delete_wall(self, x, y):
        """The Delete tool on one of your wall tiles: GCT 41 (tile index, 50) (refund percent, halved by the game for
        a low wall; executor 0x4826C0). The tool does nothing on moat plans or pitch (un-plan with
        plan_moat(dig=False))."""
        self._check_budget()
        self._check(type(x) is int and type(y) is int, "x and y must be integers")
        t = Terrain(self.pid)
        i = t.tile(x, y)
        self._check(
            i is not None and t.logic[i] & L_WALL and self._wall_owner(i) == 1,
            f"({x},{y}) is not one of your wall tiles",
        )
        queue_command(DELETE_WALL, i, DEMOLISH_REFUND, pid=self.pid)
        return {
            "queued": "delete_wall",
            "x": x,
            "y": y,
            "note": "removed when game time next moves; half its stone is refunded",
        }

    def fill_moat(self, unit_ids, x, y):
        """Diggers selected, then a click on a moat tile the UI offers to fill (an enemy's): instruction 7 (x, y, 1000).
        They carry earth into it until it is land again."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._check(all(live[i]["type"] in DIGGERS for i in unit_ids), f"only {DIGGER_NAMES} fill moats")
        self._check(type(x) is int and type(y) is int, "x and y must be integers")
        t = Terrain(self.pid)
        i = t.tile(x, y)
        # the moat list keeps our own dug tiles too (so FILLABLE answers there); units fill only another team's dug
        # entries (0x5111D0 mode 2), and the UI showed no fill cursor over our own
        e = self._moat_entry(i) if i is not None and t.logic[i] & L_MOAT else None
        self._check(
            e is not None and e[1] == 2 and self._team(e[0]) != self._team(1),
            f"({x},{y}) is not a moat you can fill (only an enemy's dug moat)",
        )
        self._order(unit_ids, I_FILL_MOAT, x, y, DIG_P4)
        self._drop_orders(unit_ids)
        return {"queued": "fill_moat", "units": len(unit_ids), "x": x, "y": y}

    def _moat_entry(self, tile):
        """(owner, kind) of the moat list's active entry for this tile, or None."""
        n = min(i32(self.pid, MOAT_COUNT), 16000)
        with self.pid.memory.file() as mem:
            mem.seek(MOAT_LIST)
            blob = mem.read(MOAT_REC * n)
        for k in range(n):
            (t,) = struct.unpack_from("<i", blob, k * MOAT_REC)
            if t == tile and blob[k * MOAT_REC + 0xC]:
                return blob[k * MOAT_REC + 0xC], blob[k * MOAT_REC + 0xE]
        return None

    def plan_moat(self, x1, y1, x2, y2, dig=True):
        """The gates page's moat button and a drag from (x1, y1) to (x2, y2): the game marks the moat plan on the tiles
        it accepts (land without buildings or walls), a 2-tile brush every other tile. dig=False is the "don't
        dig" button
        over a plan. Diggers then dig it (dig_moat). The plan costs nothing."""
        self._check_budget()
        self._check(type(dig) is bool, "dig must be true or false")
        line = self._line(x1, y1, x2, y2)
        for x, y in line[::2] + (
            [line[-1]] if len(line) % 2 == 0 else []
        ):  # the drag's first and last tile, every other between
            queue_command(BRUSH, x, y, MOAT_BRUSH, MOAT_BIT, 0 if dig else UNPLAN_FLAG, pid=self.pid)
        return {
            "queued": "plan_moat" if dig else "unplan_moat",
            "tiles": len(line),
            "note": "marked when game time next moves",
        }

    def set_rations(self, level):
        self._check_budget()
        self._check(level in RATION_NAMES, f"rations must be one of {RATION_NAMES}")
        set_rations(RATION_NAMES.index(level), self.pid)
        return {"rations": level}

    def find_sites(self, building, limit=5, near=None):
        self._check(
            building in self.building_names or building == "keep" or (self.level >= 3 and building in SIEGE_ENGINES),
            f"unknown building {building!r}",
        )
        self._check(type(limit) is int and 1 <= limit <= 50, "limit must be 1..50")
        self._check(
            not self.menu or game_refuses(building, 200, 200, self.pid, menu=True) != HIDDEN,
            f"cannot build {building}: this mission's build menu does not offer it",
        )
        return Terrain(self.pid).find_sites(
            building,
            limit,
            near or self._home(),
            self._taken(),
            lambda x, y: game_refuses(building, x, y, self.pid, menu=self.menu) is None,
        )

    def _home(self):
        """find_sites' default centre: your keep in missions (their maps put it anywhere), else the econ maps'
        (235,230)."""
        if self.mission:
            keep = next(
                (
                    b
                    for b in buildings(self.pid, Terrain(self.pid), self.bt_names)
                    if b["owner"] == 1 and b["type"] == "keep"
                ),
                None,
            )
            if keep:
                return keep["x"], keep["y"]
        return 235, 230

    def _taken(self):
        """Tiles of the builds and walls queued in this pause, which the map does not show until time moves."""
        out = {}
        for b, x, y in self._pending:
            n = footprint(b)[1]
            out.update({(x + dx, y + dy): f"a queued {b}" for dy in range(n) for dx in range(n)})
        for kind, line in self._pending_walls:
            out.update({p: f"a queued {kind}" for p in line})
        return out

    def trade(self, good, qty):
        """GCT_BUY_OR_SELL (38): the game buys in lots of 5 and sells 5/10/20/50 at a time depending on stock,
        and checks
        neither the marketplace nor the gold; the bridge does."""
        self._check_budget()
        self._check(
            good in GOODS and good != "gold", f"unknown good {good!r}; one of {sorted(g for g in GOODS if g != 'gold')}"
        )
        res = GOODS[good]
        self._check(i32(self.pid, TRADEABLE + 4 * (8 if res == 7 else res)) != 0, f"{good} cannot be traded")
        self._check(
            type(qty) is int and qty != 0 and qty % 5 == 0 and abs(qty) <= 500,
            "qty must be a non-zero multiple of 5 (at most 500): > 0 buys, < 0 sells",
        )
        self._check(i32(self.pid, MARKET_ID) > 0, "you need a market to trade")
        buy, sell = i32(self.pid, PRICES + 8 * res), i32(self.pid, PRICES + 8 * res + 4)
        stock = self._stock()
        if qty > 0:
            lots = qty // 5
            gold = stock["gold"] - self._reserved.get("gold", 0)
            self._check(
                gold >= lots * buy, f"{qty} {good} cost {lots * buy} gold ({buy} per 5); you have {gold} not yet spent"
            )
            self._reserved["gold"] = self._reserved.get("gold", 0) + lots * buy
            for _ in range(lots):
                queue_command(BUY_OR_SELL, 0, res, pid=self.pid)
            return {
                "queued": "buy",
                "good": good,
                "qty": qty,
                "gold": -lots * buy,
                "note": "bought when game time next moves",
            }
        # The game sells all of a stock below 5, else 5 below 50, 10 below 100, 20 below 200, otherwise 50 (0x458940).
        have, left, plan = stock[good], -qty, []
        while left > 0:
            lot = have if have < 5 else 5 if have < 50 else 10 if have < 100 else 20 if have < 200 else 50
            self._check(
                0 < lot <= left,
                f"cannot sell exactly {-qty} {good} from {stock[good]}: the game sells "
                "5 at a time below 50 in stock, 10 below 100, 20 below 200, else 50",
            )
            plan.append(lot)
            have, left = have - lot, left - lot
        for _ in plan:
            queue_command(BUY_OR_SELL, 1, res, pid=self.pid)
        return {
            "queued": "sell",
            "good": good,
            "qty": qty,
            "gold": sum(plan) * sell // 5,
            "note": "sold when game time next moves",
        }

    def recruit(self, unit, count=1):
        """GCT_RECRUIT_UNIT (31) once per soldier. The game takes the gold and the weapons on the next tick and the
        soldier appears when the peasant has walked to the barracks (~20-40 ticks, seen live), but it does not
        check for a
        barracks; the bridge checks everything the game checks first, so queued recruits happen."""
        self._check_budget()
        offered = list(RECRUITABLE) + list(MERCENARIES) + (list(G2_RECRUITS) if self.level >= 2 else [])
        self._check(unit in offered, f"unknown unit {unit!r}; one of {offered}")
        self._check(type(count) is int and 1 <= count <= 50, "count must be 1..50")
        self._check(not self.menu or troop_offered(unit, self.pid), f"this mission does not offer {unit}")
        if unit in MERCENARIES:
            return self._recruit_mercenary(unit, count)
        if unit in G2_RECRUITS:
            return self._recruit_guild(unit, count)
        barracks = i32(self.pid, BARRACKS_ID)
        self._check(barracks > 0, "you need a barracks to recruit")
        t = UNIT_TYPE[unit]
        gold = i32(self.pid, RECRUIT_GOLD + 4 * (t - 22))
        goods = [r for r in (i32(self.pid, RECRUIT_GOODS + 16 * (t - 22) + 4 * k) for k in range(4)) if r > 0]
        names = {v: k for k, v in GOODS.items()}
        stock, res = self._stock(), self._reserved  # what this pause's queued commands have not yet spent
        have = stock["gold"] - res.get("gold", 0)
        self._check(have >= count * gold, f"{count} {unit} cost {count * gold} gold; you have {have} not yet spent")
        for r in goods:
            have = stock[names[r]] - res.get(names[r], 0)
            self._check(have >= count, f"each {unit} needs one {names[r]}; you have {have} not yet used")
        if unit == "knight" and self.level >= 2:  # the barracks greys the knight out without a horse (fail reason 4)
            horses = (i32(self.pid, HORSES) & 0xFFFF) - res.get("horses", 0)
            self._check(horses >= count, f"each knight needs a horse from your stables; you have {horses} not yet used")
            res["horses"] = res.get("horses", 0) + count
        idle = idle_peasants(self.pid) - res.get("peasants", 0)
        self._check(idle >= count, f"each recruit needs an idle peasant at the campfire; you have {idle} not yet used")
        for _ in range(count):
            queue_command(RECRUIT, t, barracks, pid=self.pid)
        for k, v in (("gold", count * gold), ("peasants", count), *((names[r], count) for r in goods)):
            res[k] = res.get(k, 0) + v
        return {
            "queued": unit,
            "count": count,
            "gold": -count * gold,
            "note": "paid when game time next moves; each soldier appears at the barracks ~40 ticks later",
        }

    def _recruit_mercenary(self, unit, count):
        """Arabian mercenaries: the same command (31) from the mercenary post, for gold and an idle peasant only."""
        post = i32(self.pid, MERC_POST_ID)
        self._check(post > 0, "you need a mercenary post to hire mercenaries")
        gold, res = MERCENARIES[unit] * count, self._reserved
        have = self._stock()["gold"] - res.get("gold", 0)
        self._check(have >= gold, f"{count} {unit} cost {gold} gold; you have {have} not yet spent")
        idle = idle_peasants(self.pid) - res.get("peasants", 0)
        self._check(idle >= count, f"each recruit needs an idle peasant at the campfire; you have {idle} not yet used")
        for _ in range(count):
            queue_command(RECRUIT, UNIT_TYPE[unit], post, pid=self.pid)
        res["gold"], res["peasants"] = res.get("gold", 0) + gold, res.get("peasants", 0) + count
        return {
            "queued": unit,
            "count": count,
            "gold": -gold,
            "note": "paid when game time next moves; each mercenary appears at the post shortly after",
        }

    def _recruit_guild(self, unit, count):
        """Engineers and laddermen at the engineers' guild, tunnelers at the tunnelers' guild, monks at a
        cathedral (the
        same command 31; the engineers' guild and cathedral portraits put the selected building in p1 (asm
        0x466E71), the
        tunnelers' guild's sets p0 only (0x466FB1) and the game finds the guild itself). The game recruits them
        with no such building (G1);
        the UI has no button without one; the guilds' and cathedral's own panels are the only queue sites.
        The bridge refuses without the building."""
        if unit == "monk":
            home = next(
                (
                    b["id"]
                    for b in buildings(self.pid, Terrain(self.pid), self.bt_names)
                    if b["owner"] == 1 and b["type"] == "cathedral"
                ),
                0,
            )
            self._check(home > 0, "you need a cathedral to train monks")
        else:
            home = i32(self.pid, G2_HOME[unit])
            guild = "a tunnelers' guild" if unit == "tunneler" else "an engineers' guild"
            self._check(home > 0, f"you need {guild} to recruit {unit}")
        gold, res = G2_RECRUITS[unit] * count, self._reserved
        have = self._stock()["gold"] - res.get("gold", 0)
        self._check(have >= gold, f"{count} {unit} cost {gold} gold; you have {have} not yet spent")
        idle = idle_peasants(self.pid) - res.get("peasants", 0)
        self._check(idle >= count, f"each recruit needs an idle peasant at the campfire; you have {idle} not yet used")
        for _ in range(count):
            queue_command(RECRUIT, UNIT_TYPE[unit], 0 if unit == "tunneler" else home, pid=self.pid)
        res["gold"], res["peasants"] = res.get("gold", 0) + gold, res.get("peasants", 0) + count
        return {
            "queued": unit,
            "count": count,
            "gold": -gold,
            "note": "paid when game time next moves; each recruit walks from the campfire to its building",
        }

    def build_wall(self, x1, y1, x2, y2, kind="wall"):
        """GCT_PLACE_WALL (25), as the castle menu's drag does: a straight horizontal or vertical line of stone
        wall, or of
        stairs leading off an own wall. Half a stone per tile; the game stops a line where the stone runs out, so the
        bridge asks for all of it up front. The game builds the line (and takes the stone) when the queued command
        runs, at the next frame that runs commands (another command queued, or time moving), not when ordered; the stock
        in memory lags the lines of this pause (game behavior; at level 5 _wall_sim keeps the account). Stone
        promised to
        other commands of the same pause (buildings, ammo, repair) is not reserved: the game then stops the line short,
        as for a human dragging with too little stone."""
        self._check_budget()
        self._check(kind in self.wall_kinds, f"kind must be one of {list(self.wall_kinds)}")
        self._check(all(type(v) is int for v in (x1, y1, x2, y2)), "x1, y1, x2, y2 must be integers")
        self._check(x1 == x2 or y1 == y2, "a wall runs straight: x1 == x2 or y1 == y2")
        n = max(abs(x2 - x1), abs(y2 - y1)) + 1
        self._check(
            n <= (12 if kind == "stairs" else 100), f"a {kind} line is at most {12 if kind == 'stairs' else 100} tiles"
        )
        dx, dy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
        line = [(x1 + k * dx, y1 + k * dy) for k in range(n)]
        t = Terrain(self.pid)
        busy = {p for _, tiles in self._pending_walls for p in tiles}
        new = n
        for x, y in line:
            i = t.tile(x, y)
            self._check(i is not None, f"({x},{y}) is off the map")
            assert i is not None
            if kind == "crenel":
                # a crenellated wall is a new wall line laid beside a wall. The UI's line check (0x5029D0, also the
                # executor's) refuses the whole line unless every tile has a wall neighbour that is not a
                # keep's (0x4F8640,
                # message 19); tiles already walls pass the check and the executor leaves them as they are (no stone).
                if t.logic[i] & L_WALL:
                    new -= 1
                    continue
                self._check(t.free(i) and (x, y) not in busy, f"tile ({x},{y}) is not free")
                self._check(
                    game_call(0x4F8640, TMS, i, y, pid=self.pid) != 0,
                    f"({x},{y}): {place_reason(19)} (crenellations are laid beside a wall)",
                )
                continue
            self._check(t.free(i) and not t.logic[i] & L_WALL and (x, y) not in busy, f"tile ({x},{y}) is not free")
        if kind == "stairs":
            x, y = line[0]
            near = [t.tile(x + a, y + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            self._check(
                any(
                    i is not None and t.logic[i] & L_WALL and not t.logic[i] & L_STAIRS and self._wall_owner(i) == 1
                    for i in near
                ),
                f"stairs must start next to one of your walls; ({x},{y}) is not",
            )
        stone, carry = self._stock()["stone"], i32(self.pid, HALF_STONE)
        sim = getattr(self, "_wall_sim", None)
        if self.level >= 5 and sim and sim[0] == len(self._pending_walls) > 0:
            # earlier lines of this pause have not run yet, so the stock and carry in memory are stale;
            # continue from
            # the bridge's own account of what those lines will take
            stone, carry = sim[1], sim[2]
        half = 2 * stone - (1 if carry else 0)
        self._check(half >= new, f"{new} tiles of {kind} cost {new / 2:g} stone; you have {half / 2:g}")
        queue_command(PLACE_WALL, x1, y1, x2, y2, self.wall_kinds[kind], min(half, 250), pid=self.pid)
        self._pending_walls.append((kind, line))
        if self.level < 5:  # frozen reply below level 5
            return {"queued": kind, "tiles": n, "stone": -n / 2, "note": "built when game time next moves"}
        # the executor charges quarter stones through 0x41C190 (a low-wall tile 1, every other kind 2), carrying
        # the remainder at player +0x2150, so this is the stone the game takes
        quarters = (1 if kind == "low_wall" else 2) * new + carry
        self._wall_sim = (len(self._pending_walls), stone - (quarters >> 2), quarters & 3)
        return {"queued": kind, "tiles": new, "stone": -(quarters >> 2), "note": "built when game time next moves"}

    def _wall_owner(self, i):
        with self.pid.memory.file() as mem:
            mem.seek(TMS + WALL_OWNER + i)
            return (mem.read(1)[0] & 7) + 1

    def _own_army(self, unit_ids):
        self._check(
            isinstance(unit_ids, list)
            and 1 <= len(unit_ids) <= 500
            and all(type(i) is int for i in unit_ids)
            and len(set(unit_ids)) == len(unit_ids),
            "unit_ids must be a list of 1..500 distinct integers",
        )
        live = {u["id"]: u for u in units(self.pid)}
        for i in unit_ids:
            u = live.get(i)
            self._check(
                u is not None
                and u["owner"] == 1
                and u["type"] in self.unit_names
                and (u["hp"] > 0 or not self.mission),
                f"unit {i} is not one of your live soldiers; see state()['units'] (owner 1)",
            )
        return live

    def _order(self, unit_ids, instruction, *params):
        """Select exactly these units into a new tribe (commands 15, 16) and give it one unit instruction with GCT 36
        (tribe, instruction, p2..p4), as the UI does (OpenSHC UnitInstructionType: 4 attack
        unit, 9 attack
        building, 30 disband, 31 stop, ...). Callers check the units and the parameters first."""
        if len(params) > 3:
            raise RealGameError("an instruction takes at most 3 parameters")
        queue_command(ATTACK, select(unit_ids, self.pid), instruction, *params, pid=self.pid)

    def move(self, unit_ids, x, y, waypoints=None):
        """Select exactly these soldiers into a tribe and send it to tile (x, y), as the UI does (commands 15, 16, 17).
        Waypoints: Shift held from the first click, so (x, y) is the first marker (p3 = -1) and each waypoint is a
        further marker (71) walked in order."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._campaign_lord(unit_ids, live, x, y, waypoints is None)
        if waypoints is not None:
            self._check(self.level >= 2, "waypoints are not available in this task")
            pts = self._markers([(x, y), *self._points(waypoints, "waypoints")], 2)
            tribe = select(unit_ids, self.pid)
            queue_command(MOVE, tribe, x, y, -1, 1, pid=self.pid)
            for n, (wx, wy) in enumerate(pts[1:], 2):
                queue_command(MARKER, tribe, wx, wy, n, pid=self.pid)
            self._note_order("move", {"x": pts[-1][0], "y": pts[-1][1]}, unit_ids)
            return {
                "queued": "move",
                "units": len(unit_ids),
                "markers": [list(p) for p in pts],
                "note": "they walk the markers in order when game time next moves",
            }
        self._check(
            type(x) is int and type(y) is int and Terrain(self.pid).tile(x, y) is not None, f"({x},{y}) is off the map"
        )
        queue_command(MOVE, select(unit_ids, self.pid), x, y, 0, 1, pid=self.pid)
        self._note_order("move", {"x": x, "y": y}, unit_ids)
        return {
            "queued": "move",
            "units": len(unit_ids),
            "x": x,
            "y": y,
            "note": "they set off when game time next moves",
        }

    def _campaign_lord(self, unit_ids, live, x=None, y=None, home_ok=True):
        """In a historical campaign (game mode 0) your lord can only be sent
        back to his
        keep or ordered to attack; a move to anywhere else (markers, patrols too) is refused."""
        if i32(self.pid, GAME_MODE) != 0 or not any(live[i]["type"] == UNIT_TYPE["lord"] for i in unit_ids):
            return
        keeps = [
            b for b in buildings(self.pid, Terrain(self.pid), self.bt_names) if b["owner"] == 1 and b["type"] == "keep"
        ]
        home = (
            home_ok
            and type(x) is int
            and type(y) is int
            and any(abs(x - k["x"]) <= 6 and abs(y - k["y"]) <= 6 for k in keeps)
        )
        self._check(home, "in a historical campaign your lord can only go back to his keep or attack")

    # unit commands
    def _points(self, points, what):
        self._check(
            isinstance(points, list) and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in points),
            f"{what} must be a list of [x, y] pairs",
        )
        return [tuple(p) for p in points]

    def _markers(self, pts, least):
        self._check(
            least <= len(pts) <= MAX_MARKERS, f"between {least} and {MAX_MARKERS} markers in all (the game keeps 9)"
        )
        t = Terrain(self.pid)
        for x, y in pts:
            self._check(type(x) is int and type(y) is int and t.tile(x, y) is not None, f"({x},{y}) is off the map")
        return pts

    def _drop_orders(self, unit_ids):
        """Missions: a new instruction replaces an earlier move or attack these soldiers had (_check_orders)."""
        self._orders = [o for o in self._orders if not set(o["last"]) & set(unit_ids)]

    def set_stance(self, unit_ids, stance):
        """The unit panel's stance buttons: command 70 (tribe, stance) for a tribe of exactly these soldiers."""
        self._check_budget()
        self._own_army(unit_ids)
        self._check(stance in STANCES, f"stance must be one of {list(STANCES)}")
        queue_command(STANCE, select(unit_ids, self.pid), STANCES[stance], pid=self.pid)
        return {"queued": "stance", "units": len(unit_ids), "stance": stance}

    def stop(self, unit_ids):
        """The unit panel's stop button: instruction 31."""
        self._check_budget()
        self._own_army(unit_ids)
        self._order(unit_ids, I_STOP)
        self._drop_orders(unit_ids)
        return {"queued": "stop", "units": len(unit_ids), "note": "they stop when game time next moves"}

    def disband(self, unit_ids):
        """The unit panel's disband button: instruction 30. The soldiers walk back to the campfire as peasants; the gold
        and weapons they cost are not refunded. The lord cannot be disbanded."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._check(all(live[i]["type"] != UNIT_TYPE["lord"] for i in unit_ids), "your lord cannot be disbanded")
        self._order(unit_ids, I_DISBAND)
        self._drop_orders(unit_ids)
        return {
            "queued": "disband",
            "units": len(unit_ids),
            "note": "they turn back into peasants when game time next moves",
        }

    def patrol(self, unit_ids, points):
        """The patrol button, then a click per marker (the first a move with p3 = 1, the rest Shift+clicks, command 71):
        the soldiers walk the markers in order and back, over and over."""
        self._check_budget()
        self._campaign_lord(unit_ids, self._own_army(unit_ids), home_ok=False)
        pts = self._markers(self._points(points, "points"), 1)
        tribe = select(unit_ids, self.pid)
        queue_command(MOVE, tribe, pts[0][0], pts[0][1], 1, 1, pid=self.pid)
        for n, (x, y) in enumerate(pts[1:], 2):
            queue_command(MARKER, tribe, x, y, n, pid=self.pid)
        self._drop_orders(unit_ids)
        return {"queued": "patrol", "units": len(unit_ids), "points": [list(p) for p in pts]}

    def attack_ground(self, unit_ids, x, y):
        """The unit panel's "attack here" (ranged soldiers only): a move to (x, y) with p3 = p4 = 0, then instruction 5
        (x, y, the UI's radius); they shoot at whatever comes inside it."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._check(
            all(live[i]["type"] in RANGED for i in unit_ids),
            "only ranged soldiers (archers, crossbowmen, "
            "slingers, horse archers, Arabian archers, fire throwers) can attack the ground",
        )
        self._check(
            type(x) is int and type(y) is int and Terrain(self.pid).tile(x, y) is not None, f"({x},{y}) is off the map"
        )
        tribe = select(unit_ids, self.pid)
        queue_command(MOVE, tribe, x, y, 0, 0, pid=self.pid)
        queue_command(ATTACK, tribe, I_ATTACK_GROUND, x, y, GROUND_RADIUS, pid=self.pid)
        self._drop_orders(unit_ids)
        return {"queued": "attack_ground", "units": len(unit_ids), "x": x, "y": y}

    def attack_wall(self, unit_ids, x, y):
        """A click on an enemy wall tile with soldiers selected: instruction 23 with the tile's index."""
        self._check_budget()
        self._own_army(unit_ids)
        t = Terrain(self.pid)
        i = t.tile(x, y) if type(x) is int and type(y) is int else None
        self._check(i is not None and t.logic[i] & L_WALL, f"({x},{y}) is not a wall tile")
        owner = self._wall_owner(i)
        self._check(
            owner != 1 and owner not in self.allies, f"the wall at ({x},{y}) is not an enemy's (player {owner})"
        )
        self._order(unit_ids, I_ATTACK_WALL, i)
        self._drop_orders(unit_ids)
        return {"queued": "attack_wall", "units": len(unit_ids), "x": x, "y": y}

    def attack(self, unit_ids, target_id=None, building_id=None):
        """Select these soldiers into a tribe and order it to attack an enemy unit (commands 15, 16, 36 with
        instruction 4)
        or an enemy building (instruction 9, as the AI and the UI do: building id and uid)."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._check((target_id is None) != (building_id is None), "give exactly one of target_id or building_id")
        if building_id is not None:
            b = (
                next((b for b in buildings(self.pid, Terrain(self.pid), self.bt_names) if b["id"] == building_id), None)
                if type(building_id) is int
                else None
            )
            self._check(
                b is not None and b["owner"] not in (0, 1) and b["owner"] not in self.allies,
                f"building {building_id} is not an enemy building; see state()['enemy']['buildings']",
            )
            assert b is not None
            self._order(unit_ids, 9, building_id, b["uid"])
            self._note_order("attack", {"building_id": building_id}, unit_ids, target_hp=b["hp"])
            return {
                "queued": "attack",
                "units": len(unit_ids),
                "building_id": building_id,
                "note": "they attack when game time next moves",
            }
        t = live.get(target_id) if type(target_id) is int else None
        self._check(
            t is not None
            and t["owner"] not in (0, 1)
            and t["type"] in self.unit_names
            and (t["hp"] > 0 or not self.mission),
            f"unit {target_id} is not a live enemy soldier; see state()['units']",
        )
        assert t is not None
        self._check(t["owner"] not in self.allies, f"unit {target_id} belongs to your ally (player {t['owner']})")
        self._order(unit_ids, 4, target_id, t["uid"])
        self._note_order("attack", {"target_id": target_id}, unit_ids, target_hp=t["hp"])
        return {
            "queued": "attack",
            "units": len(unit_ids),
            "target_id": target_id,
            "note": "they attack when game time next moves",
        }

    # siege engines
    def _engine(self, engine_id):
        """One of your siege engines (a unit), or a refusal."""
        u = next((u for u in units(self.pid) if u["id"] == engine_id), None) if type(engine_id) is int else None
        self._check(
            u is not None and u["owner"] == 1 and u["type"] in self.engine_names,
            f"unit {engine_id} is not one of your siege engines; see state()['units']",
        )
        assert u is not None
        return u

    def _unit_short(self, unit_id, off):
        with self.pid.memory.file() as mem:
            mem.seek(UNITS + unit_id * UNIT_SIZE + off)
            return struct.unpack("<h", mem.read(2))[0]

    def _engine_panel(self, u):
        """What the panel of one of your catapults or trebuchets shows besides its picture: shots left."""
        if u["owner"] != 1 or u["type"] not in AMMO_ENGINES or self.level < 3:
            return {}
        cows = i32(self.pid, COWS)  # the Launch Cow button shows the count only while there are cows (0x438D6B)
        return {"ammo": self._unit_short(u["id"], U_AMMO), **({"cows": cows} if cows > 0 else {})}

    def _engineers(self, unit_ids):
        live = self._own_army(unit_ids)
        self._check(
            all(live[i]["type"] == UNIT_TYPE["engineer"] for i in unit_ids),
            "only engineers can do this; select engineers",
        )

    def build_siege(self, engineer_ids, engine, x, y):
        """The mallet button with these engineers selected, an engine's icon, then a click on the map: a siege tent with
        its top-left corner at (x, y) (PLACE_BUILDING with the engineers' tribe). The game takes the engine's
        gold from its
        cost table when time moves; the engineers walk to the tent, build the engine and crew it."""
        self._check_budget()
        self._check(engine in SIEGE_ENGINES, f"unknown engine {engine!r}; one of {sorted(SIEGE_ENGINES)}")
        self._check(
            not self.menu or game_refuses(engine, 200, 200, self.pid, menu=True) != HIDDEN,
            f"cannot build {engine}: this mission's siege menu does not offer it",
        )  # no icon, whoever is selected
        self._engineers(engineer_ids)
        self._check(type(x) is int and type(y) is int, "x and y must be integers")
        err = Terrain(self.pid).site_error(engine, x, y, self._taken())
        self._check(err is None, f"cannot place a {engine} tent at ({x},{y}): {err}")
        reason = game_refuses(engine, x, y, self.pid)
        self._check(
            reason is None, f"cannot place a {engine} tent at ({x},{y}): the game refuses it ({place_reason(reason)})"
        )
        mapper, bt, _ = SIEGE_ENGINES[engine]
        with self.pid.memory.file() as mem:
            mem.seek(COSTS + bt * 20)
            wood, stone, _, _, gold = struct.unpack("<5i", mem.read(20))
        stock = self._stock()
        self._check(
            stock["wood"] >= wood and stock["stone"] >= stone and stock["gold"] >= gold,
            f"a {engine} needs {gold} gold; you have {stock['gold']}",
        )
        queue_command(PLACE_BUILDING, x, y, mapper, TENT_SIDE, 15, select(engineer_ids, self.pid), pid=self.pid)
        self._pending.append((engine, x, y))
        return {
            "queued": "build_siege",
            "engine": engine,
            "x": x,
            "y": y,
            "gold": gold,
            "note": f"the engineers walk to the tent and build it; it needs a crew of "
            f"{CREW_SIZE[SIEGE_ENGINES[engine][2]]} "
            "engineers and appears in state()['units']",
        }

    def man(self, engineer_ids, engine_id):
        """Engineers selected, a click on one of your engines that is short of crew (the UI's man cursor):
        instruction 16.
        As many of them as it needs walk to it and crew it."""
        self._check_budget()
        self._engineers(engineer_ids)
        e = self._engine(engine_id)
        need = CREW_SIZE[e["type"]] - self._unit_short(engine_id, U_CREW)
        self._check(
            need > 0, f"{self.engine_names[e['type']]} {engine_id} already has its full crew of {CREW_SIZE[e['type']]}"
        )
        if self.level >= 5:  # the man cursor (0x43589A) also needs the engine reachable from a selected engineer
            self._check(
                self._reachable(engineer_ids[0], engine_id),
                f"your engineers cannot reach {self.engine_names[e['type']]} {engine_id} "
                "(on a tower, they need a wall with stairs onto it)",
            )
        self._order(engineer_ids, I_MAN, engine_id, e["uid"])
        return {
            "queued": "man",
            "engine_id": engine_id,
            "crew_needed": need,
            "note": "they walk to it when game time next moves",
        }

    def _reachable(self, unit_id, target_id):
        """The game's path-region test 0x4A5320(player, region of target, region of unit, 1) as the man cursor asks it;
        a unit's region is the short at PATH_REGION[its tile (+0xD4)]."""

        def region(uid):
            with self.pid.memory.file() as mem:
                mem.seek(UNITS + uid * UNIT_SIZE + U_TILE)
                tile = struct.unpack("<i", mem.read(4))[0]
                mem.seek(PATH_REGION + 2 * tile)
                return struct.unpack("<h", mem.read(2))[0]

        return game_call(REACHABLE, REACH_THIS, 1, region(target_id), region(unit_id), 1, pid=self.pid) != 0

    def unman(self, engine_id):
        """The engine selected, a click on it (the UI's exit cursor): instruction 17. Its crew steps off; an engine
        without crew takes no orders."""
        self._check_budget()
        e = self._engine(engine_id)
        self._check(self._unit_short(engine_id, U_CREW) > 0, f"{self.engine_names[e['type']]} {engine_id} has no crew")
        self._order([engine_id], I_UNMAN, engine_id, e["uid"], 0)
        return {"queued": "unman", "engine_id": engine_id}

    def buy_ammo(self, engine_id):
        """The ammo button on a catapult's or trebuchet's panel (command 86): 10 stone from the stockpile for
        20 shots."""
        self._check_budget()
        e = self._engine(engine_id)
        self._check(
            e["type"] in AMMO_ENGINES,
            f"only catapults and trebuchets take ammo; {engine_id} is a {self.engine_names[e['type']]}",
        )
        stone = self._stock()["stone"]
        self._check(stone >= AMMO_STONE, f"ammo costs {AMMO_STONE} stone; you have {stone}")
        queue_command(BUY_AMMO, engine_id, pid=self.pid)
        return {"queued": "buy_ammo", "engine_id": engine_id, "stone": AMMO_STONE, "shots": AMMO_SHOTS}

    def throw_cow(self, engine_id, x, y):
        """The Launch Cow button on a catapult's or trebuchet's panel, then a click on the map: instruction 22
        (x, y, 15).
        The crew throws one of your cows (from a dairy farm) at the spot; the carcass lies where it lands."""
        self._check_budget()
        e = self._engine(engine_id)
        self._check(
            e["type"] in AMMO_ENGINES,
            f"only catapults and trebuchets throw cows; {engine_id} is a {self.engine_names[e['type']]}",
        )
        self._check(self._unit_short(engine_id, U_CREW) > 0, f"{self.engine_names[e['type']]} {engine_id} has no crew")
        self._check(i32(self.pid, COWS) > 0, "you have no cows to throw (a dairy farm's cattle are your cows)")
        self._check(
            type(x) is int and type(y) is int and Terrain(self.pid).tile(x, y) is not None, f"({x},{y}) is off the map"
        )
        self._order([engine_id], I_THROW_COW, x, y, GROUND_RADIUS)
        return {"queued": "throw_cow", "engine_id": engine_id, "x": x, "y": y, "cows": i32(self.pid, COWS)}

    def set_ladder(self, unit_ids, x, y):
        """Laddermen selected, a click on an enemy wall (the ladder cursor): instruction 24 with the wall tile's index.
        They carry a ladder to the wall and raise it; soldiers can then climb onto the wall there."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._check(
            all(live[i]["type"] == UNIT_TYPE["laddermen"] for i in unit_ids),
            "only laddermen can set a ladder; select laddermen",
        )
        t = Terrain(self.pid)
        i = t.tile(x, y) if type(x) is int and type(y) is int else None
        self._check(i is not None and t.logic[i] & L_WALL, f"({x},{y}) is not a wall tile")
        owner = self._wall_owner(i)
        self._check(
            owner != 1 and owner not in self.allies, f"the wall at ({x},{y}) is not an enemy's (player {owner})"
        )
        self._order(unit_ids, I_SET_LADDER, i)
        self._drop_orders(unit_ids)
        return {"queued": "set_ladder", "units": len(unit_ids), "x": x, "y": y}

    def dig_tunnel(self, unit_ids, x, y):
        """Tunnelers selected, "Dig Tunnel Here", then a click on the map: a tunnel entrance with its top-left corner at
        (x, y) (PLACE_BUILDING, mapper 66, with the tunnelers' tribe). A tunneler digs from it towards the nearest enemy
        building; when the tunnel collapses under it, that building is damaged."""
        self._check_budget()
        live = self._own_army(unit_ids)
        self._check(
            all(live[i]["type"] == UNIT_TYPE["tunneler"] for i in unit_ids),
            "only tunnelers can dig a tunnel; select tunnelers",
        )
        self._check(
            type(x) is int and type(y) is int and Terrain(self.pid).tile(x, y) is not None, f"({x},{y}) is off the map"
        )
        reason = game_refuses("tunnel", x, y, self.pid)
        self._check(reason is None, f"cannot dig a tunnel at ({x},{y}): the game refuses it ({place_reason(reason)})")
        queue_command(PLACE_BUILDING, x, y, *TUNNEL, 15, select(unit_ids, self.pid), pid=self.pid)
        self._drop_orders(unit_ids)
        return {"queued": "dig_tunnel", "units": len(unit_ids), "x": x, "y": y}

    def advance(self, ticks):
        self._check(type(ticks) is int and 1 <= ticks <= 3000, "ticks must be 1..3000")
        self._check_budget()
        if self.budget is not None:
            ticks = min(ticks, self.budget - self.tick)
        self._run(ticks)
        self._resolve_pending()
        return {
            "tick": self.tick,
            "ticks_left": (self.budget - self.tick if self.budget is not None else None),
            "game_over": self.game_over,
        }

    def _run(self, ticks):
        """Advance exactly `ticks`, stopping on every month boundary to close that month (and, with check_every, on
        every multiple of check_every ticks to watch the lord and the siege, so their events do not depend on how
        the agent splits its advances)."""
        end = self.tick + ticks
        while self.tick < end:
            boundary = TICKS_PER_MONTH * (self._months_done + 1)
            stop = min(end, boundary)
            if self.check_every:
                stop = min(stop, (self.tick // self.check_every + 1) * self.check_every)
            advance(stop - self.tick, self.pid)
            # crusader-bridge pauses on the first tick decision after the game ends a skirmish: watch there too
            over = self.vs_ai and (i32(self.pid, GAME_OVER) or i32(self.pid, MENU) != MENU_IN_GAME)
            if over or (self.check_every and self.tick % self.check_every == 0):
                self._watch()
            if self.tick == boundary:
                self._close_month()
            if self.match_over:
                break

    def _armies(self, live):
        mine = [u for u in live if u["owner"] == 1 and u["type"] in UNIT_NAMES and u["type"] != UNIT_TYPE["lord"]]
        enemy = [u for u in live if u["owner"] >= 2 and u["owner"] not in self.allies and u["type"] in UNIT_NAMES]
        return mine, enemy

    STALL_TICKS = (
        200  # missions: soldiers standing still this long, short of the order and not fighting -> order_stalled
    )

    def _note_order(self, cmd, target, unit_ids, target_hp=None):
        if self.mission:
            live = {u["id"]: u for u in units(self.pid)}
            pos = {i: (live[i]["x"], live[i]["y"], live[i]["hp"]) for i in unit_ids if i in live}
            # an order replaces any earlier order for the same soldiers
            self._orders = [o for o in self._orders if not set(o["last"]) & set(pos)]
            self._orders.append(
                {
                    "tick": self.tick,
                    "cmd": cmd,
                    "target": target,
                    "units": len(pos),
                    "last": pos,
                    "still_since": self.tick,
                    "target_hp": target_hp,
                }
            )

    def _target_hp(self, target, live):
        if "target_id" in target:
            u = live.get(target["target_id"])
            return u["hp"] if u else 0
        b = next(
            (b for b in buildings(self.pid, Terrain(self.pid), self.bt_names) if b["id"] == target["building_id"]), None
        )
        return b["hp"] if b else 0

    def _check_orders(self, live):
        """Missions, every check_every ticks: an order whose soldiers have all stood still for STALL_TICKS,
        without losing
        hp or hurting the target, and (a move) more than 4 tiles from where they were sent, was dropped by the game
        (an unreachable tile, a blocked path): an order_stalled event says so, once. An order is done when its soldiers
        arrive, its target dies, or they all die."""
        live = {u["id"]: u for u in live if u["hp"] > 0}  # a dying soldier (hp 0) is not standing still
        keep = []
        for o in self._orders:
            alive = [i for i in o["last"] if i in live]
            if not alive:
                continue
            t = o["target"]
            if "x" in t and all(abs(live[i]["x"] - t["x"]) + abs(live[i]["y"] - t["y"]) <= 4 for i in alive):
                continue  # arrived
            thp = self._target_hp(t, live) if o["target_hp"] is not None else None
            if thp == 0:
                continue  # the target is dead or gone
            busy = (
                any(
                    abs(live[i]["x"] - o["last"][i][0]) + abs(live[i]["y"] - o["last"][i][1]) >= 1
                    or live[i]["hp"] < o["last"][i][2]
                    for i in alive
                )
                or len(alive) < len(o["last"])
                or (thp is not None and thp < o["target_hp"])
            )
            o["last"] = {i: (live[i]["x"], live[i]["y"], live[i]["hp"]) for i in alive}
            if thp is not None:
                o["target_hp"] = thp
            if busy:
                o["still_since"] = self.tick
            elif self.tick - o["still_since"] >= self.STALL_TICKS:
                self._emit(
                    "order_stalled",
                    cmd=o["cmd"],
                    ordered_at=o["tick"],
                    units=o["units"],
                    **t,
                    at=[live[alive[0]]["x"], live[alive[0]]["y"]],
                    note="these soldiers stopped short and are not fighting; the game dropped the order "
                    "(unreachable tile or blocked path?)",
                )
                continue
            keep.append(o)
        self._orders = keep

    def _watch(self, live=None):
        """Lord and siege events, read from the unit array: lord_died the first time the run's lord is no longer a live
        unit with hp; siege_arrived when the attackers first exist; siege_defeated when none is left alive."""
        live = live if live is not None else units(self.pid)
        if self._orders:
            self._check_orders(live)
        if (
            self.lord_uid and not self.lord_died and not lord_alive(self.pid, self.lord_uid, live)
        ):  # campaign-1 has no lord
            self.lord_died = True
            self._emit("lord_died")
        for p, uid in self.enemy_lords.items():
            if p not in self.enemy_lords_died and not lord_alive(self.pid, uid, live, player=p):
                self.enemy_lords_died.add(p)
                self._emit("enemy_lord_died", player=p)
        if self.mission and not self.match_over and (i32(self.pid, GAME_OVER) or i32(self.pid, MENU) != MENU_IN_GAME):
            # The game ended the mission. Trail missions end like a skirmish (gameOver; the game's winner check 0x486600
            # marks the winners in WINNERS); a won campaign mission leaves the match for the next mission's book page.
            self.match_over = True
            if not i32(
                self.pid, GAME_OVER
            ):  # a campaign mission: the stats screen (menu 29) comes first, then the next page
                with contextlib.suppress(RealGameError):
                    wait_for(
                        lambda: i32(self.pid, MENU) not in (MENU_IN_GAME, 29), 60, "the game to leave the stats screen"
                    )
            menu = i32(self.pid, MENU)
            won = (i32(self.pid, WINNERS + 2) & 0xFFFF) == 1 if i32(self.pid, GAME_OVER) else menu == MENU_NEXT_MISSION
            self.game_over = "match won" if won else "match lost"
            self._emit(
                "match_end",
                result="won" if won else "lost",
                game_over_flag=i32(self.pid, GAME_OVER),
                menu=menu,
                winners=[i32(self.pid, WINNERS + 2 * p) & 0xFFFF for p in range(1, 9)],
            )
        if self.skirmish and not self.match_over and i32(self.pid, GAME_OVER):
            # A skirmish ends when a lord dies: the game sets gameOver and shows its end screen, after which it only
            # crawls on (~13 ticks/s, nothing left to play). The run ends here, at a tick on the check grid.
            self.match_over = True
            won = not self.lord_died and len(self.enemy_lords_died) == len(self.enemy_lords)
            self.game_over = "match won" if won else "match lost"
            self._emit(
                "match_end",
                winner=1 if won else sorted(set(self.enemy_lords) - self.enemy_lords_died) or None,
                result="won" if won else "lost",
            )
        return live

    def _close_month(self):
        st = read_state(self.pid)
        live = self._watch()
        mine, enemy = self._armies(live)
        self._months_done += 1
        self._emit(
            "month_end",
            month=self._months_done,
            gold=st["stock"]["gold"],
            popularity=st["popularity"],
            population=st["population"],
            game_tick=st["tick"],
            army=len(mine),
            enemy_army=len(enemy),
            lord_alive=not self.lord_died,
            **self._enemy_month(live),
        )

    def _enemy_month(self, live):
        """Skirmish month fields: the enemy's live soldiers and buildings, and whether every enemy starting
        lord lives."""
        if not self.vs_ai:
            return {}
        enemy_b = [b for b in buildings(self.pid, Terrain(self.pid), self.bt_names) if b["owner"] in self.enemy_lords]
        out: dict[str, object] = {
            "enemy_buildings": len(enemy_b),
            "enemy_lords_alive": len(self.enemy_lords) - len(self.enemy_lords_died),
        }
        if self.mission:  # missions only, so the scored skirmish's month records do not change
            out["enemy_lord_hp"] = {
                str(lord["owner"]): lord.get("hp", 0) for lord in self._lords(self.enemy_lords, live)
            }
            lord = next((u for u in live if u["uid"] == self.lord_uid), None) if self.lord_uid else None
            out["lord_hp"] = lord["hp"] if lord and not self.lord_died else 0
        return out

    def _resolve_pending(self):
        self._reserved = {}
        if not self._pending and not self._pending_demolish and not self._pending_walls:
            return
        t = Terrain(self.pid)
        for kind, line in self._pending_walls:
            built = sum(1 for x, y in line if (tile := t.tile(x, y)) is not None and t.logic[tile] & L_WALL)
            if built < len(line):
                self._emit("build_refused", building=kind, x=line[0][0], y=line[0][1], tiles=len(line), built=built)
        self._pending_walls = []
        for building, x, y in self._pending:
            i = t.tile(x, y)
            if i is None or t.building[i] <= 0:
                reason = game_refuses(building, x, y, self.pid)  # asked again now: usually a unit walked onto the spot
                self._emit(
                    "build_refused",
                    building=building,
                    x=x,
                    y=y,
                    reason=place_reason(reason) if reason is not None else "the spot was not free when time moved",
                )
        self._pending = []
        left = {(b["id"], b["uid"]) for b in buildings(self.pid, t, self.bt_names)}
        for bid, uid, kind in self._pending_demolish:
            if (bid, uid) in left:
                self._emit("demolish_refused", building_id=bid, type=kind)
        self._pending_demolish = []

    # observation
    def state(self):
        st = read_state(self.pid)
        t = Terrain(self.pid)
        live = units(self.pid)
        return {
            "tick": self.tick,
            "month": self._months_done,
            "ticks_per_month": TICKS_PER_MONTH,
            "ticks_left": (self.budget - self.tick if self.budget is not None else None),
            "game_over": self.game_over,
            "gold": st["stock"]["gold"],
            "popularity": st["popularity"],
            "population": st["population"],
            "housing": st["housing"],
            "tax": st["tax"] - 3,
            "rations": RATION_NAMES[st["rations"]] if 0 <= st["rations"] <= 4 else st["rations"],
            "stock": st["stock"],
            "date": {"month": st["month"], "year": st["year"]},
            "buildings": [
                {k: b[k] for k in ("id", "type", "x", "y")}
                for b in buildings(self.pid, t, self.bt_names)
                if b["owner"] == 1
            ],
            "idle_peasants": idle_peasants(self.pid),
            "units": [
                {
                    "id": u["id"],
                    "type": self.unit_names[u["type"]],
                    "owner": u["owner"],
                    "x": u["x"],
                    "y": u["y"],
                    "hp": u["hp"],
                    **self._engine_panel(u),
                }
                for u in live
                if u["type"] in self.unit_names and (u["hp"] > 0 or not self.mission)
            ],
            # missions leave out dying units (hp 0, gone in a few ticks); the scored tasks keep listing them, unchanged
            "lord_alive": not self.lord_died,
            **({"enemy": self._enemy_state(t, live)} if self.vs_ai else {}),
            **({"mission": self.mission} if self.mission else {}),
            **(
                {
                    "allies": {
                        "players": sorted(self.allies),
                        "lords": self._lords(self.ally_lords, live),
                        **({"panel": self._allies_panel()} if self.level >= 6 else {}),
                    }
                }
                if self.allies
                else {}
            ),
        }

    def _lords(self, lords, live):
        out = []
        for p, uid in lords.items():
            lid = i32(self.pid, LORD_ID + STRIDE * (p - 1))
            u = next((u for u in live if u["id"] == lid and u["uid"] == uid), None)
            alive = p not in self.enemy_lords_died and u is not None and u["hp"] > 0
            details = {k: u[k] for k in ("id", "x", "y", "hp")} if alive and u is not None else {}
            out.append({"owner": p, "alive": alive, **details})
        return out

    def _enemy_state(self, t, live):
        """What the player can see of the CPU lords (skirmish shows the whole map): each enemy's lord and buildings."""
        out = {"lords": self._lords(self.enemy_lords, live), "buildings": []}
        out["buildings"] = [
            {k: b[k] for k in ("id", "type", "x", "y", "owner", "hp", "max_hp")}
            for b in buildings(self.pid, t, self.bt_names)
            if b["owner"] in self.enemy_lords
        ]
        return out

    def events(self, since=0):
        self._check(type(since) is int and 0 <= since <= len(self._events), "invalid event offset")
        return self._events[since:]

    def attack_building(self, unit_ids, building_id):
        return self.attack(unit_ids, building_id=building_id)

    def select(self, unit_ids):
        self._own_army(unit_ids)
        return {"tribe": select(unit_ids, self.pid)}

    def look(self, x, y):
        raise RealGameError("camera control is not supported")

    def ascii_map(self, x0=0, y0=0, x1=399, y1=399):
        self._check(
            all(type(v) is int and 0 <= v < MAP_SIDE for v in (x0, y0, x1, y1)) and x0 <= x1 and y0 <= y1,
            "invalid map rectangle",
        )
        return "\n".join(row[x0 : x1 + 1] for row in ascii_map(self.pid).splitlines()[y0 : y1 + 1])


if __name__ == "__main__":
    if sys.argv[1:2] == ["start"]:
        start_match()
    elif sys.argv[1:2] == ["advance"]:
        advance(int(sys.argv[2]))
    print(json.dumps(read_state()))
