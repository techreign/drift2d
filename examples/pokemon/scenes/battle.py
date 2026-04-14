"""Turn-based battle scene for the Pokemon example game."""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame

from drift2d import Scene

if TYPE_CHECKING:
    from core.pokemon import Pokemon


# ── State machine ──────────────────────────────────────────────────────────────


class State(Enum):
    INTRO = auto()
    CHOOSE_ACTION = auto()
    CHOOSE_MOVE = auto()
    CHOOSE_POKEMON = auto()
    ENEMY_TURN = auto()
    ANIMATING = auto()
    MESSAGE = auto()
    CATCH = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Constants ──────────────────────────────────────────────────────────────────

W, H = 800, 600

# Layout
ENEMY_CENTER = (560, 160)  # enemy pokemon circle center
PLAYER_CENTER = (240, 360)  # player pokemon circle center
ENEMY_RADIUS = 55
PLAYER_RADIUS = 70

# Menu box
MENU_BOX_RECT = pygame.Rect(0, 430, 800, 170)
MSG_BOX_RECT = pygame.Rect(0, 430, 800, 170)

# HP bar geometry for each side
ENEMY_HP_RECT = pygame.Rect(30, 60, 240, 14)
PLAYER_HP_RECT = pygame.Rect(530, 330, 240, 14)

# Colors
COL_BG_TOP = (144, 200, 128)
COL_BG_BOT = (80, 160, 64)
COL_PANEL = (20, 24, 32)
COL_WHITE = (255, 255, 255)
COL_BLACK = (0, 0, 0)
COL_GRAY = (90, 90, 100)
COL_DARK = (30, 34, 44)
COL_HP_GREEN = (88, 208, 80)
COL_HP_YELLOW = (248, 208, 48)
COL_HP_RED = (240, 80, 48)
COL_HP_BG = (40, 40, 48)
COL_SELECT = (255, 220, 60)

# Type colors (used for move buttons)
TYPE_COLORS = {
    "normal": (168, 168, 120),
    "fire": (240, 128, 48),
    "water": (104, 144, 240),
    "grass": (120, 200, 80),
    "electric": (248, 208, 48),
    "ice": (152, 216, 216),
    "fighting": (192, 48, 40),
    "poison": (160, 64, 160),
    "ground": (224, 192, 104),
    "flying": (168, 144, 240),
    "psychic": (248, 88, 136),
    "bug": (168, 184, 32),
    "rock": (184, 160, 56),
    "ghost": (112, 88, 152),
    "dragon": (112, 56, 248),
}

ACTION_LABELS = ["FIGHT", "BAG", "POKEMON", "RUN"]
ACTION_COLORS = {
    "FIGHT": (180, 40, 40),
    "BAG": (200, 160, 20),
    "POKEMON": (40, 150, 60),
    "RUN": (50, 80, 190),
}


# ── Helpers ────────────────────────────────────────────────────────────────────


def _hp_color(pct: float) -> tuple:
    if pct > 0.5:
        return COL_HP_GREEN
    if pct > 0.20:
        return COL_HP_YELLOW
    return COL_HP_RED


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * min(1.0, max(0.0, t))


def _catch_success(pokemon: "Pokemon", pokeballs: int) -> bool:
    """Simplified catch calculation using catch_rate."""
    if pokeballs <= 0:
        return False
    catch_rate = pokemon.species.catch_rate
    hp_factor = (3 * pokemon.max_hp - 2 * pokemon.hp) / (3 * pokemon.max_hp)
    chance = (catch_rate / 255) * hp_factor
    return random.random() < chance


def _draw_rounded_rect(
    screen: pygame.Surface,
    color: tuple,
    rect: pygame.Rect,
    radius: int = 10,
    border: int = 0,
    border_color: tuple | None = None,
):
    """Draw a rectangle with rounded corners using pygame.draw calls."""
    if border > 0 and border_color:
        outer = pygame.Rect(
            rect.x - border, rect.y - border, rect.w + border * 2, rect.h + border * 2
        )
        _draw_rounded_rect(screen, border_color, outer, radius + border)

    r = max(0, min(radius, rect.w // 2, rect.h // 2))
    # Center rect
    pygame.draw.rect(
        screen, color, pygame.Rect(rect.x + r, rect.y, rect.w - 2 * r, rect.h)
    )
    pygame.draw.rect(
        screen, color, pygame.Rect(rect.x, rect.y + r, rect.w, rect.h - 2 * r)
    )
    # Corner circles
    pygame.draw.circle(screen, color, (rect.x + r, rect.y + r), r)
    pygame.draw.circle(screen, color, (rect.right - r, rect.y + r), r)
    pygame.draw.circle(screen, color, (rect.x + r, rect.bottom - r), r)
    pygame.draw.circle(screen, color, (rect.right - r, rect.bottom - r), r)


# ── Pokemon sprite drawing ─────────────────────────────────────────────────────


def _draw_pokemon_sprite(
    screen: pygame.Surface,
    name: str,
    cx: int,
    cy: int,
    size: int,
    facing_left: bool,
    is_fainted: bool = False,
):
    """Draw a recognizable pokemon shape using pygame.draw primitives.

    cx, cy = center of the sprite bounding box
    size   = approximate radius/half-height of the creature
    facing_left = True for enemy (faces left toward player)
    """
    if is_fainted:
        _draw_fainted(screen, cx, cy, size)
        return

    name_low = name.lower()
    draw_fn = _SPRITE_REGISTRY.get(name_low, _draw_generic)
    draw_fn(screen, cx, cy, size, facing_left)


def _draw_fainted(screen: pygame.Surface, cx: int, cy: int, size: int):
    """Gray swirl / X to show fainted state."""
    pygame.draw.circle(screen, (100, 100, 110), (cx, cy), size)
    pygame.draw.circle(screen, (70, 70, 80), (cx, cy), size, 3)
    # X mark
    s = size // 2
    pygame.draw.line(screen, (200, 50, 50), (cx - s, cy - s), (cx + s, cy + s), 4)
    pygame.draw.line(screen, (200, 50, 50), (cx + s, cy - s), (cx - s, cy + s), 4)


def _flip(x: int, cx: int, facing_left: bool) -> int:
    """Mirror an x-offset around cx if not facing left."""
    if facing_left:
        return cx + x
    return cx - x


# ── Individual species ─────────────────────────────────────────────────────────


def _draw_charmander(screen, cx, cy, size, facing_left):
    s = size
    # Body — orange teardrop
    pygame.draw.ellipse(
        screen, (240, 130, 40), pygame.Rect(cx - s // 2, cy - s // 2, s, int(s * 1.2))
    )
    # Cream belly
    pygame.draw.ellipse(
        screen,
        (255, 220, 160),
        pygame.Rect(cx - s // 3, cy - s // 4, s // 2 + 4, int(s * 0.7)),
    )
    # Head
    pygame.draw.circle(screen, (240, 130, 40), (cx, cy - int(s * 0.55)), int(s * 0.45))
    # Eyes
    ex = _flip(int(s * 0.15), cx, facing_left)
    pygame.draw.circle(screen, COL_WHITE, (ex, cy - int(s * 0.6)), int(s * 0.12))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.6)), int(s * 0.07))
    # Arm
    arm_x = _flip(-int(s * 0.45), cx, facing_left)
    pygame.draw.line(
        screen,
        (220, 110, 30),
        (arm_x, cy - s // 6),
        (arm_x - (6 if facing_left else -6), cy + s // 4),
        5,
    )
    # Tail — curved upward with flame
    tail_x = _flip(-int(s * 0.4), cx, facing_left)
    tail_y = cy + int(s * 0.5)
    end_x = _flip(-int(s * 0.7), cx, facing_left)
    end_y = cy + int(s * 0.1)
    pygame.draw.line(screen, (220, 100, 30), (tail_x, tail_y), (end_x, end_y), 5)
    # Flame tip
    flame_pts = [
        (end_x, end_y - int(s * 0.3)),
        (end_x - 6, end_y),
        (end_x + 6, end_y),
    ]
    pygame.draw.polygon(screen, (255, 200, 0), flame_pts)
    pygame.draw.polygon(
        screen,
        (255, 100, 0),
        [
            (end_x, end_y - int(s * 0.18)),
            (end_x - 3, end_y + 2),
            (end_x + 3, end_y + 2),
        ],
    )
    # Outline
    pygame.draw.ellipse(
        screen, (160, 80, 20), pygame.Rect(cx - s // 2, cy - s // 2, s, int(s * 1.2)), 2
    )
    pygame.draw.circle(
        screen, (160, 80, 20), (cx, cy - int(s * 0.55)), int(s * 0.45), 2
    )


def _draw_squirtle(screen, cx, cy, size, facing_left):
    s = size
    # Shell (brown oval behind)
    pygame.draw.ellipse(
        screen,
        (140, 100, 60),
        pygame.Rect(cx - int(s * 0.45), cy - int(s * 0.55), int(s * 0.9), int(s * 1.1)),
    )
    # Body — blue round
    pygame.draw.circle(screen, (90, 150, 220), (cx, cy), int(s * 0.55))
    # Cream belly
    pygame.draw.ellipse(
        screen,
        (220, 230, 255),
        pygame.Rect(
            cx - int(s * 0.28), cy - int(s * 0.25), int(s * 0.56), int(s * 0.5)
        ),
    )
    # Head
    pygame.draw.circle(screen, (90, 150, 220), (cx, cy - int(s * 0.52)), int(s * 0.38))
    # Shell ridge lines
    for i in range(3):
        lx = cx - int(s * 0.3) + i * int(s * 0.3)
        pygame.draw.line(
            screen, (100, 70, 40), (lx, cy - int(s * 0.45)), (lx, cy + int(s * 0.5)), 2
        )
    # Eyes
    ex = _flip(int(s * 0.14), cx, facing_left)
    pygame.draw.circle(screen, COL_WHITE, (ex, cy - int(s * 0.55)), int(s * 0.12))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.55)), int(s * 0.07))
    # Tail — curled
    tail_x = _flip(-int(s * 0.5), cx, facing_left)
    pygame.draw.circle(
        screen, (90, 150, 220), (tail_x, cy + int(s * 0.35)), int(s * 0.15), 3
    )
    pygame.draw.circle(
        screen, (90, 150, 220), (tail_x, cy + int(s * 0.35)), int(s * 0.08)
    )
    # Outline
    pygame.draw.circle(screen, (50, 90, 160), (cx, cy), int(s * 0.55), 2)
    pygame.draw.circle(
        screen, (50, 90, 160), (cx, cy - int(s * 0.52)), int(s * 0.38), 2
    )


def _draw_bulbasaur(screen, cx, cy, size, facing_left):
    s = size
    # Body — green round
    pygame.draw.ellipse(
        screen,
        (110, 190, 120),
        pygame.Rect(cx - int(s * 0.55), cy - int(s * 0.4), int(s * 1.1), int(s * 0.85)),
    )
    # Bulb on top/back — dark green oval
    bx = _flip(-int(s * 0.1), cx, facing_left)
    pygame.draw.ellipse(
        screen,
        (60, 140, 70),
        pygame.Rect(bx - int(s * 0.3), cy - int(s * 0.85), int(s * 0.6), int(s * 0.65)),
    )
    # Bulb spots
    pygame.draw.circle(screen, (40, 110, 50), (bx - 4, cy - int(s * 0.65)), 5)
    pygame.draw.circle(screen, (40, 110, 50), (bx + 6, cy - int(s * 0.72)), 4)
    # Head
    pygame.draw.circle(screen, (110, 190, 120), (cx, cy - int(s * 0.4)), int(s * 0.38))
    # Eyes
    ex = _flip(int(s * 0.15), cx, facing_left)
    pygame.draw.circle(screen, (220, 30, 30), (ex, cy - int(s * 0.44)), int(s * 0.11))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.44)), int(s * 0.06))
    # Spots on body
    pygame.draw.circle(screen, (80, 160, 90), (cx + int(s * 0.3), cy), 6)
    pygame.draw.circle(
        screen, (80, 160, 90), (cx - int(s * 0.35), cy + int(s * 0.15)), 5
    )
    # Outline
    pygame.draw.ellipse(
        screen,
        (60, 130, 70),
        pygame.Rect(cx - int(s * 0.55), cy - int(s * 0.4), int(s * 1.1), int(s * 0.85)),
        2,
    )
    pygame.draw.circle(screen, (60, 130, 70), (cx, cy - int(s * 0.4)), int(s * 0.38), 2)


