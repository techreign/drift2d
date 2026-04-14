"""Load entities from YAML files. The heart of the declarative workflow."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml
from .entity import (
    Entity,
    Transform,
    Sprite,
    RigidBody,
    BoxCollider,
    AnimationPlayer,
)
from .utils import Vec2


# Maps YAML component names to builder functions
_COMPONENT_BUILDERS: dict[str, Any] = {}


def register_component(name: str, builder):
    """Register a custom component loader. builder(data) -> component instance."""
    _COMPONENT_BUILDERS[name] = builder


def _build_transform(data: dict) -> Transform:
    pos = data.get("position", [0, 0])
    scale = data.get("scale", [1, 1])
    return Transform(
        position=Vec2(pos[0], pos[1]),
        rotation=data.get("rotation", 0.0),
        scale=Vec2(scale[0], scale[1]),
    )


def _build_sprite(data: dict) -> Sprite:
    return Sprite(
        image=data.get("image", ""),
        color=tuple(data.get("color", [255, 255, 255])),
        width=data.get("width", 32),
        height=data.get("height", 32),
        flip_x=data.get("flip_x", False),
        flip_y=data.get("flip_y", False),
        visible=data.get("visible", True),
        layer=data.get("layer", 0),
    )


def _build_rigidbody(data: dict) -> RigidBody:
    vel = data.get("velocity", [0, 0])
    return RigidBody(
        velocity=Vec2(vel[0], vel[1]),
        gravity_scale=data.get("gravity_scale", 1.0),
        friction=data.get("friction", 0.0),
        kinematic=data.get("kinematic", False),
    )


def _build_collider(data: dict) -> BoxCollider:
    offset = data.get("offset", [0, 0])
    return BoxCollider(
        width=data.get("width", 32),
        height=data.get("height", 32),
        offset=Vec2(offset[0], offset[1]),
        solid=data.get("solid", True),
        tag=data.get("tag", ""),
    )


def _build_animation(data: dict) -> AnimationPlayer:
    return AnimationPlayer(
        animations=data.get("animations", {}),
        current=data.get("default", ""),
        speed=data.get("speed", 10.0),
    )


_BUILTIN_BUILDERS = {
    "transform": _build_transform,
    "sprite": _build_sprite,
    "rigidbody": _build_rigidbody,
    "collider": _build_collider,
    "animation": _build_animation,
}


def load_entity(path: Path) -> Entity:
    """Load a single entity from a YAML file."""
    data = yaml.safe_load(path.read_text())
    return _entity_from_dict(data)


def load_entities(directory: Path) -> list[Entity]:
    """Load all .yaml entity files from a directory."""
    entities = []
    if not directory.exists():
        return entities
    for path in sorted(directory.glob("*.yaml")):
        entities.append(load_entity(path))
    return entities


def entity_from_yaml(yaml_string: str) -> Entity:
    """Create an entity from a YAML string (useful for inline definitions)."""
    data = yaml.safe_load(yaml_string)
    return _entity_from_dict(data)


def _entity_from_dict(data: dict) -> Entity:
    entity = Entity(name=data.get("name", ""))

    for tag in data.get("tags", []):
        entity.tags.add(tag)

    for key, value in data.items():
        if key in ("name", "tags"):
            continue

        builder = _BUILTIN_BUILDERS.get(key) or _COMPONENT_BUILDERS.get(key)
        if builder and isinstance(value, dict):
            entity.add(builder(value))
        elif builder and value is True:
            # Allow shorthand like `rigidbody: true` for defaults
            entity.add(builder({}))

    # Ensure every entity has a Transform
    if not entity.has(Transform):
        entity.add(Transform())

    return entity
