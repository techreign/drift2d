# The Dev Loop — AI-Assisted Game Development

The Dev Loop is what makes Drift2D different from every other game engine. It creates a live feedback loop between your running game and Claude.

## How It Works

```
Game Running ──> Screenshots + State JSON ──> Claude reads
     ^                                            │
     │                                            │
     └──── Hot reload <── Claude edits code ──────┘
```

## Setup

```python
game = Game.from_project(".")
game.enable_dev(
    output_dir=".drift-dev",      # where to write data
    screenshot_interval=3.0,       # seconds between captures
    watch_dirs=["scenes"],         # directories to watch for changes
)
game.run("main")
```

## What Gets Captured

### state.json

Updated every screenshot interval:

```json
{
  "fps": 60.2,
  "frame_count": 1234,
  "game_time": 20.5,
  "entity_count": 15,
  "player_x": 450.0,
  "player_y": 300.0,
  "player_vx": 120.0,
  "player_vy": -200.0,
  "current_scene": "level_1",
  "avg_fps": 59.8,
  "min_fps": 52.0,
  "deaths": [
    {"x": 450, "y": 600, "time": 12.3, "cause": "fell_off_map"}
  ],
  "collectibles_gathered": 5,
  "enemies_killed": 2,
  "issues": [
    "Player died 3x near (450, 320) in 30s — possible difficulty spike"
  ]
}
```

### Screenshots

Rolling window of PNGs in `.drift-dev/screenshots/`:
- `latest.png` — always the most recent frame
- `frame_0001.png` through `frame_0020.png` — rolling history

### events.log

Append-only log:
```
[12.3s] DEATH at (450, 600) cause=fell_off_map
[15.0s] HOT RELOAD — files changed, reloading scenes
[20.0s] CLAUDE: Widened platform at x=400
```

## Hot Reload

When you edit a `.py` file in a watched directory, the engine:

1. Detects the file modification (checked every 1 second)
2. Reloads the Python module
3. Re-instantiates the current scene class
4. Transfers state (lives, score, level number) to the new instance
5. Calls `enter()` on the new scene

The game never stops running.

## Commands

Claude can write to `.drift-dev/commands.json` to control the game:

```json
{"action": "screenshot"}
{"action": "reload"}
{"action": "set_player_pos", "x": 100, "y": 200}
{"action": "log", "message": "Testing new platform layout"}
```

The file is consumed (deleted) after processing.

## Auto-Detected Issues

The Dev Loop automatically flags:
- **FPS drops** — "FPS dropped to 42 — possible performance issue"
- **Death clusters** — "Player died 4x near (450, 320) in 30s — possible difficulty spike"
- More detectors can be added in `devloop.py`

## Logging Game Events

In your scene code, log events for analysis:

```python
def _die(self, transform, cause="unknown"):
    if self.game.dev:
        self.game.dev.log_death(transform.position.x, transform.position.y, cause)

def _collect_item(self):
    if self.game.dev:
        self.game.dev.log_collectible()

def _kill_enemy(self):
    if self.game.dev:
        self.game.dev.log_enemy_kill()
```

## AutoPlay

Enable a bot to play the game automatically:

```python
game.enable_autoplay()
```

The bot:
- Moves toward the level exit (door)
- Jumps over gaps and walls
- Avoids/stomps enemies
- Collects nearby items
- Auto-presses through menus
- Uses barrels when nearby
- Steers toward platforms when falling

It's intentionally imperfect — a perfect bot wouldn't find the problems human players hit.
