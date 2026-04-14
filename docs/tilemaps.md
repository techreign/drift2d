# Tilemaps — Text-Based Level Design

Drift2D uses plain text files for level design. Every character in the file maps to a tile type. This means Claude can read, edit, and generate levels as easily as editing a string.

## Basic Usage

```python
from drift2d import Tilemap, TileDef

tilemap = Tilemap(tile_size=32)

# Define tile types
tilemap.define("G", TileDef(char="G", color=(60, 120, 45), solid=True))
tilemap.define("W", TileDef(char="W", color=(80, 80, 80), solid=True))

# Load from file
tilemap.load_from_file("levels/level1.txt")

# Or from a string
tilemap.load_from_string("""
................
..P.............
GGGG............
......GGGG......
..............D.
GGGGGGGGGGGGGGGG
""")
```

## Level File Format

Each character is one tile. Dots and spaces are empty/air.

```
WWWWWWWWWWWWWWWW
W..............W
W..P...........W
W..GGGG........W
W..........GGG.W
W..............W
W........E...D.W
WGGGGGGGGGGGGGW
WWWWWWWWWWWWWWWW
```

Common tile conventions:
- `G` — ground/platform (solid)
- `W` — wall (solid)
- `P` — player spawn point
- `E` — enemy spawn
- `B` — collectible (banana, coin, etc.)
- `b` — barrel/launcher
- `D` — door/exit
- `T` — target/goal
- `.` — empty air

## Finding Special Tiles

After loading, find spawn points and object positions:

```python
# Returns list of (col, row) tuples
spawns = tilemap.find_tiles("P")
enemies = tilemap.find_tiles("E")
bananas = tilemap.find_tiles("B")

# Convert to world coordinates
for col, row in enemies:
    world_pos = tilemap.tile_to_world(col, row)
    # spawn an enemy entity at world_pos
```

## Collision Detection

```python
from drift2d.utils import Rect

# Check if a rectangle overlaps any solid tiles
player_rect = Rect(player.x - 16, player.y - 16, 32, 32)
hits = tilemap.collide_rect(player_rect)

if hits:
    # hits is a list of Rect objects for each solid tile hit
    for tile_rect in hits:
        # resolve collision...
```

## Coordinate Conversion

```python
# World position to tile coordinates
col, row = tilemap.world_to_tile(Vec2(150, 200))

# Tile coordinates to world position (top-left of tile)
world_pos = tilemap.tile_to_world(col, row)
# Add Vec2(tile_size/2, tile_size/2) for center of tile
```

## Modifying Tiles at Runtime

```python
# Change a tile
tilemap.set_tile(col, row, ".")  # remove a block

# Read a tile
char = tilemap.get_tile(col, row)  # returns "G", ".", etc.
```

## Rendering

```python
def draw(self):
    # Draw with camera offset
    self.tilemap.draw(self.game.screen, self.game.camera.position)
```

The tilemap pre-renders to a surface for performance. It rebuilds automatically when tiles change.

## Using Sprite Images

```python
tilemap.define("G", TileDef(
    char="G",
    color=(60, 120, 45),  # fallback color
    solid=True,
    image="grass.png",     # from assets/sprites/
))
tilemap._asset_root = Path("assets")  # set asset root for image loading
```

## Tips for AI-Friendly Level Design

1. **Keep levels under 60 columns wide** — fits in Claude's context easily
2. **Use consistent tile characters** across all levels
3. **One level per file** — `levels/level1.txt`, `levels/level2.txt`
4. **Bottom row should be solid** (unless you want fall-death pits)
5. **Mark spawn and exit clearly** with P and D
