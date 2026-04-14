"""Scene system: each screen/level is a Scene. SceneManager handles transitions."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import Game


class Scene:
    """Base class for all scenes. Override the hooks you need."""

    def __init__(self):
        self.game: Game | None = None  # set by SceneManager

    def enter(self):
        """Called when this scene becomes active."""
        pass

    def exit(self):
        """Called when leaving this scene."""
        pass

    def update(self, dt: float):
        """Called every frame. dt is seconds since last frame."""
        pass

    def draw(self):
        """Called every frame after update."""
        pass

    def on_collision(self, collision):
        """Called for each collision this frame."""
        pass


class SceneManager:
    """Stack-based scene management. Push/pop/switch scenes."""

    def __init__(self):
        self._scenes: dict[str, Scene] = {}
        self._stack: list[str] = []
        self.game: Game | None = None

    def register(self, name: str, scene: Scene):
        self._scenes[name] = scene

    def switch(self, name: str):
        """Replace current scene with a new one."""
        if self._stack:
            current = self._scenes.get(self._stack[-1])
            if current:
                current.exit()
            self._stack.pop()

        self._push_scene(name)

    def push(self, name: str):
        """Push a scene on top (pause current)."""
        self._push_scene(name)

    def pop(self):
        """Pop current scene, resume previous."""
        if self._stack:
            current = self._scenes.get(self._stack[-1])
            if current:
                current.exit()
            self._stack.pop()

        if self._stack:
            resumed = self._scenes.get(self._stack[-1])
            if resumed:
                resumed.enter()

    def _push_scene(self, name: str):
        scene = self._scenes.get(name)
        if not scene:
            raise ValueError(
                f"Scene '{name}' not registered. Available: {list(self._scenes.keys())}"
            )
        scene.game = self.game
        self._stack.append(name)
        scene.enter()

    @property
    def current(self) -> Scene | None:
        if not self._stack:
            return None
        return self._scenes.get(self._stack[-1])
