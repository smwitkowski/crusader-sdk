# Map legend

The driver's text map renders each tile using the first matching condition below:

| Character | Meaning |
| --- | --- |
| space | Outside the valid tile area. |
| Building letter or `B` | A building occupies the tile; `B` is the fallback when its name has no mapped letter. |
| `~` | Tile lacks the land flag. |
| `f` | Farmland. |
| `^` | A blocked or wall tile. |
| `,` | Land with a farmable logic flag. |
| `.` | Other land. |

Building letters are `h` hovel, `w` woodcutter, `m` market, `c` chapel or church, `a` apple orchard, `d` dairy farm, `p` hunters post, `f` wheat farm, `n` mill, `k` bakery, `g` granary, `s` stockpile, `q` quarry, `b` brewery, `i` inn, `o` well, `j` hops farm, and `K` keep. Thus `f` is ambiguous between a wheat farm and farmland. The map character alone is not a complete building-placement test; the driver also checks units and other conditions.

`ascii_map(x0=0, y0=0, x1=399, y1=399)` returns newline-separated rows for an inclusive rectangle. Coordinates must be integers within the map, with lower bounds no greater than upper bounds. Building lookup happens before terrain checks, and `B` also covers unrecognized building names. This is a terrain/building display, not a unit display.
