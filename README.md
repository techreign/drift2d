# Drift2D

**The game engine that watches itself.** A 2D game engine built for AI-assisted development, where Claude can see the game running, find bugs, and fix them — all while the game is still playing.

## Why Drift2D?

Every other game engine treats AI as an afterthought. Drift2D was built from the ground up for the AI development loop:

- **Plain text everything** — scenes are Python, entities are YAML, levels are text files. No binary formats. Claude can read and modify every file in your project.
- **DevLoop** — while your game runs, Drift captures screenshots and game state to JSON every few seconds. Claude reads the data, spots issues, and edits code that hot-reloads without restarting.
- **AutoPlay** — a built-in bot plays your game automatically. Claude watches the bot, identifies death clusters, performance drops, and design problems, then fixes them live.
- **Convention over configuration** — every Drift project has the same structure. Claude never has to ask "where does this go?"

## Quick Start

```bash
pip install drift2d
drift new my-game
cd my-game
drift run
```

Or manually:

```python
from drift2d import Game, Scene, Entity, Transform, Sprite, Vec2

class MyScene(Scene):
    def enter(self):
        player = Entity("player")
        player.add(Transform(position=Vec2(400, 300)))
        player.add(Sprite(color=(100, 200, 255), width=32, height=32))
        self.game.world.spawn(player)

    def update(self, dt):
        player = self.game.world.find("player")
        if player:
            direction = self.game.input.get_vector()
            player.get(Transform).position += direction * 200 * dt

game = Game(title="My Game", width=800, height=600)
game.scenes.register("main", MyScene())
game.run("main")
```

## The Dev Loop

This is what makes Drift2D different. Enable it with one line:

```python
game = Game.from_project(".")
game.enable_dev(watch_dirs=["scenes"])
game.enable_autoplay()  # optional: bot plays for you
game.run("main")
```

While the game runs, Drift writes to `.drift-dev/`:

```
.drift-dev/
  state.json         # player pos, FPS, deaths, kills, issues
  screenshots/
    latest.png        # current frame
    frame_0001.png    # rolling history
  events.log          # deaths, hot reloads, commands
  commands.json       # Claude writes here to control the game
```

Claude reads `state.json`, sees that the player died 4 times at the same spot, edits the level file to widen a platform, and the game hot-reloads. No restart needed.

## Project Structure

Every Drift game follows the same layout:

```
my-game/
  game.toml           # window size, physics, input bindings
  run.py              # entry point
  scenes/
    main.py           # game logic (one class per scene)
  entities/
    player.yaml       # declarative entity definitions
  levels/
    level1.txt        # text-based tilemaps
  assets/
    sprites/
    sounds/
```

## Entities

Define entities in Python or YAML:

**Python:**
```python
player = Entity("player")
player.add(Transform(position=Vec2(100, 200)))
player.add(Sprite(color=(100, 200, 255), width=32, height=48))
player.add(RigidBody(gravity_scale=1.0))
player.add(BoxCollider(width=32, height=48))
game.world.spawn(player)
```

**YAML** (`entities/player.yaml`):
```yaml
name: player
tags: [player]
transform:
  position: [100, 200]
sprite:
  color: [100, 200, 255]
  width: 32
  height: 48
rigidbody:
  gravity_scale: 1.0
collider:
  width: 32
  height: 48
```

## Tilemaps

Levels are plain text files:

```
..............
..P...........
GGGG..........
......GGGG....
...........E..
..........GGG.
..............
..........D...
GGGGGGGGGGGGGG
```

Load and use them:

```python
from drift2d import Tilemap, TileDef

tilemap = Tilemap(tile_size=32)
tilemap.define("G", TileDef(char="G", color=(60, 120, 45), solid=True))
tilemap.load_from_file("levels/level1.txt")

# Collision detection
hits = tilemap.collide_rect(player_rect)
```

## Particles

Add juice with configurable particle emitters:

```python
from drift2d import ParticleEmitter, ParticleConfig

dust = ParticleEmitter(ParticleConfig(
    count=5, lifetime=(0.2, 0.5), speed=(20, 60),
    color=(100, 80, 50), size=(1.5, 3.0), gravity=80, fade=True,
))

# Emit at a position
dust.emit(player.x, player.y)

# Update and draw each frame
dust.update(dt)
dust.draw(screen, camera_offset)
```

## Input

Action-mapped input — no raw keycodes in game logic:

```python
# Built-in actions: move_left, move_right, move_up, move_down, jump, action, cancel
direction = game.input.get_vector()  # Vec2 from WASD/arrows
if game.input.is_action_just_pressed("jump"):
    player.velocity.y = -400
```

Custom bindings in `game.toml`:
```toml
[input]
attack = ["z", "RETURN"]
dash = ["LSHIFT"]
```

## Examples

| Example | Genre | Features shown |
|---------|-------|---------------|
| `examples/platformer/` | Platformer | Physics, collisions, YAML entities |
| `examples/topdown/` | Top-down | Tilemap, particles, enemy AI |
| `examples/pong/` | Arcade | Minimal game (~80 lines) |
| `examples/dkc/` | Platformer | Full game: 5 levels, DevLoop, AutoPlay |
| `examples/sokoban/` | Puzzle | Grid movement, undo, non-physics genre |

## API Reference

### Core
- `Game` — main loop, config loading, dev/autoplay integration
- `Scene` — base class with `enter()`, `exit()`, `update(dt)`, `draw()`, `on_collision()`
- `SceneManager` — stack-based scene transitions

### ECS
- `Entity` — ID + components bag
- `World` — entity container with `spawn()`, `despawn()`, `query()`, `find()`
- `Transform` — position, rotation, scale
- `Sprite` — image/color, size, layer, flip, visibility
- `RigidBody` — velocity, gravity, friction, kinematic flag
- `BoxCollider` — AABB collision with tag and solid flag
- `AnimationPlayer` — frame-based sprite animation

### Systems
- `Input` — action-mapped keyboard/mouse input
- `Camera` — smooth follow with zoom
- `Renderer` — sprites, shapes, text (all camera-aware)
- `Audio` — sound effects and music
- `Tilemap` — text-file levels with collision
- `ParticleEmitter` — configurable particle system

### Dev Tools
- `DevLoop` — screenshots, state JSON, hot reload, commands
- `AutoPlayer` — heuristic bot for autonomous playtesting

## Requirements

- Python 3.10+
- pygame-ce >= 2.4 (or pygame >= 2.5)
- PyYAML >= 6.0
- Click >= 8.0

## License

MIT
