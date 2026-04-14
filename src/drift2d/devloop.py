"""
Dev Loop: Claude watches the game live.

Captures screenshots, dumps game state to JSON, watches for code changes,
and hot-reloads scenes without restarting. This is the core differentiator.

Usage:
    game = Game.from_project(".")
    dev = DevLoop(game, screenshot_interval=3.0)
    # In your game loop, dev.update(dt) is called automatically when enabled
"""

from __future__ import annotations
import json
import time
import importlib
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import Game

import pygame


@dataclass
class DeathEvent:
    x: float
    y: float
    time: float
    cause: str = ""


@dataclass
class DevState:
    """Full game state snapshot for Claude to analyze."""

    timestamp: float = 0.0
    fps: float = 0.0
    frame_count: int = 0
    game_time: float = 0.0
    entity_count: int = 0
    screenshot_path: str = ""

    # Player
    player_x: float = 0.0
    player_y: float = 0.0
    player_vx: float = 0.0
    player_vy: float = 0.0
    player_on_ground: bool = False

    # Scene
    current_scene: str = ""
    scene_file: str = ""

    # Performance
    avg_fps: float = 0.0
    min_fps: float = 999.0
    frame_times: list[float] = field(default_factory=list)

    # Events
    deaths: list[dict] = field(default_factory=list)
    collectibles_gathered: int = 0
    enemies_killed: int = 0

    # Issues detected
    issues: list[str] = field(default_factory=list)


