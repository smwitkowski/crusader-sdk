# Concepts

## Time and pause

The game is paused between calls and moves only inside `advance(ticks)`, which runs 1 to 3000 ticks and returns the current tick, the remaining budget if one is configured, and the game-over status. A match can end before the requested interval. A month is exactly 800 ticks. Most commands are queued: the game applies them when time next moves, so advance and read state again before relying on an effect. Several commands can be queued in one pause; the driver tracks the gold, goods, peasants and tiles they will use, so a later command in the same pause is refused if an earlier one has already claimed what it needs.

## Coordinates and IDs

Map coordinates are tile `(x, y)` pairs on a 400 × 400 grid; map rectangles are inclusive. A building's coordinates identify the top-left tile of its square footprint. Use `find_sites` to find positions the game accepts, then handle refusal because conditions can change. Unit and building IDs come from state; they belong to the current match, and unit IDs are reused after a unit dies. Orders need owned units or buildings. Player 1 is the controlled player; other numbers are computer lords.

## Events and refusals

`events(since)` takes an offset into the session's event list; after reading a batch, advance the offset by its length. Event fields vary by type. `advance` does not return events; read them with `events`. See [events](reference/events.md).

A command is refused when its arguments are invalid or the game would not allow the action; the client raises `CrusaderError` with the reason, which is usually specific enough to act on (for example the amounts a build needs and the amounts held). A successful request means the command was queued, not that it achieved its aim: a unit can walk onto a building site, or a path can be blocked. Inspect subsequent state and events. After the game ends a match, every command except `state` is refused. See [errors](reference/errors.md).

## Game mechanics primer

This section summarizes the rules of Stronghold Crusader that matter when playing through the SDK. Figures come from the game's own panels as the driver reads them, unless marked as measured or taken from the game manual.

### Peasants, housing and jobs

The town's population is its peasants. New peasants walk in from the map edge while popularity is 50 or more and housing has room; below 50 they start to leave. Each hovel houses 8. An arriving peasant waits at the campfire by the keep (`State.idle_peasants`) until a staffed building needs a worker or `recruit` turns him into a soldier. A staffed building without a worker produces nothing, so buildings, housing and popularity have to grow together. `disband` and putting buildings to sleep return people to the campfire.

### Popularity

Popularity runs from 0 to 100 and moves each month by the sum of several factors. `report("popularity")` returns each factor and their sum (`coming_month`) in the units the game displays:

| Factor | Values |
|---|---|
| Food (rations) | `none` −8, `half` −4, `normal` 0, `extra` +4, `double` +8. An empty granary counts as −8 whatever the setting. |
| Food (variety) | Eating 2 food types +1, 3 types +2, all 4 types +3. |
| Tax | Level −3: +7, −2: +5, −1: +3, 0: +1, 1: −2, 2: −4, 3: −6, 4: −8, 5: −12, 6: −16, 7: −20, 8: −24. A bribe level with an empty treasury counts as +1. |
| Crowding | 0 while the game's crowding figure is at or below 100 %; −2 for each further 20 %, down to −10. Build hovels before the town outgrows them. |
| Fear factor | −5 to +5: the town's fear level, raised by good things and lowered by bad things. |
| Religion | By share of the population blessed: under 25 % 0, 25 % +2, 50 % +4, 75 % +6, 95 % +8; plus two further bonuses of +1 and +2, which the game manual attributes to a church and a cathedral. |
| Ale coverage | By share of the population served by inns: under 25 % 0, 25 % +2, 50 % +4, 75 % +6, 100 % +8. |

Food, tax and crowding count as 0 until the town has peasants. Scripted map events can add further lines. Popularity acts as a reserve: it can be built up with low taxes and good food and then spent on a period of high taxes, as long as it stays at 50 or above.

### Food and rations

Peasants eat apples, cheese, meat and bread from the granary; consumption grows with the population and with the ration level. Wheat and flour are not food until baked. Food only counts once a worker has delivered it to a granary, and a new granary must touch an existing one. When the granary is full, deliveries stop. `building_info(granary_id)` reports the food stock and `months_supply`. A small town eats little (measured: about 5 units a month for 34 peasants at normal rations), so an early surplus can pay for `extra` rations or be sold.

### Taxes and gold

`set_tax(level)` takes −3 to 8. Positive levels collect gold from every peasant; the game accumulates it weekly and pays it into the treasury at the end of each game month, so the first receipts arrive a month after the change. Negative levels are bribes paid out of the treasury the same way. Measured examples: level 4 yields about 48 gold a month from 40 peasants; level −3 costs about 1 gold per peasant per month. The other sources of gold are selling goods at a market and, at the start of a match, the starting treasury.

### The first month of a new skirmish

A new skirmish does not hand over its starting goods at once: the starting gold and wood are paid out gradually over roughly the first 640 ticks. Builds ordered at tick 0 can therefore be refused for lack of wood or gold. Advance most of the first month, then read `State.stock` and start building.

### Production chains

Raw-material buildings (woodcutter, quarry with ox tether, iron mine, pitch rig, farms) deliver to the stockpile or granary; processing buildings (mill, bakery, brewery, weapon workshops) fetch an input from a store and deliver the product to another. The full chains are tabulated in the [buildings reference](reference/buildings.md#production-chains). Points that decide whether a chain works:

- Every link needs its own worker and therefore a free peasant.
- Workers walk. Place producers near what they harvest and near the store they deliver to, and leave paths open: buildings packed around the keep, granary or stockpile can wall them in and stop all deliveries.
- Stores fill up. A stockpile holds a limited number of goods; extra stockpiles, granaries and armories must touch the existing one.
- Farms need farmable grass (`,` on the map), iron mines ore, quarries stone and pitch rigs marsh. `find_sites` returns only spots the game accepts.
- Output arrives in loads with long gaps (measured: a woodcutter brings about 12 wood a load; a quarry's first ox load of about 12 stone arrives several months after it is built). A month with nothing from a new building is normal.

### Fear factor

Good things (maypole, dancing bear, gardens, statue, shrine) and bad things (gallows, stocks, dungeon and the rest) move the town's fear level between −5 and +5 once there are enough of them for the town's size. Good things raise popularity each month, slow workers and strengthen troops; bad things lower popularity, speed workers up (measured at level −4: about a third more wood per woodcutter) and weaken troops. `report("fear")` shows the counts, the level, and `efficiency_pct`; `report("army")` shows the matching combat modifier as `fear_bonus`, 5 % per level.

### Soldiers and winning

Barracks troops need a weapon (and for some, armor) from the armory, gold and an idle peasant; mercenaries, engineers, laddermen, tunnelers and monks need only gold and a peasant at their building. Weapons are made by workshops or bought at the market. See [units](reference/units.md). In a skirmish each player has a lord; the game ends the match shortly after a lord dies, and `State.game_over` then reads `"match won"` or `"match lost"`. A keep cannot be damaged, so an enemy is beaten by reaching and killing his lord. Soldiers fight enemies that come near on their own according to their stance; orders direct them at a unit, building, wall tile or place.

### Castle

Stone walls cost half a stone a tile and block ground units; stairs let soldiers onto them, gatehouses let them through, and towers give ranged troops height. A moat is planned for free and dug by soldiers; a dug moat blocks ground units. Pitch ditches lit from a brazier, killing pits, dog cages and tower engines add to the defence. Attackers answer with siege engines, ladders, siege towers, tunnels and by filling moats. See the [defences](commands/defences.md) and [siege](commands/siege.md) commands.
