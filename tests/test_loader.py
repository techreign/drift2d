"""Tests for YAML entity loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drift2d.loader import entity_from_yaml
from drift2d.entity import Transform, Sprite, RigidBody, BoxCollider


def test_load_basic_entity():
    yaml_str = """
name: player
tags: [player, hero]
transform:
  position: [100, 200]
sprite:
  color: [255, 0, 0]
  width: 32
  height: 48
"""
    e = entity_from_yaml(yaml_str)
    assert e.name == "player"
    assert "player" in e.tags
    assert "hero" in e.tags
    assert e.has(Transform)
    assert e.get(Transform).position.x == 100.0
    assert e.get(Transform).position.y == 200.0
    assert e.has(Sprite)
    assert e.get(Sprite).color == (255, 0, 0)
    assert e.get(Sprite).width == 32


def test_load_with_physics():
    yaml_str = """
name: ball
transform:
  position: [50, 50]
rigidbody:
  gravity_scale: 1.0
  friction: 0.5
collider:
  width: 16
  height: 16
  tag: ball
"""
    e = entity_from_yaml(yaml_str)
    assert e.has(RigidBody)
    assert e.get(RigidBody).gravity_scale == 1.0
    assert e.get(RigidBody).friction == 0.5
    assert e.has(BoxCollider)
    assert e.get(BoxCollider).tag == "ball"


def test_load_shorthand():
    yaml_str = """
name: simple
rigidbody: true
"""
    e = entity_from_yaml(yaml_str)
    assert e.has(RigidBody)
    assert e.has(Transform)  # always added


def test_load_defaults():
    yaml_str = """
name: empty
"""
    e = entity_from_yaml(yaml_str)
    assert e.name == "empty"
    assert e.has(Transform)
    assert e.get(Transform).position.x == 0.0


def test_load_with_scale_and_rotation():
    yaml_str = """
name: rotated
transform:
  position: [10, 20]
  rotation: 45.0
  scale: [2, 3]
"""
    e = entity_from_yaml(yaml_str)
    t = e.get(Transform)
    assert t.rotation == 45.0
    assert t.scale.x == 2.0
    assert t.scale.y == 3.0
