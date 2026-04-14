"""Rendering: camera, sprite drawing, shape helpers, text."""

from __future__ import annotations
from pathlib import Path
import pygame
from .utils import Vec2
from .entity import Entity, Transform, Sprite


class Camera:
    """2D camera with position and optional smoothing."""

    def __init__(self, width: int, height: int):
        self.position = Vec2()
        self.width = width
        self.height = height
        self.zoom: float = 1.0
        self._target: Entity | None = None
        self._smoothing: float = 5.0

    def follow(self, entity: Entity, smoothing: float = 5.0):
        self._target = entity
        self._smoothing = smoothing

    def update(self, dt: float):
        if self._target and self._target.has(Transform):
            target_pos = self._target.get(Transform).position
            center = Vec2(target_pos.x - self.width / 2, target_pos.y - self.height / 2)
            t = min(1.0, self._smoothing * dt)
            self.position += (center - self.position) * t

    def world_to_screen(self, pos: Vec2) -> Vec2:
        return Vec2(
            (pos.x - self.position.x) * self.zoom,
            (pos.y - self.position.y) * self.zoom,
        )

    def screen_to_world(self, pos: Vec2) -> Vec2:
        return Vec2(
            pos.x / self.zoom + self.position.x,
            pos.y / self.zoom + self.position.y,
        )


class Renderer:
    """Wraps pygame drawing with camera awareness."""

    def __init__(self, screen: pygame.Surface, camera: Camera, asset_root: Path):
        self.screen = screen
        self.camera = camera
        self.asset_root = asset_root
        self._sprite_cache: dict[str, pygame.Surface] = {}
        self._font_cache: dict[tuple[str | None, int], pygame.Font] = {}

    def _load_sprite(self, path: str) -> pygame.Surface:
        if path not in self._sprite_cache:
            full_path = self.asset_root / "sprites" / path
            if full_path.exists():
                self._sprite_cache[path] = pygame.image.load(
                    str(full_path)
                ).convert_alpha()
            else:
                # Generate a colored placeholder
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                surf.fill((255, 0, 255, 200))
                self._sprite_cache[path] = surf
        return self._sprite_cache[path]

    def _get_font(self, name: str | None = None, size: int = 24) -> pygame.Font:
        key = (name, size)
        if key not in self._font_cache:
            self._font_cache[key] = pygame.font.SysFont(name, size)
        return self._font_cache[key]

    def draw_entities(self, entities):
        """Draw all entities with Sprite+Transform, sorted by layer."""
        drawables = []
        for entity in entities:
            sprite = entity.get(Sprite)
            transform = entity.get(Transform)
            if sprite and transform and sprite.visible:
                drawables.append((sprite.layer, entity))

        drawables.sort(key=lambda x: x[0])

        for _, entity in drawables:
            self._draw_entity(entity)

    def _draw_entity(self, entity: Entity):
        transform = entity.get(Transform)
        sprite = entity.get(Sprite)
        screen_pos = self.camera.world_to_screen(transform.position)

        if sprite.image:
            surf = self._load_sprite(sprite.image)
            # Scale if needed
            target_w = int(sprite.width * transform.scale.x * self.camera.zoom)
            target_h = int(sprite.height * transform.scale.y * self.camera.zoom)
            if (target_w, target_h) != surf.get_size():
                surf = pygame.transform.scale(surf, (target_w, target_h))
            # Flip
            if sprite.flip_x or sprite.flip_y:
                surf = pygame.transform.flip(surf, sprite.flip_x, sprite.flip_y)
            # Rotate
            if transform.rotation != 0:
                surf = pygame.transform.rotate(surf, -transform.rotation)
            rect = surf.get_rect(center=screen_pos.as_int_tuple())
            self.screen.blit(surf, rect)
        else:
            # No image — draw colored rect
            w = int(sprite.width * transform.scale.x * self.camera.zoom)
            h = int(sprite.height * transform.scale.y * self.camera.zoom)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = screen_pos.as_int_tuple()
            pygame.draw.rect(self.screen, sprite.color, rect)

    # ── Shape helpers (world-space) ──

    def draw_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        color=(255, 255, 255),
        width: int = 0,
    ):
        sp = self.camera.world_to_screen(Vec2(x, y))
        pygame.draw.rect(
            self.screen,
            color,
            pygame.Rect(
                int(sp.x),
                int(sp.y),
                int(w * self.camera.zoom),
                int(h * self.camera.zoom),
            ),
            width,
        )

    def draw_circle(
        self, x: float, y: float, radius: float, color=(255, 255, 255), width: int = 0
    ):
        sp = self.camera.world_to_screen(Vec2(x, y))
        pygame.draw.circle(
            self.screen, color, sp.as_int_tuple(), int(radius * self.camera.zoom), width
        )

    def draw_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color=(255, 255, 255),
        width: int = 1,
    ):
        sp1 = self.camera.world_to_screen(Vec2(x1, y1))
        sp2 = self.camera.world_to_screen(Vec2(x2, y2))
        pygame.draw.line(
            self.screen, color, sp1.as_int_tuple(), sp2.as_int_tuple(), width
        )

    # ── Screen-space helpers (UI) ──

    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        color=(255, 255, 255),
        size: int = 24,
        font_name: str | None = None,
    ):
        font = self._get_font(font_name, size)
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def draw_screen_rect(
        self, x: int, y: int, w: int, h: int, color=(255, 255, 255), width: int = 0
    ):
        pygame.draw.rect(self.screen, color, pygame.Rect(x, y, w, h), width)