def _draw_pikachu(screen, cx, cy, size, facing_left):
    s = size
    # Yellow body
    pygame.draw.ellipse(
        screen,
        (248, 220, 50),
        pygame.Rect(cx - int(s * 0.45), cy - int(s * 0.3), int(s * 0.9), int(s * 0.75)),
    )
    # Head round
    pygame.draw.circle(screen, (248, 220, 50), (cx, cy - int(s * 0.3)), int(s * 0.42))
    # Ears — pointy triangles
    ear_base = int(s * 0.15)
    ear_h = int(s * 0.55)
    # Left ear
    lx = _flip(int(s * 0.2), cx, facing_left)
    le_pts = [
        (lx - ear_base, cy - int(s * 0.55)),
        (lx + ear_base, cy - int(s * 0.55)),
        (lx, cy - int(s * 0.55) - ear_h),
    ]
    pygame.draw.polygon(screen, (248, 220, 50), le_pts)
    pygame.draw.polygon(
        screen,
        (40, 20, 20),
        [
            (lx - ear_base // 2, cy - int(s * 0.55) - ear_h // 5),
            (lx + ear_base // 2, cy - int(s * 0.55) - ear_h // 5),
            (lx, cy - int(s * 0.55) - ear_h + 4),
        ],
    )
    # Right ear
    rx = _flip(-int(s * 0.2), cx, facing_left)
    re_pts = [
        (rx - ear_base, cy - int(s * 0.55)),
        (rx + ear_base, cy - int(s * 0.55)),
        (rx, cy - int(s * 0.55) - ear_h),
    ]
    pygame.draw.polygon(screen, (248, 220, 50), re_pts)
    pygame.draw.polygon(
        screen,
        (40, 20, 20),
        [
            (rx - ear_base // 2, cy - int(s * 0.55) - ear_h // 5),
            (rx + ear_base // 2, cy - int(s * 0.55) - ear_h // 5),
            (rx, cy - int(s * 0.55) - ear_h + 4),
        ],
    )
    # Red cheeks
    chk = _flip(int(s * 0.28), cx, facing_left)
    pygame.draw.circle(screen, (240, 80, 80), (chk, cy - int(s * 0.2)), int(s * 0.14))
    chk2 = _flip(-int(s * 0.28), cx, facing_left)
    pygame.draw.circle(screen, (240, 80, 80), (chk2, cy - int(s * 0.2)), int(s * 0.14))
    # Eye
    ex = _flip(int(s * 0.16), cx, facing_left)
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.36)), int(s * 0.09))
    pygame.draw.circle(screen, COL_WHITE, (ex + 2, cy - int(s * 0.38)), int(s * 0.04))
    # Lightning tail
    tx = _flip(-int(s * 0.5), cx, facing_left)
    ty = cy
    dir_x = -1 if facing_left else 1
    tail_pts = [
        (tx, ty - int(s * 0.1)),
        (tx + dir_x * int(s * 0.25), ty - int(s * 0.35)),
        (tx + dir_x * int(s * 0.15), ty - int(s * 0.2)),
        (tx + dir_x * int(s * 0.5), ty - int(s * 0.55)),
        (tx + dir_x * int(s * 0.4), ty - int(s * 0.3)),
        (tx + dir_x * int(s * 0.3), ty + int(s * 0.1)),
    ]
    pygame.draw.polygon(screen, (200, 160, 20), tail_pts)
    pygame.draw.polygon(screen, (240, 200, 30), tail_pts, 2)
    # Outline
    pygame.draw.circle(
        screen, (200, 160, 20), (cx, cy - int(s * 0.3)), int(s * 0.42), 2
    )
    pygame.draw.ellipse(
        screen,
        (200, 160, 20),
        pygame.Rect(cx - int(s * 0.45), cy - int(s * 0.3), int(s * 0.9), int(s * 0.75)),
        2,
    )


def _draw_rattata(screen, cx, cy, size, facing_left):
    s = size
    # Purple body
    pygame.draw.ellipse(
        screen,
        (160, 100, 180),
        pygame.Rect(
            cx - int(s * 0.55), cy - int(s * 0.25), int(s * 1.1), int(s * 0.65)
        ),
    )
    # Head
    pygame.draw.circle(screen, (160, 100, 180), (cx, cy - int(s * 0.3)), int(s * 0.38))
    # Big ears
    ex_r = _flip(int(s * 0.22), cx, facing_left)
    pygame.draw.ellipse(
        screen, (200, 140, 220), pygame.Rect(ex_r - 8, cy - int(s * 0.75), 16, 24)
    )
    pygame.draw.ellipse(
        screen, (240, 180, 250), pygame.Rect(ex_r - 5, cy - int(s * 0.72), 10, 18)
    )
    # Big front teeth
    tx = _flip(int(s * 0.1), cx, facing_left)
    pygame.draw.rect(screen, COL_WHITE, pygame.Rect(tx - 7, cy - int(s * 0.14), 6, 10))
    pygame.draw.rect(screen, COL_WHITE, pygame.Rect(tx + 1, cy - int(s * 0.14), 6, 10))
    pygame.draw.rect(
        screen, (220, 220, 220), pygame.Rect(tx - 7, cy - int(s * 0.14), 6, 10), 1
    )
    # Eye
    eye_x = _flip(int(s * 0.15), cx, facing_left)
    pygame.draw.circle(screen, (40, 20, 20), (eye_x, cy - int(s * 0.35)), int(s * 0.09))
    pygame.draw.circle(
        screen, COL_WHITE, (eye_x + 2, cy - int(s * 0.37)), int(s * 0.04)
    )
    # Long thin tail
    tail_x = _flip(-int(s * 0.5), cx, facing_left)
    dir_x = -1 if facing_left else 1
    pygame.draw.line(
        screen,
        (130, 80, 150),
        (tail_x, cy + int(s * 0.15)),
        (tail_x + dir_x * int(s * 0.6), cy - int(s * 0.3)),
        3,
    )
    # Outline
    pygame.draw.ellipse(
        screen,
        (110, 60, 130),
        pygame.Rect(
            cx - int(s * 0.55), cy - int(s * 0.25), int(s * 1.1), int(s * 0.65)
        ),
        2,
    )
    pygame.draw.circle(
        screen, (110, 60, 130), (cx, cy - int(s * 0.3)), int(s * 0.38), 2
    )


def _draw_pidgey(screen, cx, cy, size, facing_left):
    s = size
    # Brown body
    pygame.draw.ellipse(
        screen,
        (160, 130, 90),
        pygame.Rect(cx - int(s * 0.5), cy - int(s * 0.35), int(s * 1.0), int(s * 0.75)),
    )
    # Cream chest
    pygame.draw.ellipse(
        screen,
        (220, 200, 160),
        pygame.Rect(
            cx - int(s * 0.25), cy - int(s * 0.25), int(s * 0.5), int(s * 0.55)
        ),
    )
    # Head
    pygame.draw.circle(screen, (160, 130, 90), (cx, cy - int(s * 0.38)), int(s * 0.35))
    # Crest feather
    cx_c = _flip(int(s * 0.05), cx, facing_left)
    pygame.draw.ellipse(
        screen, (80, 60, 40), pygame.Rect(cx_c - 5, cy - int(s * 0.82), 10, 20)
    )
    # Wing
    wx = _flip(-int(s * 0.3), cx, facing_left)
    wing_pts = [
        (wx, cy - int(s * 0.1)),
        (wx - (30 if facing_left else -30), cy + int(s * 0.2)),
        (wx - (10 if facing_left else -10), cy + int(s * 0.35)),
        (wx + (20 if facing_left else -20), cy + int(s * 0.15)),
    ]
    pygame.draw.polygon(screen, (130, 100, 60), wing_pts)
    pygame.draw.polygon(screen, (100, 75, 40), wing_pts, 2)
    # Beak
    bk = _flip(int(s * 0.3), cx, facing_left)
    bk_pts = [
        (bk, cy - int(s * 0.38)),
        (bk + (14 if facing_left else -14), cy - int(s * 0.3)),
        (bk, cy - int(s * 0.22)),
    ]
    pygame.draw.polygon(screen, (220, 180, 60), bk_pts)
    # Eye
    ex = _flip(int(s * 0.12), cx, facing_left)
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.44)), int(s * 0.09))
    pygame.draw.circle(screen, COL_WHITE, (ex + 2, cy - int(s * 0.46)), int(s * 0.04))
    # Outline
    pygame.draw.ellipse(
        screen,
        (100, 80, 50),
        pygame.Rect(cx - int(s * 0.5), cy - int(s * 0.35), int(s * 1.0), int(s * 0.75)),
        2,
    )


