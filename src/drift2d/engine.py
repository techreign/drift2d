"""The Game class: main loop, fixed timestep, ties everything together."""

from __future__ import annotations
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import pygame

from .scene import SceneManager
from .entity import World
from .input import Input
from .renderer import Camera, Renderer
from .audio import Audio
from .physics import update_physics
from .animation import update_animations  # noqa: E402


class Game:
    """
    Main entry point. Create a Game, register scenes, call run().

    Usage:
        game = Game()
        game.scenes.register("main", MyScene())
        game.run("main")

    Or load from game.toml:
        game = Game.from_project("path/to/game/")
    """

    def __init__(
        self,
        title: str = "Drift Game",
        width: int = 800,
        height: int = 600,
        fps: int = 60,
        bg_color: tuple = (20, 20, 30),
        asset_root: Path | None = None,
        gravity: float = 980.0,
        pixel_perfect: bool = False,
    ):
        pygame.init()
        pygame.mixer.init()

        self.title = title
        self.width = width
        self.height = height
        self.fps = fps
        self.bg_color = bg_color
        self.gravity = gravity
        self.pixel_perfect = pixel_perfect
        self.running = False
        self.debug = False
        self.dev: "DevLoop | None" = None  # set via enable_dev()
        self.autoplay: "AutoPlayer | None" = None  # set via enable_autoplay()

        # Core systems
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)

        self.clock = pygame.time.Clock()
        self.world = World()
        self.input = Input()
        self.camera = Camera(width, height)
        self.renderer = Renderer(self.screen, self.camera, asset_root or Path("assets"))
        self.audio = Audio(asset_root or Path("assets"))
        self.scenes = SceneManager()
        self.scenes.game = self

        # Frame data
        self.dt: float = 0.0
        self.frame_count: int = 0
        self.time: float = 0.0

    @classmethod
    def from_project(cls, project_path: str = ".") -> Game:
        """Load game config from game.toml in the project directory."""
        root = Path(project_path).resolve()
        config_path = root / "game.toml"

        config = {}
        if config_path.exists():
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

        game_cfg = config.get("game", {})
        window_cfg = config.get("window", {})
        physics_cfg = config.get("physics", {})

        game = cls(
            title=game_cfg.get("title", "Drift Game"),
            width=window_cfg.get("width", 800),
            height=window_cfg.get("height", 600),
            fps=window_cfg.get("fps", 60),
            bg_color=tuple(window_cfg.get("bg_color", [20, 20, 30])),
            asset_root=root / "assets",
            gravity=physics_cfg.get("gravity", 980.0),
            pixel_perfect=window_cfg.get("pixel_perfect", False),
        )

        # Load input bindings
        input_cfg = config.get("input", {})
        for action, keys in input_cfg.items():
            key_codes = [getattr(pygame, f"K_{k}", None) for k in keys]
            key_codes = [k for k in key_codes if k is not None]
            if key_codes:
                game.input.bind(action, key_codes)

        return game

    def enable_autoplay(self):
        """Enable AI autoplay — bot plays the game for testing."""
        from .autoplay import AutoPlayer

        self.autoplay = AutoPlayer(self)
        self.autoplay.enable()

    def enable_dev(
        self,
        output_dir: str = ".drift-dev",
        screenshot_interval: float = 3.0,
        watch_dirs: list[str] | None = None,
    ):
        """Enable the dev loop — Claude watches the game live."""
        from .devloop import DevLoop

        self.dev = DevLoop(self, output_dir=output_dir)
        self.dev.screenshot_interval = screenshot_interval
        if watch_dirs:
            for d in watch_dirs:
                self.dev.watch_directory(Path(d))

    def run(self, start_scene: str | None = None):
        """Start the game loop."""
        if start_scene:
            self.scenes.switch(start_scene)

        self.running = True
        while self.running:
            self.dt = self.clock.tick(self.fps) / 1000.0
            self.dt = min(self.dt, 0.05)  # cap to avoid spiral of death
            self.time += self.dt
            self.frame_count += 1

            # AutoPlay (inject synthetic input before processing events)
            if self.autoplay:
                self.autoplay.update(self.dt)

            # Events
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                    break

            self.input.update(events)

            # Flush entity adds/removes from last frame
            self.world.flush()

            # Update current scene
            scene = self.scenes.current
            if scene:
                scene.update(self.dt)

            # Physics
            collisions = update_physics(self.world, self.dt, self.gravity)
            if scene:
                for col in collisions:
                    scene.on_collision(col)

            # Animations
            update_animations(self.world, self.dt)

            # Camera
            self.camera.update(self.dt)

            # Draw
            self.screen.fill(self.bg_color)
            if scene:
                scene.draw()

            # Auto-draw entities (skip if scene handles its own rendering)
            if not getattr(scene, "custom_draw", False):
                self.renderer.draw_entities(self.world.query())

            # Debug overlay
            if self.debug:
                self._draw_debug()

            # Dev loop (screenshots, state dump, hot reload)
            if self.dev:
                self.dev.update(self.dt)

            pygame.display.flip()

        pygame.quit()

    def quit(self):
        self.running = False

    def _draw_debug(self):
        fps_text = f"FPS: {self.clock.get_fps():.0f}  Entities: {self.world.count}"
        self.renderer.draw_text(fps_text, 4, 4, color=(0, 255, 0), size=16)