class DevLoop:
    """
    The live AI feedback loop. Captures game state and screenshots,
    watches files for changes, and hot-reloads scenes.
    """

    def __init__(self, game: Game, output_dir: str = ".drift-dev"):
        self.game = game
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Screenshot config
        self.screenshot_interval = 3.0
        self._screenshot_timer = 0.0
        self._screenshot_count = 0

        # State tracking
        self.state = DevState()
        self._death_log: list[DeathEvent] = []
        self._fps_samples: list[float] = []
        self._collectibles = 0
        self._enemies_killed = 0

        # Hot reload
        self._file_mtimes: dict[str, float] = {}
        self._reload_check_interval = 1.0
        self._reload_timer = 0.0
        self._scene_modules: dict[str, str] = {}  # scene_name -> module_name

        # Watch the scenes directory
        self._watch_dirs: list[Path] = []

        # Write initial instruction file for Claude
        self._write_claude_instructions()

    def _write_claude_instructions(self):
        """Write a file that tells Claude how to interact with the dev loop."""
        instructions = {
            "what_is_this": "Drift2D Dev Loop — Claude watches the game live",
            "screenshot_dir": str(self.output_dir / "screenshots"),
            "state_file": str(self.output_dir / "state.json"),
            "event_log": str(self.output_dir / "events.log"),
            "how_to_use": [
                "1. Read state.json for current game state",
                "2. Look at screenshots/ for visual state",
                "3. Edit scene .py files — they hot-reload automatically",
                "4. Write to commands.json to trigger actions",
                "5. Read issues[] in state.json for auto-detected problems",
            ],
            "commands": {
                "screenshot": "Take an immediate screenshot",
                "reload": "Force reload all scenes",
                "set_player_pos": {"x": 0, "y": 0},
                "set_entity": {"name": "str", "property": "str", "value": "any"},
                "pause": "Pause the game",
                "resume": "Resume the game",
            },
        }
        (self.output_dir / "README.json").write_text(json.dumps(instructions, indent=2))

    def watch_directory(self, path: Path):
        """Add a directory to watch for file changes."""
        self._watch_dirs.append(Path(path))
        self._scan_mtimes()

    def register_scene_module(self, scene_name: str, module_name: str):
        """Register which module a scene class lives in, for hot reload."""
        self._scene_modules[scene_name] = module_name

    def log_death(self, x: float, y: float, cause: str = ""):
        """Log a player death for pattern analysis."""
        event = DeathEvent(x=x, y=y, time=self.game.time, cause=cause)
        self._death_log.append(event)

        # Append to event log
        with open(self.output_dir / "events.log", "a") as f:
            f.write(
                f"[{self.game.time:.1f}s] DEATH at ({x:.0f}, {y:.0f}) cause={cause}\n"
            )

        # Detect repeated deaths
        recent = [d for d in self._death_log if self.game.time - d.time < 30]
        positions = [(d.x, d.y) for d in recent]
        for pos in set(positions):
            count = positions.count(pos)
            if count >= 3:
                self.state.issues.append(
                    f"Player died {count}x near ({pos[0]:.0f}, {pos[1]:.0f}) in 30s — possible difficulty spike"
                )

    def log_collectible(self):
        self._collectibles += 1

    def log_enemy_kill(self):
        self._enemies_killed += 1

    def update(self, dt: float):
        """Called every frame by the engine."""
        # Track FPS
        current_fps = self.game.clock.get_fps()
        self._fps_samples.append(current_fps)
        if len(self._fps_samples) > 300:
            self._fps_samples = self._fps_samples[-300:]

        # Screenshot timer
        self._screenshot_timer += dt
        if self._screenshot_timer >= self.screenshot_interval:
            self._screenshot_timer = 0
            self._take_screenshot()
            self._dump_state()

        # Hot reload check
        self._reload_timer += dt
        if self._reload_timer >= self._reload_check_interval:
            self._reload_timer = 0
            self._check_hot_reload()

        # Check for commands from Claude
        self._process_commands()

        # Auto-detect issues
        self._detect_issues()

    def _take_screenshot(self):
        """Capture the current frame."""
        ss_dir = self.output_dir / "screenshots"
        ss_dir.mkdir(exist_ok=True)

        # Keep a rolling window of screenshots (last 20)
        filename = f"frame_{self._screenshot_count:04d}.png"
        path = ss_dir / filename
        pygame.image.save(self.game.screen, str(path))

        # Also save as "latest.png" for easy access
        latest = ss_dir / "latest.png"
        pygame.image.save(self.game.screen, str(latest))

        self.state.screenshot_path = str(latest)
        self._screenshot_count += 1

        # Clean old screenshots (keep last 20)
        if self._screenshot_count > 20:
            old = ss_dir / f"frame_{self._screenshot_count - 21:04d}.png"
            if old.exists():
                old.unlink()

    def _dump_state(self):
        """Write current game state to JSON."""
        self.state.timestamp = time.time()
        self.state.fps = self.game.clock.get_fps()
        self.state.frame_count = self.game.frame_count
        self.state.game_time = self.game.time
        self.state.entity_count = self.game.world.count

        # Player state
        player = self.game.world.find("player")
        if player:
            from .entity import Transform, RigidBody

            t = player.get(Transform)
            rb = player.get(RigidBody)
            if t:
                self.state.player_x = round(t.position.x, 1)
                self.state.player_y = round(t.position.y, 1)
            if rb:
                self.state.player_vx = round(rb.velocity.x, 1)
                self.state.player_vy = round(rb.velocity.y, 1)

        # Scene info
        scenes = self.game.scenes
        if scenes._stack:
            self.state.current_scene = scenes._stack[-1]

        # FPS stats
        if self._fps_samples:
            self.state.avg_fps = round(
                sum(self._fps_samples) / len(self._fps_samples), 1
            )
            self.state.min_fps = round(min(self._fps_samples), 1)

        # Events
        self.state.deaths = [
            {"x": d.x, "y": d.y, "time": round(d.time, 1), "cause": d.cause}
            for d in self._death_log[-20:]  # last 20 deaths
        ]
        self.state.collectibles_gathered = self._collectibles
        self.state.enemies_killed = self._enemies_killed

        # Write state
        state_dict = asdict(self.state)
        state_dict.pop("frame_times", None)  # don't dump raw frame times
        (self.output_dir / "state.json").write_text(json.dumps(state_dict, indent=2))

    def _detect_issues(self):
        """Auto-detect common problems."""
        self.state.issues.clear()

        # Low FPS
        if self._fps_samples and len(self._fps_samples) > 30:
            recent_avg = sum(self._fps_samples[-30:]) / 30
            if recent_avg < 45:
                self.state.issues.append(
                    f"FPS dropped to {recent_avg:.0f} — possible performance issue"
                )

        # Player stuck (not moving for a while)
        # This is tracked frame-to-frame in the state

    def _scan_mtimes(self):
        """Record modification times of all watched files."""
        for watch_dir in self._watch_dirs:
            if not watch_dir.exists():
                continue
            for py_file in watch_dir.rglob("*.py"):
                self._file_mtimes[str(py_file)] = py_file.stat().st_mtime

    def _check_hot_reload(self):
        """Check if any watched files changed, reload if so."""
        changed = False
        for watch_dir in self._watch_dirs:
            if not watch_dir.exists():
                continue
            for py_file in watch_dir.rglob("*.py"):
                path_str = str(py_file)
                mtime = py_file.stat().st_mtime
                if path_str in self._file_mtimes:
                    if mtime > self._file_mtimes[path_str]:
                        changed = True
                        self._file_mtimes[path_str] = mtime
                        self._reload_module(py_file)
                else:
                    self._file_mtimes[path_str] = mtime

        if changed:
            with open(self.output_dir / "events.log", "a") as f:
                f.write(
                    f"[{self.game.time:.1f}s] HOT RELOAD — files changed, reloading scenes\n"
                )

    def _reload_module(self, py_file: Path):
        """Reload a specific Python module."""
        # Find module name from file path
        for mod_name, mod in list(sys.modules.items()):
            if hasattr(mod, "__file__") and mod.__file__:
                if Path(mod.__file__).resolve() == py_file.resolve():
                    try:
                        importlib.reload(mod)
                        # Re-instantiate the current scene if it's from this module
                        self._reinstantiate_scene(mod_name, mod)
                    except Exception as e:
                        with open(self.output_dir / "events.log", "a") as f:
                            f.write(f"[{self.game.time:.1f}s] RELOAD ERROR: {e}\n")
                    break

    def _reinstantiate_scene(self, module_name: str, module):
        """After reloading a module, reinstantiate the active scene from it."""
        current = self.game.scenes.current
        if not current:
            return

        current_class_name = type(current).__name__
        # Check if the reloaded module has this class
        new_class = getattr(module, current_class_name, None)
        if new_class and new_class is not type(current):
            # Transfer state we want to keep
            old_attrs = {}
            for attr in ["lives", "bananas", "score", "level_num"]:
                if hasattr(current, attr):
                    old_attrs[attr] = getattr(current, attr)

            # Create new instance
            new_scene = new_class(
                **{
                    k: v
                    for k, v in old_attrs.items()
                    if k in new_class.__init__.__code__.co_varnames
                }
            )

            # Register and switch
            scene_name = self.game.scenes._stack[-1]
            self.game.scenes._scenes[scene_name] = new_scene
            new_scene.game = self.game
            new_scene.enter()

    def _process_commands(self):
        """Check for commands from Claude via commands.json."""
        cmd_file = self.output_dir / "commands.json"
        if not cmd_file.exists():
            return

        try:
            commands = json.loads(cmd_file.read_text())
            cmd_file.unlink()  # consume the commands

            for cmd in commands if isinstance(commands, list) else [commands]:
                action = cmd.get("action", "")

                if action == "screenshot":
                    self._take_screenshot()
                    self._dump_state()
                elif action == "reload":
                    for watch_dir in self._watch_dirs:
                        for py_file in watch_dir.rglob("*.py"):
                            self._reload_module(py_file)
                elif action == "set_player_pos":
                    player = self.game.world.find("player")
                    if player:
                        from .entity import Transform

                        t = player.get(Transform)
                        if t:
                            t.position.x = cmd.get("x", t.position.x)
                            t.position.y = cmd.get("y", t.position.y)
                elif action == "log":
                    with open(self.output_dir / "events.log", "a") as f:
                        f.write(
                            f"[{self.game.time:.1f}s] CLAUDE: {cmd.get('message', '')}\n"
                        )

        except (json.JSONDecodeError, KeyError):
            pass