def _draw_caterpie(screen, cx, cy, size, facing_left):
    s = size
    # Segmented worm body — 4 green ovals in a row
    seg_color = (110, 200, 80)
    dark_seg = (80, 160, 55)
    segs = 4
    seg_r = int(s * 0.25)
    dir_x = 1 if facing_left else -1
    for i in range(segs):
        sx = cx + dir_x * (i - segs // 2) * (seg_r + 2)
        sy = cy + int(math.sin(i * 0.8) * s * 0.15)
        col = seg_color if i % 2 == 0 else dark_seg
        pygame.draw.circle(screen, col, (sx, sy), seg_r)
        pygame.draw.circle(screen, (50, 120, 30), (sx, sy), seg_r, 2)
    # Head (front segment, larger)
    hx = cx + dir_x * (segs // 2) * (seg_r + 2)
    hy = cy - int(s * 0.05)
    pygame.draw.circle(screen, (130, 210, 90), (hx, hy), int(seg_r * 1.2))
    pygame.draw.circle(screen, (60, 140, 40), (hx, hy), int(seg_r * 1.2), 2)
    # Eyes
    ex = hx + dir_x * 5
    pygame.draw.circle(screen, COL_WHITE, (ex, hy - 6), 6)
    pygame.draw.circle(screen, COL_BLACK, (ex, hy - 6), 3)
    # Red antenna
    ant_x = hx + dir_x * 4
    ant_tip_x = ant_x + dir_x * 8
    pygame.draw.line(
        screen,
        (200, 50, 50),
        (ant_x, hy - int(seg_r * 1.1)),
        (ant_tip_x, hy - int(seg_r * 1.5)),
        3,
    )
    pygame.draw.circle(screen, (220, 60, 60), (ant_tip_x, hy - int(seg_r * 1.5)), 5)


def _draw_geodude(screen, cx, cy, size, facing_left):
    s = size
    # Rocky gray body — irregular polygon
    rock_pts = [
        (cx - int(s * 0.55), cy - int(s * 0.1)),
        (cx - int(s * 0.4), cy - int(s * 0.55)),
        (cx, cy - int(s * 0.6)),
        (cx + int(s * 0.45), cy - int(s * 0.45)),
        (cx + int(s * 0.55), cy + int(s * 0.1)),
        (cx + int(s * 0.35), cy + int(s * 0.5)),
        (cx - int(s * 0.3), cy + int(s * 0.55)),
        (cx - int(s * 0.5), cy + int(s * 0.3)),
    ]
    pygame.draw.polygon(screen, (160, 145, 115), rock_pts)
    # Rock texture lines
    pygame.draw.line(
        screen,
        (130, 115, 90),
        (cx - int(s * 0.3), cy - int(s * 0.3)),
        (cx + int(s * 0.1), cy + int(s * 0.15)),
        2,
    )
    pygame.draw.line(
        screen,
        (130, 115, 90),
        (cx + int(s * 0.2), cy - int(s * 0.4)),
        (cx + int(s * 0.4), cy + int(s * 0.05)),
        2,
    )
    # Angry eyes — thick brows
    ex = _flip(int(s * 0.18), cx, facing_left)
    ex2 = _flip(-int(s * 0.18), cx, facing_left)
    pygame.draw.circle(screen, COL_WHITE, (ex, cy - int(s * 0.15)), int(s * 0.14))
    pygame.draw.circle(screen, COL_WHITE, (ex2, cy - int(s * 0.15)), int(s * 0.14))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.13)), int(s * 0.09))
    pygame.draw.circle(screen, COL_BLACK, (ex2, cy - int(s * 0.13)), int(s * 0.09))
    # Brows (angry slant)
    pygame.draw.line(
        screen,
        COL_BLACK,
        (ex - int(s * 0.15), cy - int(s * 0.3)),
        (ex + int(s * 0.1), cy - int(s * 0.22)),
        4,
    )
    pygame.draw.line(
        screen,
        COL_BLACK,
        (ex2 + int(s * 0.15), cy - int(s * 0.3)),
        (ex2 - int(s * 0.1), cy - int(s * 0.22)),
        4,
    )
    # Arms — fist shapes
    arm_x = _flip(-int(s * 0.62), cx, facing_left)
    pygame.draw.circle(
        screen, (140, 125, 100), (arm_x, cy + int(s * 0.05)), int(s * 0.22)
    )
    pygame.draw.circle(
        screen, (110, 95, 75), (arm_x, cy + int(s * 0.05)), int(s * 0.22), 2
    )
    # Outline
    pygame.draw.polygon(screen, (100, 85, 65), rock_pts, 3)


def _draw_zubat(screen, cx, cy, size, facing_left):
    s = size
    # Purple body — small oval
    pygame.draw.ellipse(
        screen,
        (150, 90, 200),
        pygame.Rect(
            cx - int(s * 0.28), cy - int(s * 0.4), int(s * 0.56), int(s * 0.65)
        ),
    )
    # Wings — large bat wings
    dir_x = 1 if facing_left else -1
    # Left wing
    lw_pts = [
        (cx - int(s * 0.25), cy - int(s * 0.2)),
        (cx - int(s * 0.8), cy - int(s * 0.55)),
        (cx - int(s * 0.9), cy),
        (cx - int(s * 0.7), cy + int(s * 0.35)),
        (cx - int(s * 0.3), cy + int(s * 0.1)),
    ]
    pygame.draw.polygon(screen, (120, 60, 170), lw_pts)
    pygame.draw.polygon(screen, (90, 40, 140), lw_pts, 2)
    # Right wing
    rw_pts = [
        (cx + int(s * 0.25), cy - int(s * 0.2)),
        (cx + int(s * 0.8), cy - int(s * 0.55)),
        (cx + int(s * 0.9), cy),
        (cx + int(s * 0.7), cy + int(s * 0.35)),
        (cx + int(s * 0.3), cy + int(s * 0.1)),
    ]
    pygame.draw.polygon(screen, (120, 60, 170), rw_pts)
    pygame.draw.polygon(screen, (90, 40, 140), rw_pts, 2)
    # No visible eyes (blind)
    # Fang mouth
    pygame.draw.line(
        screen, COL_WHITE, (cx - 5, cy + int(s * 0.1)), (cx - 5, cy + int(s * 0.25)), 3
    )
    pygame.draw.line(
        screen, COL_WHITE, (cx + 5, cy + int(s * 0.1)), (cx + 5, cy + int(s * 0.25)), 3
    )
    # Ears — pointed
    pygame.draw.polygon(
        screen,
        (150, 90, 200),
        [
            (cx - int(s * 0.18), cy - int(s * 0.38)),
            (cx - int(s * 0.28), cy - int(s * 0.7)),
            (cx - int(s * 0.06), cy - int(s * 0.38)),
        ],
    )
    pygame.draw.polygon(
        screen,
        (150, 90, 200),
        [
            (cx + int(s * 0.18), cy - int(s * 0.38)),
            (cx + int(s * 0.28), cy - int(s * 0.7)),
            (cx + int(s * 0.06), cy - int(s * 0.38)),
        ],
    )
    # Outline body
    pygame.draw.ellipse(
        screen,
        (90, 50, 140),
        pygame.Rect(
            cx - int(s * 0.28), cy - int(s * 0.4), int(s * 0.56), int(s * 0.65)
        ),
        2,
    )


def _draw_gastly(screen, cx, cy, size, facing_left):
    s = size
    # Gaseous outer glow — translucent purple rings
    for r_off in [0.8, 0.7, 0.6]:
        glow_surf = pygame.Surface((s * 3, s * 3), pygame.SRCALPHA)
        alpha = int(40 + (0.8 - r_off) * 100)
        pygame.draw.circle(
            glow_surf,
            (120, 60, 170, alpha),
            (int(s * 1.5), int(s * 1.5)),
            int(s * r_off * 1.2),
        )
        screen.blit(glow_surf, (cx - int(s * 1.5), cy - int(s * 1.5)))
    # Core sphere
    pygame.draw.circle(screen, (80, 50, 130), (cx, cy), int(s * 0.55))
    # Swirling gas wisps
    for ang in [0, 90, 180, 270]:
        rad = math.radians(ang)
        wx = cx + int(math.cos(rad) * s * 0.7)
        wy = cy + int(math.sin(rad) * s * 0.7)
        pygame.draw.circle(screen, (100, 65, 160, 120), (wx, wy), int(s * 0.2))
    # Eyes — glowing white
    ex = _flip(int(s * 0.18), cx, facing_left)
    ex2 = _flip(-int(s * 0.18), cx, facing_left)
    pygame.draw.circle(screen, COL_WHITE, (ex, cy - int(s * 0.12)), int(s * 0.14))
    pygame.draw.circle(screen, COL_WHITE, (ex2, cy - int(s * 0.12)), int(s * 0.14))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.1)), int(s * 0.09))
    pygame.draw.circle(screen, COL_BLACK, (ex2, cy - int(s * 0.1)), int(s * 0.09))
    # Grinning mouth
    pygame.draw.arc(
        screen,
        COL_WHITE,
        pygame.Rect(
            cx - int(s * 0.22), cy + int(s * 0.05), int(s * 0.44), int(s * 0.22)
        ),
        math.pi,
        2 * math.pi,
        3,
    )
    # Outline
    pygame.draw.circle(screen, (60, 30, 110), (cx, cy), int(s * 0.55), 3)


def _draw_machop(screen, cx, cy, size, facing_left):
    s = size
    # Gray muscular body
    # Torso — wide trapezoid
    torso_pts = [
        (cx - int(s * 0.45), cy - int(s * 0.15)),
        (cx + int(s * 0.45), cy - int(s * 0.15)),
        (cx + int(s * 0.38), cy + int(s * 0.45)),
        (cx - int(s * 0.38), cy + int(s * 0.45)),
    ]
    pygame.draw.polygon(screen, (160, 155, 175), torso_pts)
    # Head
    pygame.draw.circle(screen, (160, 155, 175), (cx, cy - int(s * 0.38)), int(s * 0.35))
    # Head ridges (3 lines on top)
    for i in range(3):
        lx = cx - int(s * 0.2) + i * int(s * 0.2)
        pygame.draw.line(
            screen,
            (120, 115, 135),
            (lx, cy - int(s * 0.62)),
            (lx, cy - int(s * 0.7)),
            4,
        )
    # Eyes
    ex = _flip(int(s * 0.14), cx, facing_left)
    pygame.draw.circle(screen, (200, 50, 50), (ex, cy - int(s * 0.38)), int(s * 0.1))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.36)), int(s * 0.06))
    # Muscular arms
    la_x = _flip(-int(s * 0.52), cx, facing_left)
    pygame.draw.ellipse(
        screen,
        (140, 135, 155),
        pygame.Rect(
            la_x - int(s * 0.2), cy - int(s * 0.18), int(s * 0.4), int(s * 0.5)
        ),
    )
    # Pose — fist raised on one side
    fist_x = _flip(int(s * 0.52), cx, facing_left)
    pygame.draw.ellipse(
        screen,
        (140, 135, 155),
        pygame.Rect(
            fist_x - int(s * 0.2), cy - int(s * 0.45), int(s * 0.4), int(s * 0.4)
        ),
    )
    pygame.draw.circle(
        screen, (120, 115, 135), (fist_x, cy - int(s * 0.5)), int(s * 0.18)
    )
    # Trunks (waistband)
    pygame.draw.ellipse(
        screen,
        (100, 80, 180),
        pygame.Rect(
            cx - int(s * 0.38), cy + int(s * 0.35), int(s * 0.76), int(s * 0.2)
        ),
    )
    # Outline
    pygame.draw.polygon(screen, (100, 95, 115), torso_pts, 2)
    pygame.draw.circle(
        screen, (100, 95, 115), (cx, cy - int(s * 0.38)), int(s * 0.35), 2
    )


