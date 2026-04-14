"""Lightweight particle system for juice: sparks, dust, explosions."""

from __future__ import annotations
from dataclasses import dataclass
import random
import math
import pygame
from .utils import Vec2


@dataclass
class ParticleConfig:
    """Configuration for a particle emitter."""

    count: int = 20
    lifetime: tuple[float, float] = (0.3, 1.0)
    speed: tuple[float, float] = (50.0, 150.0)
    direction: float = -90.0  # degrees, -90 = up
    spread: float = 360.0  # degrees of cone spread
    color: tuple = (255, 255, 255)
    color_end: tuple | None = None  # fade to this color
    size: tuple[float, float] = (2.0, 5.0)
    size_end: float = 0.0
    gravity: float = 0.0
    fade: bool = True


@dataclass
class _Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 1.0
    max_life: float = 1.0
    size: float = 3.0
    size_start: float = 3.0
    color: tuple = (255, 255, 255)


class ParticleEmitter:
    """Emits and manages a pool of particles."""

    def __init__(self, config: ParticleConfig | None = None):
        self.config = config or ParticleConfig()
        self._particles: list[_Particle] = []

    def emit(self, x: float, y: float, count: int | None = None):
        """Burst particles at position."""
        cfg = self.config
        n = count or cfg.count

        for _ in range(n):
            angle_deg = cfg.direction + random.uniform(-cfg.spread / 2, cfg.spread / 2)
            angle = math.radians(angle_deg)
            speed = random.uniform(*cfg.speed)
            lifetime = random.uniform(*cfg.lifetime)
            size = random.uniform(*cfg.size)

            self._particles.append(
                _Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=lifetime,
                    max_life=lifetime,
                    size=size,
                    size_start=size,
                    color=cfg.color,
                )
            )

    def update(self, dt: float):
        """Update all particles. Remove dead ones."""
        cfg = self.config
        alive = []
        for p in self._particles:
            p.life -= dt
            if p.life <= 0:
                continue

            p.vy += cfg.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt

            # Interpolate size
            t = 1.0 - (p.life / p.max_life)
            p.size = p.size_start + (cfg.size_end - p.size_start) * t

            alive.append(p)

        self._particles = alive

    def draw(self, screen: pygame.Surface, camera_offset: Vec2 = Vec2()):
        """Render all particles."""
        cfg = self.config
        for p in self._particles:
            t = 1.0 - (p.life / p.max_life)
            sx = int(p.x - camera_offset.x)
            sy = int(p.y - camera_offset.y)
            size = max(1, int(p.size))

            # Color interpolation
            if cfg.color_end:
                r = int(cfg.color[0] + (cfg.color_end[0] - cfg.color[0]) * t)
                g = int(cfg.color[1] + (cfg.color_end[1] - cfg.color[1]) * t)
                b = int(cfg.color[2] + (cfg.color_end[2] - cfg.color[2]) * t)
                color = (r, g, b)
            else:
                color = cfg.color

            # Alpha fade
            if cfg.fade:
                alpha = int(255 * (p.life / p.max_life))
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*color, alpha), (size, size), size)
                screen.blit(surf, (sx - size, sy - size))
            else:
                pygame.draw.circle(screen, color, (sx, sy), size)

    @property
    def alive(self) -> int:
        return len(self._particles)

    @property
    def is_done(self) -> bool:
        return len(self._particles) == 0
