"""Tilemap: load and render tile-based levels from plain text or CSV."""

from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import pygame
from .utils import Vec2, Rect


@dataclass
class TileDef:
    """Definition of a tile type."""

    char: str
    color: tuple = (100, 100, 100)
    solid: bool = False
    image: str = ""
    tag: str = ""


class Tilemap:
    """
    Grid-based level. Define tiles, load from a text file, render + collide.

    Level format (level.txt):
        ................
        ....GGGG........
        ..............G.
        .P..........GGG.
        GGGGGGGGGGGGGGGG

    Usage:
        tilemap = Tilemap(tile_size=32)
        tilemap.define("G", TileDef(char="G", color=(60,60,80), solid=True))
        tilemap.define("P", TileDef(char="P", color=(100,200,255), tag="spawn"))
        tilemap.load_from_file("levels/level1.txt")
    """

    def __init__(self, tile_size: int = 32):
        self.tile_size = tile_size
        self.tiles: dict[str, TileDef] = {}
        self.grid: list[list[str]] = []
        self.width = 0  # in tiles
        self.height = 0  # in tiles
        self._surface: pygame.Surface | None = None
        self._dirty = True
        self._sprite_cache: dict[str, pygame.Surface] = {}
        self._asset_root: Path | None = None

    def define(self, char: str, tile_def: TileDef):
        self.tiles[char] = tile_def
        self._dirty = True

    def load_from_string(self, text: str):
        self.grid = []
        for line in text.strip().splitlines():
            self.grid.append(list(line))
        self.height = len(self.grid)
        self.width = max(len(row) for row in self.grid) if self.grid else 0
        self._dirty = True

    def load_from_file(self, path: str | Path):
        path = Path(path)
        self.load_from_string(path.read_text())

    def get_tile(self, col: int, row: int) -> str | None:
        if 0 <= row < self.height and 0 <= col < len(self.grid[row]):
            return self.grid[row][col]
        return None

    def set_tile(self, col: int, row: int, char: str):
        if 0 <= row < self.height and 0 <= col < len(self.grid[row]):
            self.grid[row][col] = char
            self._dirty = True

    def world_to_tile(self, pos: Vec2) -> tuple[int, int]:
        return int(pos.x // self.tile_size), int(pos.y // self.tile_size)

    def tile_to_world(self, col: int, row: int) -> Vec2:
        return Vec2(col * self.tile_size, row * self.tile_size)

    def find_tiles(self, char: str) -> list[tuple[int, int]]:
        """Find all positions of a tile character. Returns (col, row) list."""
        results = []
        for row in range(self.height):
            for col in range(len(self.grid[row])):
                if self.grid[row][col] == char:
                    results.append((col, row))
        return results

    def get_solid_rect(self, col: int, row: int) -> Rect | None:
        char = self.get_tile(col, row)
        if char and char in self.tiles and self.tiles[char].solid:
            return Rect(
                col * self.tile_size,
                row * self.tile_size,
                self.tile_size,
                self.tile_size,
            )
        return None

    def collide_rect(self, rect: Rect) -> list[Rect]:
        """Return all solid tile rects that overlap with the given rect."""
        min_col = max(0, int(rect.left // self.tile_size))
        max_col = min(self.width - 1, int(rect.right // self.tile_size))
        min_row = max(0, int(rect.top // self.tile_size))
        max_row = min(self.height - 1, int(rect.bottom // self.tile_size))

        hits = []
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                solid_rect = self.get_solid_rect(col, row)
                if solid_rect and solid_rect.overlaps(rect):
                    hits.append(solid_rect)
        return hits

    def _build_surface(self):
        """Pre-render the entire tilemap to a surface for fast blitting."""
        pw = self.width * self.tile_size
        ph = self.height * self.tile_size
        self._surface = pygame.Surface((pw, ph), pygame.SRCALPHA)

        for row in range(self.height):
            for col in range(len(self.grid[row])):
                char = self.grid[row][col]
                if char == "." or char == " " or char not in self.tiles:
                    continue

                tile_def = self.tiles[char]
                x = col * self.tile_size
                y = row * self.tile_size

                if tile_def.image and self._asset_root:
                    img_path = self._asset_root / "sprites" / tile_def.image
                    if tile_def.image not in self._sprite_cache and img_path.exists():
                        img = pygame.image.load(str(img_path)).convert_alpha()
                        self._sprite_cache[tile_def.image] = pygame.transform.scale(
                            img, (self.tile_size, self.tile_size)
                        )
                    if tile_def.image in self._sprite_cache:
                        self._surface.blit(self._sprite_cache[tile_def.image], (x, y))
                        continue

                # Fallback: colored rect
                pygame.draw.rect(
                    self._surface,
                    tile_def.color,
                    pygame.Rect(x, y, self.tile_size, self.tile_size),
                )

        self._dirty = False

    def draw(self, screen: pygame.Surface, camera_offset: Vec2 = Vec2()):
        """Draw the tilemap with camera offset."""
        if self._dirty or self._surface is None:
            self._build_surface()
        screen.blit(self._surface, (-camera_offset.x, -camera_offset.y))
