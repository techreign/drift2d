"""Input system with action mapping. No raw keycodes in game logic."""

from __future__ import annotations
import pygame
from .utils import Vec2


# Default action map — games override this in game.toml
_DEFAULT_ACTIONS = {
    "move_left": [pygame.K_LEFT, pygame.K_a],
    "move_right": [pygame.K_RIGHT, pygame.K_d],
    "move_up": [pygame.K_UP, pygame.K_w],
    "move_down": [pygame.K_DOWN, pygame.K_s],
    "jump": [pygame.K_SPACE],
    "action": [pygame.K_z, pygame.K_RETURN],
    "cancel": [pygame.K_x, pygame.K_ESCAPE],
}


class Input:
    """Stateful input handler. Tracks pressed/just_pressed/just_released."""

    def __init__(self):
        self.actions: dict[str, list[int]] = dict(_DEFAULT_ACTIONS)
        self._pressed: set[int] = set()
        self._just_pressed: set[int] = set()
        self._just_released: set[int] = set()
        self._mouse_pos: tuple[int, int] = (0, 0)
        self._mouse_buttons: tuple[bool, ...] = (False, False, False)
        self._mouse_just_pressed: set[int] = set()

    def bind(self, action: str, keys: list[int]):
        self.actions[action] = keys

    def update(self, events: list[pygame.event.Event]):
        self._just_pressed.clear()
        self._just_released.clear()
        self._mouse_just_pressed.clear()

        for event in events:
            if event.type == pygame.KEYDOWN:
                self._pressed.add(event.key)
                self._just_pressed.add(event.key)
            elif event.type == pygame.KEYUP:
                self._pressed.discard(event.key)
                self._just_released.add(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._mouse_just_pressed.add(event.button)

        self._mouse_pos = pygame.mouse.get_pos()
        self._mouse_buttons = pygame.mouse.get_pressed()

    def is_action_pressed(self, action: str) -> bool:
        keys = self.actions.get(action, [])
        return any(k in self._pressed for k in keys)

    def is_action_just_pressed(self, action: str) -> bool:
        keys = self.actions.get(action, [])
        return any(k in self._just_pressed for k in keys)

    def is_action_just_released(self, action: str) -> bool:
        keys = self.actions.get(action, [])
        return any(k in self._just_released for k in keys)

    def get_axis(self, negative: str, positive: str) -> float:
        val = 0.0
        if self.is_action_pressed(negative):
            val -= 1.0
        if self.is_action_pressed(positive):
            val += 1.0
        return val

    def get_vector(self) -> Vec2:
        return Vec2(
            self.get_axis("move_left", "move_right"),
            self.get_axis("move_up", "move_down"),
        )

    @property
    def mouse_pos(self) -> Vec2:
        return Vec2(*self._mouse_pos)

    def is_mouse_pressed(self, button: int = 1) -> bool:
        idx = button - 1
        if 0 <= idx < len(self._mouse_buttons):
            return self._mouse_buttons[idx]
        return False

    def is_mouse_just_pressed(self, button: int = 1) -> bool:
        return button in self._mouse_just_pressed
