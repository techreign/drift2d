"""Tests for Tilemap (no pygame display needed)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drift2d.tilemap import Tilemap, TileDef
from drift2d.utils import Vec2, Rect


def test_load_from_string():
    tm = Tilemap(tile_size=16)
    tm.load_from_string("...\nGGG\n...")
    assert tm.width == 3
    assert tm.height == 3
    assert tm.get_tile(0, 1) == "G"
    assert tm.get_tile(0, 0) == "."


def test_find_tiles():
    tm = Tilemap()
    tm.load_from_string("..P.\nGGGG\n...P")
    positions = tm.find_tiles("P")
    assert (2, 0) in positions
    assert (3, 2) in positions
    assert len(positions) == 2


def test_world_to_tile():
    tm = Tilemap(tile_size=32)
    col, row = tm.world_to_tile(Vec2(50, 70))
    assert col == 1
    assert row == 2


def test_tile_to_world():
    tm = Tilemap(tile_size=32)
    pos = tm.tile_to_world(3, 5)
    assert pos.x == 96.0
    assert pos.y == 160.0


def test_solid_collision():
    tm = Tilemap(tile_size=32)
    tm.define("G", TileDef(char="G", solid=True))
    tm.load_from_string("...\nGGG\n...")

    # Rect overlapping the ground row
    test_rect = Rect(10, 30, 20, 20)
    hits = tm.collide_rect(test_rect)
    assert len(hits) > 0

    # Rect not touching ground
    test_rect2 = Rect(10, 0, 10, 10)
    hits2 = tm.collide_rect(test_rect2)
    assert len(hits2) == 0


def test_set_tile():
    tm = Tilemap()
    tm.load_from_string("...\n...\n...")
    tm.set_tile(1, 1, "X")
    assert tm.get_tile(1, 1) == "X"
