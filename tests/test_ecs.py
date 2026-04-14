"""Tests for Entity, World, Components."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drift2d.entity import Entity, World, Transform, Sprite
from drift2d.utils import Vec2


def test_entity_create():
    e = Entity("player")
    assert e.name == "player"
    assert e.active is True


def test_entity_components():
    e = Entity("test")
    t = e.add(Transform(position=Vec2(10, 20)))
    assert e.has(Transform)
    assert e.get(Transform).position.x == 10.0
    assert not e.has(Sprite)


def test_entity_remove_component():
    e = Entity()
    e.add(Transform())
    e.add(Sprite())
    assert e.has(Sprite)
    e.remove(Sprite)
    assert not e.has(Sprite)
    assert e.has(Transform)


def test_entity_tags():
    e = Entity()
    e.tags.add("enemy")
    e.tags.add("flying")
    assert "enemy" in e.tags
    assert "player" not in e.tags


def test_world_spawn_and_flush():
    w = World()
    e = Entity("a")
    w.spawn(e)
    # Not yet in world until flush
    assert w.count == 0
    w.flush()
    assert w.count == 1


def test_world_despawn():
    w = World()
    e = Entity("a")
    w.spawn(e)
    w.flush()
    assert w.count == 1
    w.despawn(e)
    w.flush()
    assert w.count == 0


def test_world_query():
    w = World()
    e1 = Entity("a")
    e1.add(Transform())
    e1.add(Sprite())

    e2 = Entity("b")
    e2.add(Transform())

    w.spawn(e1)
    w.spawn(e2)
    w.flush()

    # Query for entities with both Transform and Sprite
    results = list(w.query(Transform, Sprite))
    assert len(results) == 1
    assert results[0].name == "a"

    # Query for just Transform
    results = list(w.query(Transform))
    assert len(results) == 2


def test_world_query_tag():
    w = World()
    e1 = Entity("enemy1")
    e1.tags.add("enemy")
    e2 = Entity("player")
    e2.tags.add("player")

    w.spawn(e1)
    w.spawn(e2)
    w.flush()

    enemies = list(w.query_tag("enemy"))
    assert len(enemies) == 1
    assert enemies[0].name == "enemy1"


def test_world_find():
    w = World()
    e = Entity("target")
    w.spawn(e)
    w.flush()
    found = w.find("target")
    assert found is not None
    assert found.name == "target"
    assert w.find("nonexistent") is None


def test_world_clear():
    w = World()
    for i in range(5):
        w.spawn(Entity(f"e{i}"))
    w.flush()
    assert w.count == 5
    w.clear()
    assert w.count == 0
