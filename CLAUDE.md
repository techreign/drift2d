# Drift2D — Claude-First 2D Game Engine

## What is this?
A 2D game engine where every file is plain text, every convention is predictable, and the entire project fits in an AI context window. Built for solo devs who build with Claude.

## Tech Stack
- Python 3.10+
- pygame-ce (rendering, input, audio)
- PyYAML (entity definitions)
- Click (CLI)

## Project Structure
```
src/drift2d/
  __init__.py    — public API, re-exports everything
  engine.py      — Game class, main loop, fixed timestep
  scene.py       — Scene base class, SceneManager
  entity.py      — Entity, Component, World (ECS-lite)
  renderer.py    — Camera, draw helpers, sprite batching
  input.py       — Input singleton, action mapping
  physics.py     — AABB collisions, spatial grid
  audio.py       — Sound/music manager
  loader.py      — YAML entity/scene loader
  cli.py         — `drift` CLI commands
  utils.py       — Vec2, Timer, helpers
```

## Conventions
- Scenes live in `scenes/` as Python files, one class per file
- Entities defined in `entities/` as YAML files
- Assets in `assets/sprites/` and `assets/sounds/`
- Game config in `game.toml` at project root
- All coordinates are pixels, origin top-left
- Y-down coordinate system (standard screen coords)

## Commands
```bash
drift new <name>       # scaffold a new game
drift run              # run the game
drift build            # package for distribution
```

## Testing
```bash
cd ~/projects/drift2d
pip install -e ".[dev]"
python -m pytest tests/
```
