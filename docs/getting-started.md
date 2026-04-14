# Getting Started with Drift2D

## Installation

```bash
pip install drift2d
```

Or from source:
```bash
git clone https://github.com/shoaib/drift2d.git
cd drift2d
pip install -e .
```

## Create Your First Game

```bash
drift new my-game
cd my-game
```

This creates:
```
my-game/
  game.toml        # config
  run.py            # entry point
  scenes/
    main.py         # your game logic
  entities/         # YAML entity definitions
  assets/
    sprites/
    sounds/
```

## Run It

```bash
drift run
```

Or directly:
```bash
python run.py
```

You'll see a window with a blue square you can move with WASD/arrows.

## How It Works

### Scenes

Every screen in your game is a Scene. The engine calls your hooks:

```python
from drift2d import Scene, Entity, Transform, Sprite, Vec2

class MainScene(Scene):
    def enter(self):
        """Called once when this scene becomes active."""
        pass

    def exit(self):
        """Called when leaving this scene."""
        pass

    def update(self, dt: float):
        """Called every frame. dt = seconds since last frame."""
        pass

    def draw(self):
        """Called every frame after update."""
        pass

    def on_collision(self, collision):
        """Called for each collision this frame."""
        pass
```

### Entities

Entities are just IDs with components attached:

```python
player = Entity("player")
player.add(Transform(position=Vec2(100, 200)))
player.add(Sprite(color=(100, 200, 255), width=32, height=32))
player.add(RigidBody(gravity_scale=1.0))
player.add(BoxCollider(width=32, height=32))
self.game.world.spawn(player)
```

Query entities by component:
```python
for entity in self.game.world.query(Transform, Sprite):
    pos = entity.get(Transform).position
```

Find by name or tag:
```python
player = self.game.world.find("player")
enemies = list(self.game.world.query_tag("enemy"))
```

### Input

Use actions, not keycodes:

```python
# Movement vector from WASD/arrows
direction = self.game.input.get_vector()

# Single axis
horizontal = self.game.input.get_axis("move_left", "move_right")

# Button checks
if self.game.input.is_action_just_pressed("jump"):
    # just this frame
if self.game.input.is_action_pressed("jump"):
    # held down
```

### Scene Switching

```python
# Register scenes
game.scenes.register("menu", MenuScene())
game.scenes.register("gameplay", GameScene())

# Switch (replaces current)
game.scenes.switch("gameplay")

# Push (stacks, like a pause menu)
game.scenes.push("pause")
game.scenes.pop()  # resume previous
```

### Config (game.toml)

```toml
[game]
title = "My Game"

[window]
width = 800
height = 600
fps = 60
bg_color = [20, 20, 30]

[physics]
gravity = 980.0

[input]
attack = ["z", "RETURN"]
```

## Enable the Dev Loop

Add two lines to your run.py:

```python
game = Game.from_project(".")
game.enable_dev(watch_dirs=["scenes"])  # Claude watches
game.enable_autoplay()                  # Bot plays
game.run("main")
```

While the game runs, Claude can:
1. Read `.drift-dev/state.json` for player position, FPS, death log
2. View `.drift-dev/screenshots/latest.png` for visual state
3. Edit scene files — they hot-reload automatically
4. Write `.drift-dev/commands.json` to teleport the player, force screenshots, etc.

## Next Steps

- Look at `examples/` for complete games
- Read the [Dev Loop Guide](dev-loop.md) for advanced AI-assisted development
- Read the [Tilemap Guide](tilemaps.md) for level design
