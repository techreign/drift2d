"""ECS-lite: Entities are IDs, Components are data, Systems are functions."""

from __future__ import annotations
from typing import Any, Iterator
from dataclasses import dataclass, field
from .utils import Vec2


# ── Built-in Components ──────────────────────────────────────────


@dataclass
class Transform:
    position: Vec2 = field(default_factory=Vec2)
    rotation: float = 0.0
    scale: Vec2 = field(default_factory=lambda: Vec2(1.0, 1.0))


@dataclass
class Sprite:
    image: str = ""  # path relative to assets/sprites/
    color: tuple = (255, 255, 255)
    width: int = 32
    height: int = 32
    flip_x: bool = False
    flip_y: bool = False
    visible: bool = True
    layer: int = 0  # higher = drawn later (on top)


@dataclass
class RigidBody:
    velocity: Vec2 = field(default_factory=Vec2)
    acceleration: Vec2 = field(default_factory=Vec2)
    gravity_scale: float = 1.0
    friction: float = 0.0
    kinematic: bool = False  # True = moved by code, not physics


@dataclass
class BoxCollider:
    width: float = 32.0
    height: float = 32.0
    offset: Vec2 = field(default_factory=Vec2)
    solid: bool = True
    tag: str = ""  # for filtering collisions


@dataclass
class AnimationPlayer:
    animations: dict = field(default_factory=dict)  # name -> list of frame paths
    current: str = ""
    frame: int = 0
    speed: float = 10.0  # frames per second
    _timer: float = 0.0


# ── Entity ────────────────────────────────────────────────────────


class Entity:
    """An entity is just an ID with a bag of components."""

    _next_id = 0

    def __init__(self, name: str = ""):
        Entity._next_id += 1
        self.id: int = Entity._next_id
        self.name: str = name or f"entity_{self.id}"
        self.active: bool = True
        self.tags: set[str] = set()
        self._components: dict[type, Any] = {}

    def add(self, component: Any) -> Any:
        self._components[type(component)] = component
        return component

    def get(self, comp_type: type) -> Any | None:
        return self._components.get(comp_type)

    def has(self, comp_type: type) -> bool:
        return comp_type in self._components

    def remove(self, comp_type: type):
        self._components.pop(comp_type, None)

    def __repr__(self) -> str:
        comps = ", ".join(c.__class__.__name__ for c in self._components.values())
        return f"Entity({self.name} [{comps}])"


# ── World ─────────────────────────────────────────────────────────


class World:
    """Container for all entities. Query by component type."""

    def __init__(self):
        self._entities: dict[int, Entity] = {}
        self._to_add: list[Entity] = []
        self._to_remove: list[int] = []

    def spawn(self, entity: Entity) -> Entity:
        self._to_add.append(entity)
        return entity

    def despawn(self, entity: Entity):
        self._to_remove.append(entity.id)

    def query(self, *comp_types: type) -> Iterator[Entity]:
        for entity in self._entities.values():
            if entity.active and all(entity.has(ct) for ct in comp_types):
                yield entity

    def query_tag(self, tag: str) -> Iterator[Entity]:
        for entity in self._entities.values():
            if entity.active and tag in entity.tags:
                yield entity

    def find(self, name: str) -> Entity | None:
        for entity in self._entities.values():
            if entity.name == name:
                return entity
        return None

    def flush(self):
        """Apply pending adds/removes. Called by engine each frame."""
        for entity in self._to_add:
            self._entities[entity.id] = entity
        self._to_add.clear()

        for eid in self._to_remove:
            self._entities.pop(eid, None)
        self._to_remove.clear()

    def clear(self):
        self._entities.clear()
        self._to_add.clear()
        self._to_remove.clear()

    @property
    def count(self) -> int:
        return len(self._entities)
