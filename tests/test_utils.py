"""Tests for Vec2, Rect, Timer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drift2d.utils import Vec2, Rect, Timer


def test_vec2_add():
    a = Vec2(1, 2)
    b = Vec2(3, 4)
    c = a + b
    assert c.x == 4.0
    assert c.y == 6.0


def test_vec2_sub():
    a = Vec2(5, 10)
    b = Vec2(2, 3)
    c = a - b
    assert c.x == 3.0
    assert c.y == 7.0


def test_vec2_mul():
    a = Vec2(3, 4)
    b = a * 2
    assert b.x == 6.0
    assert b.y == 8.0


def test_vec2_rmul():
    a = Vec2(3, 4)
    b = 2 * a
    assert b.x == 6.0
    assert b.y == 8.0


def test_vec2_length():
    a = Vec2(3, 4)
    assert abs(a.length - 5.0) < 0.001


def test_vec2_normalized():
    a = Vec2(10, 0)
    n = a.normalized
    assert abs(n.x - 1.0) < 0.001
    assert abs(n.y) < 0.001


def test_vec2_zero_normalized():
    a = Vec2(0, 0)
    n = a.normalized
    assert n.x == 0.0 and n.y == 0.0


def test_vec2_distance():
    a = Vec2(0, 0)
    b = Vec2(3, 4)
    assert abs(a.distance_to(b) - 5.0) < 0.001


def test_vec2_dot():
    a = Vec2(1, 0)
    b = Vec2(0, 1)
    assert a.dot(b) == 0.0


def test_vec2_iadd():
    a = Vec2(1, 2)
    a += Vec2(3, 4)
    assert a.x == 4.0 and a.y == 6.0


def test_rect_overlap():
    a = Rect(0, 0, 10, 10)
    b = Rect(5, 5, 10, 10)
    assert a.overlaps(b)


def test_rect_no_overlap():
    a = Rect(0, 0, 10, 10)
    b = Rect(20, 20, 10, 10)
    assert not a.overlaps(b)


def test_rect_contains_point():
    r = Rect(0, 0, 100, 100)
    assert r.contains_point(Vec2(50, 50))
    assert not r.contains_point(Vec2(150, 50))


def test_rect_center():
    r = Rect(0, 0, 100, 50)
    c = r.center
    assert c.x == 50.0 and c.y == 25.0


def test_timer_countdown():
    t = Timer(1.0)
    assert not t.done
    finished = t.update(0.5)
    assert not finished
    assert not t.done
    finished = t.update(0.6)
    assert finished
    assert t.done


def test_timer_progress():
    t = Timer(2.0)
    t.update(1.0)
    assert abs(t.progress - 0.5) < 0.01


def test_timer_reset():
    t = Timer(1.0)
    t.update(1.5)
    assert t.done
    t.reset()
    assert not t.done
    assert t.remaining == 1.0