def _draw_nidoran(screen, cx, cy, size, facing_left):
    s = size
    # Purple body
    pygame.draw.ellipse(
        screen,
        (180, 100, 180),
        pygame.Rect(cx - int(s * 0.5), cy - int(s * 0.3), int(s * 1.0), int(s * 0.7)),
    )
    # Head
    pygame.draw.circle(screen, (180, 100, 180), (cx, cy - int(s * 0.32)), int(s * 0.38))
    # Horn on forehead
    horn_x = _flip(int(s * 0.15), cx, facing_left)
    horn_pts = [
        (horn_x - 6, cy - int(s * 0.55)),
        (horn_x + 6, cy - int(s * 0.55)),
        (horn_x, cy - int(s * 0.85)),
    ]
    pygame.draw.polygon(screen, (150, 70, 150), horn_pts)
    # Big ears
    ear_x = _flip(-int(s * 0.2), cx, facing_left)
    pygame.draw.ellipse(
        screen, (200, 140, 210), pygame.Rect(ear_x - 9, cy - int(s * 0.72), 18, 28)
    )
    pygame.draw.ellipse(
        screen, (240, 180, 240), pygame.Rect(ear_x - 5, cy - int(s * 0.7), 10, 20)
    )
    # Spots on body
    for px2, py2 in [(cx + int(s * 0.2), cy), (cx - int(s * 0.15), cy + int(s * 0.1))]:
        pygame.draw.circle(screen, (140, 70, 140), (px2, py2), 5)
    # Eye
    ex = _flip(int(s * 0.14), cx, facing_left)
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.35)), int(s * 0.1))
    pygame.draw.circle(screen, COL_WHITE, (ex + 2, cy - int(s * 0.37)), int(s * 0.04))
    # Outline
    pygame.draw.ellipse(
        screen,
        (130, 60, 130),
        pygame.Rect(cx - int(s * 0.5), cy - int(s * 0.3), int(s * 1.0), int(s * 0.7)),
        2,
    )
    pygame.draw.circle(
        screen, (130, 60, 130), (cx, cy - int(s * 0.32)), int(s * 0.38), 2
    )


def _draw_generic(screen, cx, cy, size, facing_left):
    """Fallback: draw a stylized creature with eyes and mouth."""
    s = size
    # Use a neutral blue-gray color
    body_col = (120, 130, 160)
    # Body
    pygame.draw.ellipse(
        screen,
        body_col,
        pygame.Rect(cx - int(s * 0.5), cy - int(s * 0.4), int(s * 1.0), int(s * 0.85)),
    )
    # Head
    pygame.draw.circle(screen, body_col, (cx, cy - int(s * 0.42)), int(s * 0.38))
    # Eyes
    ex = _flip(int(s * 0.15), cx, facing_left)
    pygame.draw.circle(screen, COL_WHITE, (ex, cy - int(s * 0.46)), int(s * 0.12))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.44)), int(s * 0.07))
    # Mouth
    pygame.draw.arc(
        screen,
        COL_BLACK,
        pygame.Rect(
            cx - int(s * 0.12), cy - int(s * 0.25), int(s * 0.24), int(s * 0.15)
        ),
        math.pi,
        2 * math.pi,
        2,
    )
    # Outline
    pygame.draw.ellipse(
        screen,
        (70, 80, 110),
        pygame.Rect(cx - int(s * 0.5), cy - int(s * 0.4), int(s * 1.0), int(s * 0.85)),
        2,
    )
    pygame.draw.circle(
        screen, (70, 80, 110), (cx, cy - int(s * 0.42)), int(s * 0.38), 2
    )


# Also add entries for the starter evolutions / extras using existing drawers
def _draw_blaziken(screen, cx, cy, size, facing_left):
    """Blaziken: tall fire-fighting bird, orange-red feathers."""
    s = size
    # Body — upright, orange-red
    pygame.draw.ellipse(
        screen,
        (220, 80, 20),
        pygame.Rect(cx - int(s * 0.38), cy - int(s * 0.5), int(s * 0.76), int(s * 1.1)),
    )
    # Chest feathers — cream
    pygame.draw.ellipse(
        screen,
        (255, 210, 170),
        pygame.Rect(cx - int(s * 0.22), cy - int(s * 0.4), int(s * 0.44), int(s * 0.7)),
    )
    # Head — bird-like, small
    pygame.draw.circle(screen, (220, 80, 20), (cx, cy - int(s * 0.62)), int(s * 0.3))
    # Head feathers tuft
    for i in range(3):
        fx = cx + (i - 1) * 8
        pygame.draw.line(
            screen, (250, 50, 0), (fx, cy - int(s * 0.82)), (fx, cy - int(s * 1.05)), 5
        )
    # Eyes
    ex = _flip(int(s * 0.12), cx, facing_left)
    pygame.draw.circle(screen, (255, 60, 0), (ex, cy - int(s * 0.65)), int(s * 0.1))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.63)), int(s * 0.06))
    # Leg flame — at bottom
    fl_pts = [
        (cx - int(s * 0.15), cy + int(s * 0.55)),
        (cx + int(s * 0.15), cy + int(s * 0.55)),
        (cx + int(s * 0.08), cy + int(s * 0.8)),
        (cx, cy + int(s * 0.95)),
        (cx - int(s * 0.08), cy + int(s * 0.8)),
    ]
    pygame.draw.polygon(screen, (255, 180, 0), fl_pts)
    pygame.draw.polygon(
        screen,
        (255, 100, 0),
        [
            (cx - int(s * 0.08), cy + int(s * 0.6)),
            (cx + int(s * 0.08), cy + int(s * 0.6)),
            (cx, cy + int(s * 0.85)),
        ],
    )
    # Outline
    pygame.draw.ellipse(
        screen,
        (150, 50, 10),
        pygame.Rect(cx - int(s * 0.38), cy - int(s * 0.5), int(s * 0.76), int(s * 1.1)),
        2,
    )
    pygame.draw.circle(screen, (150, 50, 10), (cx, cy - int(s * 0.62)), int(s * 0.3), 2)


def _draw_feraligatr(screen, cx, cy, size, facing_left):
    """Feraligatr: blue croc/gator body."""
    s = size
    # Body
    pygame.draw.ellipse(
        screen,
        (70, 120, 210),
        pygame.Rect(cx - int(s * 0.55), cy - int(s * 0.4), int(s * 1.1), int(s * 0.9)),
    )
    # Cream jaw
    jaw_pts = [
        (_flip(int(s * 0.3), cx, facing_left), cy + int(s * 0.0)),
        (_flip(int(s * 0.55), cx, facing_left), cy - int(s * 0.05)),
        (_flip(int(s * 0.55), cx, facing_left), cy + int(s * 0.25)),
        (_flip(int(s * 0.3), cx, facing_left), cy + int(s * 0.3)),
    ]
    pygame.draw.polygon(screen, (210, 225, 255), jaw_pts)
    # Snout teeth
    for i in range(3):
        tx = _flip(int(s * 0.38) + i * 6, cx, facing_left)
        pygame.draw.polygon(
            screen,
            COL_WHITE,
            [
                (tx - 2, cy + int(s * 0.02)),
                (tx + 2, cy + int(s * 0.02)),
                (tx, cy + int(s * 0.12)),
            ],
        )
    # Head
    pygame.draw.circle(screen, (70, 120, 210), (cx, cy - int(s * 0.42)), int(s * 0.38))
    # Ridge spines on back
    for i in range(3):
        sx2 = cx + (i - 1) * int(s * 0.25)
        pygame.draw.polygon(
            screen,
            (50, 90, 180),
            [
                (sx2 - 5, cy - int(s * 0.42)),
                (sx2 + 5, cy - int(s * 0.42)),
                (sx2, cy - int(s * 0.72)),
            ],
        )
    # Eye
    ex = _flip(int(s * 0.18), cx, facing_left)
    pygame.draw.circle(screen, (255, 100, 0), (ex, cy - int(s * 0.45)), int(s * 0.1))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.43)), int(s * 0.06))
    # Outline
    pygame.draw.ellipse(
        screen,
        (40, 80, 160),
        pygame.Rect(cx - int(s * 0.55), cy - int(s * 0.4), int(s * 1.1), int(s * 0.9)),
        2,
    )
    pygame.draw.circle(
        screen, (40, 80, 160), (cx, cy - int(s * 0.42)), int(s * 0.38), 2
    )


def _draw_sceptile(screen, cx, cy, size, facing_left):
    """Sceptile: green bipedal lizard with leaf blades."""
    s = size
    # Body — slim, tall
    pygame.draw.ellipse(
        screen,
        (80, 175, 60),
        pygame.Rect(
            cx - int(s * 0.33), cy - int(s * 0.55), int(s * 0.66), int(s * 1.1)
        ),
    )
    # Yellow belly
    pygame.draw.ellipse(
        screen,
        (230, 210, 90),
        pygame.Rect(
            cx - int(s * 0.18), cy - int(s * 0.38), int(s * 0.36), int(s * 0.65)
        ),
    )
    # Head
    pygame.draw.circle(screen, (80, 175, 60), (cx, cy - int(s * 0.62)), int(s * 0.32))
    # Leaf blades on arms
    for side in [-1, 1]:
        blade_x = cx + side * int(s * 0.5)
        blade_y = cy - int(s * 0.2)
        pts = [
            (blade_x, blade_y - int(s * 0.35)),
            (blade_x + side * 12, blade_y),
            (blade_x, blade_y + int(s * 0.1)),
        ]
        pygame.draw.polygon(screen, (50, 140, 40), pts)
    # Eye
    ex = _flip(int(s * 0.14), cx, facing_left)
    pygame.draw.circle(screen, (255, 200, 0), (ex, cy - int(s * 0.65)), int(s * 0.1))
    pygame.draw.circle(screen, COL_BLACK, (ex, cy - int(s * 0.63)), int(s * 0.06))
    # Tail leaf
    tail_x = _flip(-int(s * 0.38), cx, facing_left)
    pygame.draw.polygon(
        screen,
        (50, 140, 40),
        [
            (tail_x, cy + int(s * 0.5)),
            (tail_x - (18 if facing_left else -18), cy + int(s * 0.3)),
            (tail_x - (12 if facing_left else -12), cy + int(s * 0.65)),
        ],
    )
    # Outline
    pygame.draw.ellipse(
        screen,
        (40, 110, 30),
        pygame.Rect(
            cx - int(s * 0.33), cy - int(s * 0.55), int(s * 0.66), int(s * 1.1)
        ),
        2,
    )
    pygame.draw.circle(
        screen, (40, 110, 30), (cx, cy - int(s * 0.62)), int(s * 0.32), 2
    )


