"""Lightweight math and utility helpers."""

from __future__ import annotations
import math


class Vec2:
    """Simple 2D vector. No numpy dependency needed."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    # -- arithmetic --
    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vec2:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vec2:
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)

    # -- in-place --
    def __iadd__(self, other: Vec2) -> Vec2:
        self.x += other.x
        self.y += other.y
        return self

    def __isub__(self, other: Vec2) -> Vec2:
        self.x -= other.x
        self.y -= other.y
        return self

    def __imul__(self, scalar: float) -> Vec2:
        self.x *= scalar
        self.y *= scalar
        return self

    # -- comparison --
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vec2):
            return NotImplemented
        return math.isclose(self.x, other.x) and math.isclose(self.y, other.y)

    # -- properties --
    @property
    def length(self) -> float:
        return math.hypot(self.x, self.y)

    @property
    def normalized(self) -> Vec2:
        ln = self.length
        if ln == 0:
            return Vec2()
        return self / ln

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def distance_to(self, other: Vec2) -> float:
        return (other - self).length

    def copy(self) -> Vec2:
        return Vec2(self.x, self.y)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def as_int_tuple(self) -> tuple[int, int]:
        return (int(self.x), int(self.y))

    def __repr__(self) -> str:
        return f"Vec2({self.x:.1f}, {self.y:.1f})"


class Timer:
    """Simple countdown timer."""

    def __init__(self, duration: float, auto_start: bool = True):
        self.duration = duration
        self.remaining = duration if auto_start else 0.0
        self.running = auto_start

    def update(self, dt: float) -> bool:
        """Update timer. Returns True on the frame it finishes."""
        if not self.running:
            return False
        self.remaining -= dt
        if self.remaining <= 0:
            self.running = False
            self.remaining = 0.0
            return True
        return False

    def reset(self):
        self.remaining = self.duration
        self.running = True

    @property
    def done(self) -> bool:
        return not self.running and self.remaining <= 0

    @property
    def progress(self) -> float:
        if self.duration == 0:
            return 1.0
        return 1.0 - (self.remaining / self.duration)


class Rect:
    """Axis-aligned bounding box."""

    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = float(x)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def center(self) -> Vec2:
        return Vec2(self.x + self.w / 2, self.y + self.h / 2)

    def overlaps(self, other: Rect) -> bool:
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )

    def contains_point(self, point: Vec2) -> bool:
        return self.left <= point.x <= self.right and self.top <= point.y <= self.bottom

    def to_pygame(self):
        import pygame

        return pygame.Rect(int(self.x), int(self.y), int(self.w), int(self.h))

    def __repr__(self) -> str:
        return f"Rect({self.x:.0f}, {self.y:.0f}, {self.w:.0f}, {self.h:.0f})"
