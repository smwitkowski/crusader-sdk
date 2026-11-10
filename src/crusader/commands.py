"""Public client command metadata.

Required parameters omit the default key. Command is the bridge endpoint name.
"""

from typing import TypedDict


class _OptionalParameter(TypedDict, total=False):
    default: object
    constraints: str
    wire_names: list[str]


class Parameter(_OptionalParameter):
    name: str
    type: str


class Command(TypedDict):
    command: str
    group: str
    params: list[Parameter]
    return_type: str
    summary: str


COMMANDS: dict[str, Command] = {
    "state": {
        "command": "state",
        "group": "observe",
        "params": [],
        "return_type": "State",
        "summary": "Return the current visible game state.",
    },
    "map": {
        "command": "ascii_map",
        "group": "observe",
        "params": [
            {"name": "x0", "type": "int", "default": 0, "constraints": "0..399; x0 <= x1"},
            {"name": "y0", "type": "int", "default": 0, "constraints": "0..399; y0 <= y1"},
            {"name": "x1", "type": "int", "default": 399, "constraints": "0..399; x1 >= x0"},
            {"name": "y1", "type": "int", "default": 399, "constraints": "0..399; y1 >= y0"},
        ],
        "return_type": "str",
        "summary": "Return the inclusive tile rectangle as text.",
    },
    "find_sites": {
        "command": "find_sites",
        "group": "observe",
        "params": [
            {
                "name": "building",
                "type": "str",
                "constraints": (
                    "Building or siege engine placement name (not ID); woodcutter, stockpile, hovel, quarry, "
                    "wheat_farm, hops_farm, apple_orchard, dairy_farm, mill, bakery, brewery, market, hunters_post, "
                    "granary, armory, barracks, inn, chapel, church, well, fletcher, poleturner, blacksmith, "
                    "armourer, tanner, mercenary_post, iron_mine, lookout_tower, perimeter_tower, defense_turret, "
                    "square_tower, round_tower, gatehouse, large_gatehouse, engineers_guild, tunnelers_guild, "
                    "stables, cathedral, apothecary, ox_tether, pitch_rig, maypole, dancing_bear, small_garden, "
                    "medium_garden, large_garden, statue, shrine, gallows, cess_pit, stocks, burning_stake, "
                    "dungeon, stretching_rack, gibbet, chopping_block, dunking_stool, gatehouse_turned, "
                    "large_gatehouse_turned, drawbridge, killing_pit, pitch_ditch, dog_cage, oil_smelter, "
                    "water_pot, keep, catapult, trebuchet, battering_ram, siege_tower, portable_shield, "
                    "fire_ballista; the map's build menu can withhold some"
                ),
            },
            {"name": "limit", "type": "int", "default": 5, "constraints": "1..50"},
            {
                "name": "near",
                "type": "tuple[int, int] | None",
                "default": None,
                "wire_names": ["near_x", "near_y"],
                "constraints": "tile (x, y) to search around; the search centres on (235, 230) when omitted",
            },
        ],
        "return_type": "list[Site]",
        "summary": "Find valid building sites, optionally near a tile.",
    },
    "look": {
        "command": "look",
        "group": "observe",
        "params": [
            {"name": "x", "type": "int", "constraints": "0..399; the command is always refused"},
            {"name": "y", "type": "int", "constraints": "0..399; the command is always refused"},
        ],
        "return_type": "CommandResult",
        "summary": "Centre the camera on a tile; always refused by the game driver.",
    },
    "select": {
        "command": "select",
        "group": "observe",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int]",
                "constraints": "list of 1..500 distinct IDs of own live units",
            }
        ],
        "return_type": "CommandResult",
        "summary": "Select owned soldiers by ID.",
    },
    "events": {
        "command": "events",
        "group": "observe",
        "params": [{"name": "since", "type": "int", "default": 0, "constraints": "0..current event count"}],
        "return_type": "list[Event]",
        "summary": "Return events from list offset since onward.",
    },
    "build": {
        "command": "build",
        "group": "economy",
        "params": [
            {
                "name": "building",
                "type": "str",
                "constraints": (
                    "Building placement name (not ID); woodcutter, stockpile, hovel, quarry, wheat_farm, hops_farm, "
                    "apple_orchard, dairy_farm, mill, bakery, brewery, market, hunters_post, granary, armory, "
                    "barracks, inn, chapel, church, well, fletcher, poleturner, blacksmith, armourer, tanner, "
                    "mercenary_post, iron_mine, lookout_tower, perimeter_tower, defense_turret, square_tower, "
                    "round_tower, gatehouse, large_gatehouse, engineers_guild, tunnelers_guild, stables, cathedral, "
                    "apothecary, ox_tether, pitch_rig, maypole, dancing_bear, small_garden, medium_garden, "
                    "large_garden, statue, shrine, gallows, cess_pit, stocks, burning_stake, dungeon, "
                    "stretching_rack, gibbet, chopping_block, dunking_stool, gatehouse_turned, "
                    "large_gatehouse_turned, drawbridge, killing_pit, pitch_ditch, dog_cage, oil_smelter, "
                    "water_pot, flag_1, flag_2, flag_3, flag_4, heads, brazier, mangonel, ballista; "
                    "the map's build menu can withhold some"
                ),
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Place a building at the top-left tile of its footprint.",
    },
    "demolish": {
        "command": "demolish",
        "group": "economy",
        "params": [
            {"name": "building_id", "type": "int", "constraints": "ID of an owned building from state buildings"}
        ],
        "return_type": "CommandResult",
        "summary": "Demolish an owned building.",
    },
    "set_tax": {
        "command": "set_tax",
        "group": "economy",
        "params": [{"name": "level", "type": "int", "constraints": "-3..8"}],
        "return_type": "CommandResult",
        "summary": "Set tax from -3 to 8.",
    },
    "set_rations": {
        "command": "set_rations",
        "group": "economy",
        "params": [{"name": "level", "type": "str", "constraints": "none, half, normal, extra, double"}],
        "return_type": "CommandResult",
        "summary": "Set the ration level.",
    },
    "trade": {
        "command": "trade",
        "group": "economy",
        "params": [
            {
                "name": "good",
                "type": "str",
                "constraints": (
                    "wood, hops, stone, iron, pitch, wheat, bread, cheese, meat, apples, ale, flour, bows, "
                    "crossbows, spears, pikes, maces, swords, leather_armor, metal_armor; tradeability depends on "
                    "game state"
                ),
            },
            {"name": "qty", "type": "int", "constraints": "nonzero multiple of 5; positive buys, negative sells"},
        ],
        "return_type": "CommandResult",
        "summary": "Buy or sell goods in multiples of five.",
    },
    "recruit": {
        "command": "recruit",
        "group": "economy",
        "params": [
            {
                "name": "unit",
                "type": "str",
                "constraints": (
                    "Unit name (not ID); archer, crossbowman, spearman, pikeman, maceman, swordsman, knight, "
                    "arabian_archer, slave, slinger, assassin, horse_archer, arabian_swordsman, fire_thrower, "
                    "engineer, laddermen, tunneler, monk; a map can withhold some"
                ),
            },
            {"name": "count", "type": "int", "default": 1, "constraints": "1..50"},
        ],
        "return_type": "CommandResult",
        "summary": "Recruit soldiers or mercenaries.",
    },
    "move": {
        "command": "move",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "waypoints",
                "type": "Iterable[tuple[int, int]] | None",
                "default": None,
                "constraints": "1..8 points if provided; each must be a valid map tile (coordinates 0..399)",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order units to a tile and optional subsequent waypoints.",
    },
    "set_stance": {
        "command": "set_stance",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {"name": "stance", "type": "str", "constraints": "stand_ground, defensive, aggressive"},
        ],
        "return_type": "CommandResult",
        "summary": "Set unit stance to stand_ground, defensive, or aggressive.",
    },
    "stop": {
        "command": "stop",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            }
        ],
        "return_type": "CommandResult",
        "summary": "Stop the selected units.",
    },
    "disband": {
        "command": "disband",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            }
        ],
        "return_type": "CommandResult",
        "summary": "Return soldiers to the campfire as peasants.",
    },
    "patrol": {
        "command": "patrol",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "points",
                "type": "Iterable[tuple[int, int]]",
                "constraints": "1..9 points; each point must be a valid map tile (coordinates 0..399)",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order units to patrol one to nine points.",
    },
    "attack_ground": {
        "command": "attack_ground",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order ranged units to attack a tile.",
    },
    "attack_wall": {
        "command": "attack_wall",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order units to attack an enemy wall tile.",
    },
    "attack": {
        "command": "attack",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {"name": "target_id", "type": "int", "constraints": "ID of a live enemy unit from state units"},
        ],
        "return_type": "CommandResult",
        "summary": "Order units to attack an enemy unit.",
    },
    "attack_building": {
        "command": "attack_building",
        "group": "military",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {"name": "building_id", "type": "int", "constraints": "ID of an enemy building from state enemy buildings"},
        ],
        "return_type": "CommandResult",
        "summary": "Order units to attack an enemy building.",
    },
    "build_siege": {
        "command": "build_siege",
        "group": "siege",
        "params": [
            {
                "name": "engineer_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live engineers; None is refused by the game driver",
            },
            {
                "name": "engine",
                "type": "str",
                "constraints": "catapult, trebuchet, battering_ram, siege_tower, portable_shield, fire_ballista",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Construct a siege engine at the tent's top-left tile.",
    },
    "man": {
        "command": "man",
        "group": "siege",
        "params": [
            {
                "name": "engineer_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live engineers; None is refused by the game driver",
            },
            {"name": "engine_id", "type": "int", "constraints": "ID of an own siege engine from state units"},
        ],
        "return_type": "CommandResult",
        "summary": "Assign engineers to crew an engine.",
    },
    "unman": {
        "command": "unman",
        "group": "siege",
        "params": [{"name": "engine_id", "type": "int", "constraints": "ID of an own siege engine from state units"}],
        "return_type": "CommandResult",
        "summary": "Remove an engine's crew.",
    },
    "buy_ammo": {
        "command": "buy_ammo",
        "group": "siege",
        "params": [{"name": "engine_id", "type": "int", "constraints": "ID of an own siege engine from state units"}],
        "return_type": "CommandResult",
        "summary": "Buy ammunition for a catapult or trebuchet.",
    },
    "throw_cow": {
        "command": "throw_cow",
        "group": "siege",
        "params": [
            {"name": "engine_id", "type": "int", "constraints": "ID of an own siege engine from state units"},
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order a catapult or trebuchet to throw a cow at a tile.",
    },
    "set_ladder": {
        "command": "set_ladder",
        "group": "siege",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order laddermen to raise ladders against a wall.",
    },
    "dig_tunnel": {
        "command": "dig_tunnel",
        "group": "siege",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order tunnelers to dig from a tile.",
    },
    "repair": {
        "command": "repair",
        "group": "economy",
        "params": [
            {"name": "building_id", "type": "int", "constraints": "ID of an owned building from state buildings"}
        ],
        "return_type": "CommandResult",
        "summary": "Repair an owned tower or gatehouse.",
    },
    "set_building_active": {
        "command": "set_building_active",
        "group": "economy",
        "params": [
            {"name": "building_id", "type": "int", "constraints": "ID of an owned building from state buildings"},
            {"name": "active", "type": "bool", "constraints": "True wakes; False puts to sleep"},
        ],
        "return_type": "CommandResult",
        "summary": "Set whether buildings of this type are active.",
    },
    "set_workshop_product": {
        "command": "set_workshop_product",
        "group": "economy",
        "params": [
            {"name": "building_id", "type": "int", "constraints": "ID of an owned building from state buildings"},
            {
                "name": "weapon",
                "type": "str",
                "constraints": "fletcher: bows, crossbows; poleturner: spears, pikes; blacksmith: maces, swords",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Set a workshop's product.",
    },
    "set_food_allowed": {
        "command": "set_food_allowed",
        "group": "economy",
        "params": [
            {"name": "food", "type": "str", "constraints": "apples, cheese, meat, bread"},
            {"name": "allowed", "type": "bool", "constraints": "True allows eating; False forbids it"},
        ],
        "return_type": "CommandResult",
        "summary": "Allow or disallow consumption of a food.",
    },
    "set_gate": {
        "command": "set_gate",
        "group": "defences",
        "params": [
            {"name": "building_id", "type": "int", "constraints": "ID of an owned building from state buildings"},
            {"name": "open", "type": "bool", "constraints": "True opens; False closes"},
        ],
        "return_type": "CommandResult",
        "summary": "Open or close a gatehouse or drawbridge.",
    },
    "plan_moat": {
        "command": "plan_moat",
        "group": "defences",
        "params": [
            {
                "name": "x1",
                "type": "int",
                "constraints": "0..399; valid map tile; line must be straight and at most 100 tiles",
            },
            {
                "name": "y1",
                "type": "int",
                "constraints": "0..399; valid map tile; line must be straight and at most 100 tiles",
            },
            {
                "name": "x2",
                "type": "int",
                "constraints": "0..399; valid map tile; line must be straight and at most 100 tiles",
            },
            {
                "name": "y2",
                "type": "int",
                "constraints": "0..399; valid map tile; line must be straight and at most 100 tiles",
            },
            {"name": "dig", "type": "bool", "default": True, "constraints": "True marks the plan; False removes it"},
        ],
        "return_type": "CommandResult",
        "summary": "Mark or remove a moat plan along a line.",
    },
    "dig_moat": {
        "command": "dig_moat",
        "group": "defences",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order units to dig a planned moat tile.",
    },
    "fill_moat": {
        "command": "fill_moat",
        "group": "defences",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order units to fill an enemy moat tile.",
    },
    "delete_wall": {
        "command": "delete_wall",
        "group": "defences",
        "params": [
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Delete an owned wall tile.",
    },
    "light_pitch": {
        "command": "light_pitch",
        "group": "defences",
        "params": [
            {
                "name": "unit_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live units; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order ranged units to ignite a pitch ditch.",
    },
    "oil_duty": {
        "command": "oil_duty",
        "group": "defences",
        "params": [
            {
                "name": "engineer_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live engineers; None is refused by the game driver",
            },
            {"name": "smelter_id", "type": "int", "constraints": "ID of an owned oil_smelter"},
        ],
        "return_type": "CommandResult",
        "summary": "Assign engineers to an oil smelter.",
    },
    "pour_oil": {
        "command": "pour_oil",
        "group": "defences",
        "params": [
            {
                "name": "engineer_ids",
                "type": "Iterable[int] | None",
                "constraints": "list of 1..500 distinct IDs of own live engineers; None is refused by the game driver",
            },
            {
                "name": "x",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
            {
                "name": "y",
                "type": "int",
                "constraints": "0..399; must form a valid map tile with its paired coordinate",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Order engineers to pour oil; currently refused by the game driver.",
    },
    "report": {
        "command": "report",
        "group": "observe",
        "params": [
            {
                "name": "page",
                "type": "str",
                "constraints": "popularity, fear, religion, army, food, population, stores, weapons, merit",
            }
        ],
        "return_type": "ReportResult",
        "summary": "Return a page of the scribe's book.",
    },
    "building_info": {
        "command": "building_info",
        "group": "observe",
        "params": [
            {"name": "building_id", "type": "int", "constraints": "ID of an owned building from state buildings"}
        ],
        "return_type": "BuildingInfo",
        "summary": "Return the panel information for an owned building.",
    },
    "ally_order": {
        "command": "ally_order",
        "group": "allies",
        "params": [
            {"name": "ally", "type": "int", "constraints": "player number of an ally whose lord is alive"},
            {"name": "order", "type": "str", "constraints": "attack, defend, cancel"},
            {
                "name": "target",
                "type": "int | None",
                "default": None,
                "constraints": "enemy player ID with a living lord for attack; None for defend or cancel",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Ask an ally to attack, defend, or cancel orders.",
    },
    "ally_send_goods": {
        "command": "ally_send_goods",
        "group": "allies",
        "params": [
            {"name": "ally", "type": "int", "constraints": "player number of an ally whose lord is alive"},
            {
                "name": "good",
                "type": "str",
                "constraints": (
                    "wood, hops, stone, iron, pitch, wheat, bread, cheese, meat, apples, ale, gold, flour, bows, "
                    "crossbows, spears, pikes, maces, swords, leather_armor, metal_armor"
                ),
            },
            {"name": "qty", "type": "int", "constraints": "positive multiple of 5"},
        ],
        "return_type": "CommandResult",
        "summary": "Send goods to an ally.",
    },
    "ally_request_goods": {
        "command": "ally_request_goods",
        "group": "allies",
        "params": [
            {"name": "ally", "type": "int", "constraints": "player number of an ally whose lord is alive"},
            {
                "name": "good",
                "type": "str",
                "constraints": (
                    "wood, hops, stone, iron, pitch, wheat, bread, cheese, meat, apples, ale, gold, flour, bows, "
                    "crossbows, spears, pikes, maces, swords, leather_armor, metal_armor"
                ),
            },
            {"name": "qty", "type": "int", "constraints": "positive multiple of 5"},
        ],
        "return_type": "CommandResult",
        "summary": "Request goods from an ally.",
    },
    "ally_answer": {
        "command": "ally_answer",
        "group": "allies",
        "params": [
            {"name": "ally", "type": "int", "constraints": "player number of an ally whose lord is alive"},
            {"name": "accept", "type": "bool", "constraints": "True sends the requested goods; False refuses"},
        ],
        "return_type": "CommandResult",
        "summary": "Accept or refuse an ally's request.",
    },
    "build_wall": {
        "command": "build_wall",
        "group": "defences",
        "params": [
            {
                "name": "x1",
                "type": "int",
                "constraints": "0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise",
            },
            {
                "name": "y1",
                "type": "int",
                "constraints": "0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise",
            },
            {
                "name": "x2",
                "type": "int",
                "constraints": "0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise",
            },
            {
                "name": "y2",
                "type": "int",
                "constraints": "0..399; valid map tile; straight line, at most 12 tiles for stairs or 100 otherwise",
            },
            {
                "name": "kind",
                "type": "str",
                "default": "wall",
                "constraints": "wall, stairs, low_wall, crenel; stairs lines are at most 12 tiles",
            },
        ],
        "return_type": "CommandResult",
        "summary": "Build a straight line of wall or stairs.",
    },
    "advance": {
        "command": "advance",
        "group": "time",
        "params": [{"name": "ticks", "type": "int", "constraints": "1..3000"}],
        "return_type": "AdvanceResult",
        "summary": "Run the game for 1 to 3000 ticks.",
    },
}