def _draw_raichu(screen, cx, cy, size, facing_left):
    """Raichu: larger, rounder pikachu evolution."""
    s = size
    # Fatter orange-yellow body
    pygame.draw.ellipse(
        screen,
        (240, 180, 50),
        pygame.Rect(
            cx - int(s * 0.52), cy - int(s * 0.35), int(s * 1.04), int(s * 0.75)
        ),
    )
    # Head
    pygame.draw.circle(screen, (240, 180, 50), (cx, cy - int(s * 0.38)), int(s * 0.44))
    # Small ears
    for ex_dir in [-1, 1]:
        ear_x = cx + ex_dir * int(s * 0.3)
        pygame.draw.circle(
            screen, (40, 20, 20), (ear_x, cy - int(s * 0.7)), int(s * 0.12)
        )
        pygame.draw.circle(
            screen, (240, 180, 50), (ear_x, cy - int(s * 0.68)), int(s * 0.08)
        )
    # Red cheeks
    chk = _flip(int(s * 0.3), cx, facing_left)
    pygame.draw.circle(screen, (240, 80, 80), (chk, cy - int(s * 0.22)), int(s * 0.16))
    chk2 = _flip(-int(s * 0.3), cx, facing_left)
    pygame.draw.circle(screen, (240, 80, 80), (chk2, cy - int(s * 0.22)), int(s * 0.16))
    # Eye
    ex2 = _flip(int(s * 0.18), cx, facing_left)
    pygame.draw.circle(screen, COL_BLACK, (ex2, cy - int(s * 0.4)), int(s * 0.1))
    pygame.draw.circle(screen, COL_WHITE, (ex2 + 2, cy - int(s * 0.42)), int(s * 0.04))
    # Heavy long tail
    tx = _flip(-int(s * 0.52), cx, facing_left)
    dir_x = -1 if facing_left else 1
    pygame.draw.line(
        screen,
        (200, 140, 30),
        (tx, cy + int(s * 0.05)),
        (tx + dir_x * int(s * 0.5), cy - int(s * 0.3)),
        6,
    )
    # Outline
    pygame.draw.circle(
        screen, (180, 130, 20), (cx, cy - int(s * 0.38)), int(s * 0.44), 2
    )
    pygame.draw.ellipse(
        screen,
        (180, 130, 20),
        pygame.Rect(
            cx - int(s * 0.52), cy - int(s * 0.35), int(s * 1.04), int(s * 0.75)
        ),
        2,
    )


# Sprite registry maps lowercase name -> draw function
_SPRITE_REGISTRY = {
    "charmander": _draw_charmander,
    "squirtle": _draw_squirtle,
    "bulbasaur": _draw_bulbasaur,
    "pikachu": _draw_pikachu,
    "rattata": _draw_rattata,
    "pidgey": _draw_pidgey,
    "caterpie": _draw_caterpie,
    "geodude": _draw_geodude,
    "zubat": _draw_zubat,
    "gastly": _draw_gastly,
    "machop": _draw_machop,
    "nidoran": _draw_nidoran,
    "blaziken": _draw_blaziken,
    "feraligatr": _draw_feraligatr,
    "sceptile": _draw_sceptile,
    "raichu": _draw_raichu,
}


# ── BattleScene ───────────────────────────────────────────────────────────────


class BattleScene(Scene):
    """
    Turn-based battle scene.

    After construction the caller must register and switch to this scene.
    The scene switches back to "overworld" when the battle ends.
    """

    custom_draw = True  # we handle all rendering ourselves

    def __init__(
        self,
        player_party: list["Pokemon"] | None = None,
        wild_pokemon: "Pokemon | None" = None,
        pokeballs: int = 5,
    ):
        super().__init__()

        self.player_party = player_party or []
        self.wild = wild_pokemon
        self.pokeballs = pokeballs
        # Aliases used by overworld to set before pushing
        self.party = self.player_party

        # Active pokemon indices
        self._player_idx = 0

        # State machine
        self._state = State.INTRO
        self._prev_state = State.INTRO

        # UI selection cursors
        self._action_idx = 0  # 0-3 (FIGHT/BAG/POKEMON/RUN)
        self._move_idx = 0  # 0-3
        self._party_idx = 0  # 0-5

        # Message queue & typewriter
        self._messages: list[str] = []
        self._current_msg = ""
        self._displayed = ""  # partial typewriter text
        self._type_timer = 0.0
        self._type_speed = 0.04  # seconds per character
        self._msg_done = False  # typewriter finished

        # HP bar animation (initialized properly in enter())
        self._player_hp_display = 0.0
        self._enemy_hp_display = 0.0

        # Slide-in animation (intro)
        self._intro_timer = 0.0
        self._intro_done = False
        self._enemy_slide = float(W)  # starts off-screen right
        self._player_slide = float(-W)  # starts off-screen left

        # Hit flash / shake
        self._flash_timer = 0.0  # overlay alpha (0-255)
        self._flash_color = (255, 255, 255)  # white by default
        self._shake_timer = 0.0
        self._shake_target = "none"  # "player" | "enemy"

        # Encounter flash at start
        self._encounter_flash = 1.0  # 0..1, fades quickly

        # XP gain messages buffered for VICTORY flow
        self._post_messages: list[str] = []

        # Catch animation timer
        self._catch_timer = 0.0
        self._catch_result = False

        # Deferred next state after MESSAGE drains
        self._after_message: State = State.CHOOSE_ACTION

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def state(self) -> str:
        """String state name for external readers (e.g. autoplay bot)."""
        return self._state.name if self._state else "UNKNOWN"

    @property
    def _player(self) -> "Pokemon":
        return self.player_party[self._player_idx]

    @property
    def _screen(self) -> pygame.Surface:
        return self.game.screen  # type: ignore[union-attr]

    # ── Scene lifecycle ───────────────────────────────────────────────────────

    def enter(self):
        # Sync party reference (overworld sets self.party before push)
        if self.party:
            self.player_party = self.party
        self._player_idx = 0
        # Find first non-fainted pokemon
        for i, p in enumerate(self.player_party):
            if not p.is_fainted:
                self._player_idx = i
                break
        self._state = State.INTRO
        self._action_idx = 0
        self._move_idx = 0
        self._messages.clear()
        self._current_msg = ""
        self._displayed = ""
        self._player_hp_display = float(self._player.hp)
        self._enemy_hp_display = float(self.wild.hp) if self.wild else 0
        self._encounter_flash = 1.0  # bright flash on encounter start
        self._push_message(
            f"A wild {self.wild.name} appeared!",
            after=State.CHOOSE_ACTION,
        )

    def exit(self):
        pass

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float):
        inp = self.game.input  # type: ignore[union-attr]

        # Always animate HP bars toward real values
        speed = 80.0 * dt  # HP units per second
        self._player_hp_display = _lerp(
            self._player_hp_display,
            float(self._player.hp),
            min(1.0, speed / max(1, self._player.max_hp)),
        )
        self._enemy_hp_display = _lerp(
            self._enemy_hp_display,
            float(self.wild.hp),
            min(1.0, speed / max(1, self.wild.max_hp)),
        )

        # Flash / shake timers
        if self._flash_timer > 0:
            self._flash_timer = max(0.0, self._flash_timer - dt * 400)
        if self._shake_timer > 0:
            self._shake_timer = max(0.0, self._shake_timer - dt)

        # Encounter flash decay
        if self._encounter_flash > 0:
            self._encounter_flash = max(0.0, self._encounter_flash - dt * 3.0)

        # Dispatch to state handlers
        if self._state == State.INTRO:
            self._update_intro(dt)
        elif self._state == State.CHOOSE_ACTION:
            self._update_choose_action(inp)
        elif self._state == State.CHOOSE_MOVE:
            self._update_choose_move(inp)
        elif self._state == State.CHOOSE_POKEMON:
            self._update_choose_pokemon(inp)
        elif self._state == State.ENEMY_TURN:
            self._update_enemy_turn()
        elif self._state == State.ANIMATING:
            self._update_animating(dt)
        elif self._state == State.MESSAGE:
            self._update_message(dt, inp)
        elif self._state == State.CATCH:
            self._update_catch(dt)
        elif self._state == State.VICTORY:
            self._update_victory(inp)
        elif self._state == State.DEFEAT:
            self._update_defeat(inp)

    # ── State: INTRO ──────────────────────────────────────────────────────────

    def _update_intro(self, dt: float):
        self._intro_timer += dt
        # Slide both pokemon in
        target_ex = float(ENEMY_CENTER[0])
        target_px = float(PLAYER_CENTER[0])
        t = min(1.0, self._intro_timer / 1.0)  # 1 second slide
        ease = 1 - (1 - t) ** 3  # cubic ease-out
        self._enemy_slide = _lerp(float(W + ENEMY_RADIUS), target_ex, ease)
        self._player_slide = _lerp(float(-PLAYER_RADIUS), target_px, ease)
        if t >= 1.0 and not self._intro_done:
            self._intro_done = True
            self._set_state(State.MESSAGE)

    # ── State: MESSAGE ────────────────────────────────────────────────────────

    def _push_message(self, msg: str, after: State = State.CHOOSE_ACTION):
        self._messages.append(msg)
        self._after_message = after

    def _set_state(self, state: State):
        self._prev_state = self._state
        self._state = state
        if state == State.MESSAGE:
            self._advance_message()

    def _advance_message(self):
        if self._messages:
            self._current_msg = self._messages.pop(0)
            self._displayed = ""
            self._type_timer = 0.0
            self._msg_done = False
        else:
            # Queue drained — handle end states
            target = self._after_message

            if target == State.VICTORY:
                # Only give XP once
                if not getattr(self, "_victory_xp_given", False):
                    self._state = State.VICTORY
                    return
                # Second drain after XP messages — go back to overworld
                self._state = State.CHOOSE_ACTION  # placeholder
                self.game.scenes.switch("overworld")  # type: ignore[union-attr]
                return

            if target == State.DEFEAT:
                if getattr(self, "_defeat_shown", False):
                    self.game.scenes.switch("overworld")  # type: ignore[union-attr]
                    return

            # Special: RUN exit
            if self._post_messages and self._post_messages[0] == "__EXIT__":
                self._post_messages.pop(0)
                self.game.scenes.switch("overworld")  # type: ignore[union-attr]
                return

            self._state = target
            self._current_msg = ""
            self._displayed = ""

    def _update_message(self, dt: float, inp):
        if not self._msg_done:
            self._type_timer += dt
            chars_to_show = int(self._type_timer / self._type_speed)
            self._displayed = self._current_msg[:chars_to_show]
            if len(self._displayed) >= len(self._current_msg):
                self._displayed = self._current_msg
                self._msg_done = True
        else:
            # Wait for confirm or auto-advance
            if inp.is_action_just_pressed("action"):
                self._advance_message()

    # ── State: CHOOSE_ACTION ──────────────────────────────────────────────────

    def _update_choose_action(self, inp):
        if inp.is_action_just_pressed("move_right"):
            self._action_idx = (self._action_idx + 1) % 4
        if inp.is_action_just_pressed("move_left"):
            self._action_idx = (self._action_idx - 1) % 4
        if inp.is_action_just_pressed("move_down"):
            self._action_idx = (self._action_idx + 2) % 4
        if inp.is_action_just_pressed("move_up"):
            self._action_idx = (self._action_idx - 2) % 4

        if inp.is_action_just_pressed("action"):
            choice = ACTION_LABELS[self._action_idx]
            if choice == "FIGHT":
                self._move_idx = 0
                self._set_state(State.CHOOSE_MOVE)
            elif choice == "BAG":
                if self.pokeballs <= 0:
                    self._push_message("No Pokeballs left!", after=State.CHOOSE_ACTION)
                    self._set_state(State.MESSAGE)
                else:
                    self._set_state(State.CATCH)
            elif choice == "POKEMON":
                self._party_idx = self._player_idx
                self._set_state(State.CHOOSE_POKEMON)
            elif choice == "RUN":
                self._push_message("Got away safely!", after=State.CHOOSE_ACTION)
                self._set_state(State.MESSAGE)
                self._after_message = State.CHOOSE_ACTION
                # Schedule the overworld switch after messages drain
                self._post_messages = ["__EXIT__"]

        if inp.is_action_just_pressed("cancel"):
            pass  # nothing to cancel from top menu

    # ── State: CHOOSE_MOVE ────────────────────────────────────────────────────

    def _update_choose_move(self, inp):
        moves = self._player.moves
        n = len(moves)

        if inp.is_action_just_pressed("move_right") and self._move_idx % 2 < 1:
            self._move_idx = min(n - 1, self._move_idx + 1)
        if inp.is_action_just_pressed("move_left") and self._move_idx % 2 > 0:
            self._move_idx = max(0, self._move_idx - 1)
        if inp.is_action_just_pressed("move_down"):
            self._move_idx = min(n - 1, self._move_idx + 2)
        if inp.is_action_just_pressed("move_up"):
            self._move_idx = max(0, self._move_idx - 2)

        if inp.is_action_just_pressed("action"):
            move = moves[self._move_idx]
            if move.pp_current <= 0:
                self._push_message("No PP left for that move!", after=State.CHOOSE_MOVE)
                self._set_state(State.MESSAGE)
                return
            self._execute_player_move(move)

        if inp.is_action_just_pressed("cancel"):
            self._set_state(State.CHOOSE_ACTION)

    # ── State: CHOOSE_POKEMON ────────────────────────────────────────────────

    def _update_choose_pokemon(self, inp):
        party = self.player_party
        n = len(party)

        if inp.is_action_just_pressed("move_down"):
            self._party_idx = min(n - 1, self._party_idx + 1)
        if inp.is_action_just_pressed("move_up"):
            self._party_idx = max(0, self._party_idx - 1)

        if inp.is_action_just_pressed("action"):
            idx = self._party_idx
            target = party[idx]
            if target.is_fainted:
                self._push_message(
                    f"{target.name} has fainted!", after=State.CHOOSE_POKEMON
                )
                self._set_state(State.MESSAGE)
                return
            if idx == self._player_idx:
                self._push_message(
                    f"{target.name} is already in battle!", after=State.CHOOSE_POKEMON
                )
                self._set_state(State.MESSAGE)
                return
            self._player_idx = idx
            self._player_hp_display = float(self._player.hp)
            msgs = [f"Go, {self._player.name}!"]
            for m in msgs:
                self._messages.append(m)
            self._after_message = State.ENEMY_TURN
            self._set_state(State.MESSAGE)

        if inp.is_action_just_pressed("cancel"):
            self._set_state(State.CHOOSE_ACTION)

    # ── Player move execution ─────────────────────────────────────────────────

    def _execute_player_move(self, move):
        from core.moves import calc_damage  # local import — stays clean

        move.pp_current -= 1
        dmg, eff, crit = calc_damage(self._player, self.wild, move)

        self.wild.hp = max(0, self.wild.hp - dmg)

        msgs = []
        msgs.append(f"{self._player.name} used {move.name}!")
        if dmg == 0:
            msgs.append(f"{self._player.name}'s attack missed!")
        else:
            if crit:
                msgs.append("A critical hit!")
                self._flash_color = (255, 60, 60)  # red flash for crit
                self._flash_timer = 200.0
            if eff > 1.5:
                msgs.append("It's super effective!")
                self._shake_target = "enemy"
                self._shake_timer = 0.35
                self._flash_color = (255, 240, 80)  # yellow flash for super effective
                self._flash_timer = 180.0
            elif eff < 0.5:
                msgs.append("It's not very effective...")
                self._flash_color = (180, 180, 180)  # gray for not very effective
                self._flash_timer = 140.0
            else:
                # Normal hit flash
                self._flash_color = (255, 255, 255)
                self._flash_timer = 180.0

        for m in msgs:
            self._messages.append(m)

        if self.wild.is_fainted:
            self._messages.append(f"Wild {self.wild.name} fainted!")
            self._after_message = State.VICTORY
        else:
            self._after_message = State.ENEMY_TURN

        self._set_state(State.MESSAGE)

    # ── State: ENEMY_TURN ────────────────────────────────────────────────────

    def _update_enemy_turn(self):
        from core.moves import calc_damage

        valid = [m for m in self.wild.moves if m.pp_current > 0]
        if not valid:
            # Struggle — 40 normal dmg
            from core.moves import Move as MoveClass

            struggle = MoveClass("Struggle", "normal", 40, 100, 1, 1, "physical")
            valid = [struggle]

        move = random.choice(valid)
        move.pp_current = max(0, move.pp_current - 1)

        dmg, eff, crit = calc_damage(self.wild, self._player, move)
        self._player.hp = max(0, self._player.hp - dmg)

        msgs = [f"Wild {self.wild.name} used {move.name}!"]
        if dmg == 0:
            msgs.append("The attack missed!")
        else:
            if crit:
                msgs.append("A critical hit!")
                self._flash_color = (255, 60, 60)
                self._flash_timer = 200.0
            if eff > 1.5:
                msgs.append("It's super effective!")
                self._shake_target = "player"
                self._shake_timer = 0.35
                self._flash_color = (255, 240, 80)
                self._flash_timer = 180.0
            elif eff < 0.5:
                msgs.append("It's not very effective...")
                self._flash_color = (180, 180, 180)
                self._flash_timer = 140.0
            else:
                self._flash_color = (255, 255, 255)
                self._flash_timer = 140.0

        for m in msgs:
            self._messages.append(m)

        if self._player.is_fainted:
            self._messages.append(f"{self._player.name} fainted!")
            # Check if any alive party members remain
            alive = [p for p in self.player_party if not p.is_fainted]
            if not alive:
                self._after_message = State.DEFEAT
            else:
                # Force switch
                self._after_message = State.CHOOSE_POKEMON
        else:
            self._after_message = State.CHOOSE_ACTION

        self._set_state(State.MESSAGE)

    # ── State: ANIMATING ─────────────────────────────────────────────────────

    def _update_animating(self, dt: float):
        # Currently unused — HP bars animate passively
        pass

    # ── State: CATCH ─────────────────────────────────────────────────────────

    def _update_catch(self, dt: float):
        # Instantly resolve catch, then push messages and return
        self.pokeballs -= 1
        success = _catch_success(self.wild, self.pokeballs + 1)  # use before decrement

        if success:
            if len(self.player_party) < 6:
                self.player_party.append(self.wild)
                self._push_message(
                    f"Gotcha! {self.wild.name} was caught!",
                    after=State.VICTORY,
                )
            else:
                self._push_message(
                    f"Gotcha! {self.wild.name} was caught! (Party full — released)",
                    after=State.VICTORY,
                )
            self._after_message = State.VICTORY
        else:
            self._push_message(
                f"Oh no! {self.wild.name} broke free!",
                after=State.ENEMY_TURN,
            )
            self._after_message = State.ENEMY_TURN

        self._set_state(State.MESSAGE)

    # ── State: VICTORY ────────────────────────────────────────────────────────

    def _update_victory(self, inp):
        # Give XP to active player pokemon — called exactly once
        xp_gained = self.wild.species.xp_yield
        msgs = [f"{self._player.name} gained {xp_gained} XP!"]
        level_msgs = self._player.gain_xp(xp_gained)
        msgs.extend(level_msgs)

        for m in msgs:
            self._messages.append(m)

        self._messages.append("Battle over! Returning...")
        # Mark before transitioning so _advance_message knows XP was given
        self._victory_xp_given = True
        self._after_message = State.VICTORY  # sentinel — triggers overworld switch

        self._set_state(State.MESSAGE)

    def _update_defeat(self, inp):
        self._messages.append("You have no Pokemon left to fight!")
        self._messages.append("Blacking out...")
        self._after_message = State.DEFEAT
        self._set_state(State.MESSAGE)
        self._defeat_shown = True

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self):
        screen = self._screen
        t = self.game.time  # type: ignore[union-attr]

        self._draw_background(screen)
        self._draw_pokemon(screen, t)
        self._draw_hp_plates(screen)
        self._draw_menu(screen, t)
        self._draw_hit_flash(screen)

        # Encounter flash (white overlay that fades in quickly at battle start)
        if self._encounter_flash > 0:
            alpha = int(self._encounter_flash * 255)
            ef_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            ef_surf.fill((255, 255, 255, alpha))
            screen.blit(ef_surf, (0, 0))

    # ── Background ────────────────────────────────────────────────────────────

    def _draw_background(self, screen: pygame.Surface):
        # Sky gradient top half
        sky_top = (100, 160, 220)
        sky_bot = (180, 210, 240)
        for y in range(H // 2):
            ratio = y / (H // 2)
            r = int(_lerp(sky_top[0], sky_bot[0], ratio))
            g = int(_lerp(sky_top[1], sky_bot[1], ratio))
            b = int(_lerp(sky_top[2], sky_bot[2], ratio))
            pygame.draw.line(screen, (r, g, b), (0, y), (W, y))

        # Ground — top half (enemy side): darker green
        enemy_ground_top = (80, 150, 70)
        enemy_ground_bot = (100, 170, 85)
        for y in range(H // 2, int(H * 0.58)):
            ratio = (y - H // 2) / (H * 0.08)
            r = int(_lerp(enemy_ground_top[0], enemy_ground_bot[0], ratio))
            g = int(_lerp(enemy_ground_top[1], enemy_ground_bot[1], ratio))
            b = int(_lerp(enemy_ground_top[2], enemy_ground_bot[2], ratio))
            pygame.draw.line(screen, (r, g, b), (0, y), (W, y))

        # Ground — bottom half (player side): lighter green
        player_ground_top = (120, 190, 100)
        player_ground_bot = (90, 155, 75)
        for y in range(int(H * 0.58), H):
            ratio = (y - H * 0.58) / (H * 0.42)
            r = int(_lerp(player_ground_top[0], player_ground_bot[0], ratio))
            g = int(_lerp(player_ground_top[1], player_ground_bot[1], ratio))
            b = int(_lerp(player_ground_top[2], player_ground_bot[2], ratio))
            pygame.draw.line(screen, (r, g, b), (0, y), (W, y))

        # Dividing line between two sides
        pygame.draw.line(
            screen, (60, 120, 50), (0, int(H * 0.58)), (W, int(H * 0.58)), 2
        )

        # Subtle grid texture on ground (player side)
        grid_col = (100, 165, 80)
        grid_y_start = int(H * 0.58)
        for gx in range(0, W, 60):
            pygame.draw.line(screen, grid_col, (gx, grid_y_start), (gx, H), 1)
        for gy in range(grid_y_start, H, 40):
            pygame.draw.line(screen, grid_col, (0, gy), (W, gy), 1)

        # Enemy side subtle grid
        enemy_grid = (70, 135, 60)
        for gx in range(0, W, 60):
            pygame.draw.line(screen, enemy_grid, (gx, H // 2), (gx, int(H * 0.58)), 1)

        # Ground shadow ellipse under enemy pokemon
        pygame.draw.ellipse(
            screen,
            (55, 110, 45),
            pygame.Rect(ENEMY_CENTER[0] - 65, ENEMY_CENTER[1] + 42, 130, 24),
        )
        # Ground shadow ellipse under player pokemon
        pygame.draw.ellipse(
            screen,
            (80, 145, 65),
            pygame.Rect(PLAYER_CENTER[0] - 85, PLAYER_CENTER[1] + 55, 170, 32),
        )

        # Ground platform highlight rings
        pygame.draw.ellipse(
            screen,
            (140, 210, 120),
            pygame.Rect(ENEMY_CENTER[0] - 62, ENEMY_CENTER[1] + 40, 124, 22),
            2,
        )
        pygame.draw.ellipse(
            screen,
            (160, 225, 140),
            pygame.Rect(PLAYER_CENTER[0] - 82, PLAYER_CENTER[1] + 53, 164, 30),
            2,
        )

    # ── Pokemon sprites ───────────────────────────────────────────────────────

    def _draw_pokemon(self, screen: pygame.Surface, t: float):
        # --- Enemy pokemon ---
        ex = int(self._enemy_slide)
        ey = ENEMY_CENTER[1]

        if self._shake_target == "enemy" and self._shake_timer > 0:
            ex += int(math.sin(self._shake_timer * 60) * 6)

        if not self.wild.is_fainted:
            _draw_pokemon_sprite(
                screen,
                self.wild.name,
                ex,
                ey,
                ENEMY_RADIUS,
                facing_left=True,
                is_fainted=False,
            )
        else:
            _draw_pokemon_sprite(
                screen,
                self.wild.name,
                ex,
                ey,
                ENEMY_RADIUS,
                facing_left=True,
                is_fainted=True,
            )

        # --- Player pokemon ---
        px = int(self._player_slide)
        py = PLAYER_CENTER[1]

        if self._shake_target == "player" and self._shake_timer > 0:
            px += int(math.sin(self._shake_timer * 60) * 6)

        # Idle bob animation
        bob = int(math.sin(t * 2.5) * 4)
        py += bob

        if not self._player.is_fainted:
            _draw_pokemon_sprite(
                screen,
                self._player.name,
                px,
                py,
                PLAYER_RADIUS,
                facing_left=False,
                is_fainted=False,
            )
        else:
            _draw_pokemon_sprite(
                screen,
                self._player.name,
                px,
                py,
                PLAYER_RADIUS,
                facing_left=False,
                is_fainted=True,
            )

    # ── HP plates ─────────────────────────────────────────────────────────────

    def _draw_hp_plates(self, screen: pygame.Surface):
        # Enemy plate — top-left area
        self._draw_name_plate(
            screen,
            x=20,
            y=20,
            pokemon=self.wild,
            hp_display=self._enemy_hp_display,
            show_hp_num=False,
            show_exp=False,
        )

        # Player plate — bottom-right area
        self._draw_name_plate(
            screen,
            x=480,
            y=290,
            pokemon=self._player,
            hp_display=self._player_hp_display,
            show_hp_num=True,
            show_exp=True,
        )

    def _draw_name_plate(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        pokemon: "Pokemon",
        hp_display: float,
        show_hp_num: bool,
        show_exp: bool = False,
    ):
        plate_w = 290
        plate_h = 105 if show_exp else 95

        # Background panel with rounded corners
        panel_rect = pygame.Rect(x, y, plate_w, plate_h)
        _draw_rounded_rect(screen, (18, 22, 30), panel_rect, radius=8)
        # White border
        _draw_rounded_rect(
            screen,
            COL_WHITE,
            panel_rect,
            radius=8,
            border=2,
            border_color=(200, 200, 210),
        )

        font_name = self._font(20)
        font_lv = self._font(16)
        font_hp = self._font(15)

        # Name
        name_surf = font_name.render(pokemon.name, True, COL_WHITE)
        screen.blit(name_surf, (x + 12, y + 10))

        # Level badge
        lv_text = f"Lv.{pokemon.level}"
        lv_surf = font_lv.render(lv_text, True, (200, 220, 255))
        screen.blit(lv_surf, (x + plate_w - lv_surf.get_width() - 12, y + 10))

        # HP label
        hp_lbl = font_hp.render("HP", True, (180, 200, 200))
        screen.blit(hp_lbl, (x + 12, y + 40))

        # HP bar background (dark, with border)
        bar_x = x + 40
        bar_y = y + 40
        bar_w = plate_w - 55
        bar_h = 10  # thicker than before
        pygame.draw.rect(screen, COL_HP_BG, pygame.Rect(bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(
            screen,
            (60, 65, 80),
            pygame.Rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2),
            1,
        )

        # HP bar fill
        pct = hp_display / pokemon.max_hp if pokemon.max_hp > 0 else 0
        pct = max(0.0, min(1.0, pct))
        fill_w = int(bar_w * pct)
        hp_col = _hp_color(pct)
        if fill_w > 0:
            # Main fill
            pygame.draw.rect(screen, hp_col, pygame.Rect(bar_x, bar_y, fill_w, bar_h))
            # Bright highlight on top 2px
            hi_col = tuple(min(255, c + 60) for c in hp_col)
            pygame.draw.rect(screen, hi_col, pygame.Rect(bar_x, bar_y, fill_w, 2))

        # HP numbers (player side only)
        if show_hp_num:
            hp_num = font_hp.render(
                f"{max(0, int(round(hp_display)))}/{pokemon.max_hp}",
                True,
                COL_WHITE,
            )
            screen.blit(hp_num, (x + 12, y + 58))

        # EXP bar (player side only)
        if show_exp:
            from core.pokemon import xp_for_level

            exp_y = y + plate_h - 14
            exp_label = self._font(12).render("EXP", True, (120, 140, 200))
            screen.blit(exp_label, (x + 12, exp_y))

            exp_bar_x = x + 44
            exp_bar_w = plate_w - 58
            exp_bar_h = 5
            pygame.draw.rect(
                screen,
                (30, 35, 50),
                pygame.Rect(exp_bar_x, exp_y + 2, exp_bar_w, exp_bar_h),
            )
            cur_xp = pokemon.xp - xp_for_level(pokemon.level)
            next_xp = xp_for_level(pokemon.level + 1) - xp_for_level(pokemon.level)
            exp_pct = max(0.0, min(1.0, cur_xp / max(1, next_xp)))
            exp_fill = int(exp_bar_w * exp_pct)
            if exp_fill > 0:
                pygame.draw.rect(
                    screen,
                    (80, 120, 240),
                    pygame.Rect(exp_bar_x, exp_y + 2, exp_fill, exp_bar_h),
                )
                # Highlight
                pygame.draw.rect(
                    screen,
                    (140, 180, 255),
                    pygame.Rect(exp_bar_x, exp_y + 2, exp_fill, 2),
                )
            pygame.draw.rect(
                screen,
                (60, 70, 100),
                pygame.Rect(exp_bar_x - 1, exp_y + 1, exp_bar_w + 2, exp_bar_h + 2),
                1,
            )

    # ── Menu / message box ────────────────────────────────────────────────────

    def _draw_menu(self, screen: pygame.Surface, t: float):
        # Dark menu box at bottom — rounded corners, white border
        menu_rect = MENU_BOX_RECT
        _draw_rounded_rect(screen, (18, 22, 30), menu_rect, radius=0)
        # Top border line
        pygame.draw.line(
            screen,
            (200, 210, 220),
            (menu_rect.x, menu_rect.y),
            (menu_rect.right, menu_rect.y),
            3,
        )

        state = self._state

        if state == State.MESSAGE or state == State.INTRO:
            self._draw_message_box(screen, t)
        elif state == State.CHOOSE_ACTION:
            self._draw_action_menu(screen, t)
        elif state == State.CHOOSE_MOVE:
            self._draw_move_menu(screen)
        elif state == State.CHOOSE_POKEMON:
            self._draw_party_menu(screen)
        elif state == State.CATCH:
            self._draw_message_box(screen, t)
        elif state == State.VICTORY:
            self._draw_message_box(screen, t)
        elif state == State.DEFEAT:
            self._draw_message_box(screen, t)

    def _draw_message_box(self, screen: pygame.Surface, t: float = 0.0):
        font = self._font(22)
        text = self._displayed if self._displayed else self._current_msg

        # Word-wrap: fit ~52 chars per line
        words = text.split(" ")
        lines: list[str] = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 <= 52:
                cur = (cur + " " + w).strip()
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)

        my = MENU_BOX_RECT.y + 22
        for line in lines[:4]:
            surf = font.render(line, True, COL_WHITE)
            screen.blit(surf, (MENU_BOX_RECT.x + 28, my))
            my += 34

        # Blinking triangle cursor when done
        if self._msg_done and int(t * 4) % 2 == 0:
            tri_x = MENU_BOX_RECT.right - 32
            tri_y = MENU_BOX_RECT.bottom - 28
            pygame.draw.polygon(
                screen,
                COL_WHITE,
                [(tri_x, tri_y), (tri_x + 12, tri_y), (tri_x + 6, tri_y + 12)],
            )

    def _draw_action_menu(self, screen: pygame.Surface, t: float = 0.0):
        # Left side: prompt text
        font_prompt = self._font(22)
        name_text = self._player.name
        surf = font_prompt.render("What will", True, COL_WHITE)
        screen.blit(surf, (28, MENU_BOX_RECT.y + 22))
        surf2 = font_prompt.render(f"{name_text} do?", True, COL_WHITE)
        screen.blit(surf2, (28, MENU_BOX_RECT.y + 52))

        # Right side: 2x2 grid of action buttons
        font_btn = self._font(22)
        btn_w, btn_h = 156, 62
        start_x = MENU_BOX_RECT.x + 440
        start_y = MENU_BOX_RECT.y + 14

        for i, label in enumerate(ACTION_LABELS):
            col_i = i % 2
            row_i = i // 2
            bx = start_x + col_i * (btn_w + 8)
            by = start_y + row_i * (btn_h + 8)

            selected = i == self._action_idx
            base_col = ACTION_COLORS[label]

            # Darken if not selected, brighten if selected
            if selected:
                bg_col = tuple(min(255, c + 30) for c in base_col)
            else:
                bg_col = tuple(max(0, c - 50) for c in base_col)

            btn_rect = pygame.Rect(bx, by, btn_w, btn_h)
            _draw_rounded_rect(screen, bg_col, btn_rect, radius=6)

            if selected:
                # Bright border
                _draw_rounded_rect(
                    screen,
                    COL_SELECT,
                    btn_rect,
                    radius=6,
                    border=2,
                    border_color=COL_SELECT,
                )
            else:
                _draw_rounded_rect(
                    screen,
                    tuple(max(0, c - 30) for c in base_col),
                    btn_rect,
                    radius=6,
                    border=1,
                    border_color=tuple(max(0, c - 30) for c in base_col),
                )

            # Button label
            text_col = COL_WHITE if not selected else COL_SELECT
            txt_surf = font_btn.render(label, True, text_col)
            trect = txt_surf.get_rect(center=(bx + btn_w // 2, by + btn_h // 2))
            screen.blit(txt_surf, trect)

    def _draw_move_menu(self, screen: pygame.Surface):
        moves = self._player.moves
        font_n = self._font(19)
        font_pp = self._font(14)
        font_ty = self._font(13)

        # Left 3/4: move grid
        grid_w = int(W * 0.72)
        cell_w = (grid_w - 20) // 2
        cell_h = (MENU_BOX_RECT.height - 20) // 2
        ox, oy = MENU_BOX_RECT.x + 8, MENU_BOX_RECT.y + 8

        for i in range(4):
            col_i = i % 2
            row_i = i // 2
            cx = ox + col_i * (cell_w + 8)
            cy = oy + row_i * (cell_h + 6)

            if i < len(moves):
                move = moves[i]
                selected = i == self._move_idx
                tc = TYPE_COLORS.get(move.type, (168, 168, 168))
                bg = tuple(max(0, int(c * 0.4)) for c in tc)
                sel_bg = tuple(max(0, int(c * 0.55)) for c in tc)

                cell_rect = pygame.Rect(cx, cy, cell_w, cell_h)
                _draw_rounded_rect(
                    screen, sel_bg if selected else bg, cell_rect, radius=5
                )

                if selected:
                    _draw_rounded_rect(
                        screen,
                        COL_WHITE,
                        cell_rect,
                        radius=5,
                        border=2,
                        border_color=COL_WHITE,
                    )
                else:
                    _draw_rounded_rect(
                        screen, tc, cell_rect, radius=5, border=1, border_color=tc
                    )

                # Move name
                nsurf = font_n.render(move.name, True, COL_WHITE)
                screen.blit(nsurf, (cx + 8, cy + 8))

                # Type badge background
                type_text = move.type.upper()
                type_surf = font_ty.render(type_text, True, COL_BLACK)
                badge_w = type_surf.get_width() + 10
                badge_h = type_surf.get_height() + 4
                badge_x = cx + cell_w - badge_w - 6
                badge_y = cy + 8
                badge_rect = pygame.Rect(badge_x, badge_y, badge_w, badge_h)
                _draw_rounded_rect(screen, tc, badge_rect, radius=3)
                screen.blit(type_surf, (badge_x + 5, badge_y + 2))

                # PP counter
                pp_col = (
                    COL_HP_GREEN
                    if move.pp_current > move.pp // 2
                    else (COL_HP_YELLOW if move.pp_current > 0 else COL_HP_RED)
                )
                pp_surf = font_pp.render(
                    f"PP {move.pp_current}/{move.pp}", True, pp_col
                )
                screen.blit(pp_surf, (cx + 8, cy + cell_h - 22))

            else:
                # Empty slot
                cell_rect = pygame.Rect(cx, cy, cell_w, cell_h)
                _draw_rounded_rect(screen, (35, 40, 52), cell_rect, radius=5)
                _draw_rounded_rect(
                    screen,
                    COL_GRAY,
                    cell_rect,
                    radius=5,
                    border=1,
                    border_color=COL_GRAY,
                )
                dash = font_n.render("—", True, COL_GRAY)
                screen.blit(
                    dash, dash.get_rect(center=(cx + cell_w // 2, cy + cell_h // 2))
                )

        # Right panel: move detail for selected
        right_x = ox + grid_w - 4
        right_y = oy
        right_w = W - right_x - 8
        right_h = MENU_BOX_RECT.height - 16

        panel_rect = pygame.Rect(right_x, right_y, right_w, right_h)
        _draw_rounded_rect(screen, (28, 32, 45), panel_rect, radius=5)
        _draw_rounded_rect(
            screen, COL_GRAY, panel_rect, radius=5, border=1, border_color=COL_GRAY
        )

        if self._move_idx < len(moves):
            sel_move = moves[self._move_idx]
            tc = TYPE_COLORS.get(sel_move.type, (168, 168, 168))

            detail_font = self._font(15)
            dy = right_y + 8
            type_lbl = detail_font.render("TYPE", True, (160, 160, 180))
            screen.blit(type_lbl, (right_x + 8, dy))
            dy += 18
            tc_surf = detail_font.render(sel_move.type.upper(), True, tc)
            screen.blit(tc_surf, (right_x + 8, dy))
            dy += 24
            pp_lbl = detail_font.render("PP", True, (160, 160, 180))
            screen.blit(pp_lbl, (right_x + 8, dy))
            dy += 18
            pp_v = detail_font.render(
                f"{sel_move.pp_current}/{sel_move.pp}", True, COL_WHITE
            )
            screen.blit(pp_v, (right_x + 8, dy))

        # Cancel hint
        hint = self._font(14).render("[X] Back", True, (140, 140, 160))
        screen.blit(hint, (ox + 2, MENU_BOX_RECT.bottom - 18))

    def _draw_party_menu(self, screen: pygame.Surface):
        font_n = self._font(18)
        font_hp = self._font(14)

        ox = MENU_BOX_RECT.x + 16
        oy = MENU_BOX_RECT.y + 10
        row_h = (MENU_BOX_RECT.height - 24) // max(1, len(self.player_party))
        row_h = min(row_h, 50)

        title = self._font(16).render("Choose Pokemon  [X] Back", True, (180, 190, 210))
        screen.blit(title, (ox, oy))
        oy += 22

        for i, p in enumerate(self.player_party):
            selected = i == self._party_idx
            by = oy + i * (row_h + 4)

            bg = (55, 75, 115) if selected else (28, 32, 48)
            row_rect = pygame.Rect(ox, by, W - 32, row_h)
            _draw_rounded_rect(screen, bg, row_rect, radius=4)
            border_col = COL_SELECT if selected else (60, 65, 80)
            _draw_rounded_rect(
                screen,
                border_col,
                row_rect,
                radius=4,
                border=2,
                border_color=border_col,
            )

            # Color dot showing pokemon type color
            pygame.draw.circle(screen, p.color, (ox + 18, by + row_h // 2), 10)
            pygame.draw.circle(screen, COL_BLACK, (ox + 18, by + row_h // 2), 10, 2)

            # Name + level
            label = f"{p.name}  Lv.{p.level}"
            col = (180, 180, 180) if p.is_fainted else COL_WHITE
            nsurf = font_n.render(label, True, col)
            screen.blit(nsurf, (ox + 36, by + 6))

            # HP bar
            bar_w = 150
            bar_x = W - 205
            bar_y = by + 8
            pct = p.hp_pct
            pygame.draw.rect(screen, COL_HP_BG, pygame.Rect(bar_x, bar_y, bar_w, 10))
            if pct > 0:
                pygame.draw.rect(
                    screen,
                    _hp_color(pct),
                    pygame.Rect(bar_x, bar_y, int(bar_w * pct), 10),
                )
            pygame.draw.rect(
                screen,
                (60, 65, 80),
                pygame.Rect(bar_x - 1, bar_y - 1, bar_w + 2, 12),
                1,
            )

            hp_txt = font_hp.render(
                f"{max(0, p.hp)}/{p.max_hp}" if not p.is_fainted else "Fainted",
                True,
                (200, 200, 200) if not p.is_fainted else (200, 80, 80),
            )
            screen.blit(hp_txt, (bar_x, by + row_h - 18))

    # ── Hit flash overlay ─────────────────────────────────────────────────────

    def _draw_hit_flash(self, screen: pygame.Surface):
        if self._flash_timer > 0:
            alpha = int(min(200, self._flash_timer * 0.7))
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            fc = self._flash_color
            flash.fill((fc[0], fc[1], fc[2], alpha // 5))
            screen.blit(flash, (0, 0))

    # ── Font helper ───────────────────────────────────────────────────────────

    def _font(self, size: int) -> pygame.font.Font:
        return pygame.font.SysFont(None, size)
