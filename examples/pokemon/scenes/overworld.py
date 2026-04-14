"""Overworld scene — grid-based movement, map transitions, wild encounters."""

from __future__ import annotations

import random
from pathlib import Path

import pygame

from drift2d import Scene, Tilemap, TileDef
from core.pokemon import make_wild, Pokemon

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TILE = 32  # pixels per tile
MOVE_DURATION = 0.15  # seconds to slide one tile
ENCOUNTER_CHANCE = 0.15  # 15% per step in tall grass

# Map order used for > / < transitions
MAP_ORDER = ["town", "route1", "route2"]

# Wild encounter tables per map: {species: (min_level, max_level)}
ENCOUNTERS: dict[str, list[tuple[str, tuple[int, int]]]] = {
    "town": [],
    "route1": [
        ("rattata", (3, 5)),
        ("pidgey", (3, 5)),
        ("caterpie", (2, 4)),
    ],
    "route2": [
        ("nidoran", (6, 8)),
        ("geodude", (5, 7)),
        ("zubat", (5, 7)),
        ("pikachu", (4, 6)),
    ],
}

# Tile visual colours
COLOR_WALL = (80, 80, 80)
COLOR_FLOOR = (210, 200, 170)
COLOR_GRASS = (60, 160, 60)
COLOR_GRASS_D = (40, 120, 40)  # darker spots on grass
COLOR_HOUSE = (139, 90, 43)
COLOR_CENTER = (220, 50, 50)
COLOR_CROSS = (255, 255, 255)
COLOR_EXIT = (200, 200, 80)
COLOR_TRAINER = (100, 100, 200)

# Player colours
COLOR_PLAYER = (50, 100, 220)
COLOR_PLAYER_EYE = (255, 255, 255)
COLOR_PLAYER_IRIS = (0, 0, 0)

# UI colours
COLOR_UI_BG = (0, 0, 0, 160)
COLOR_HP_GOOD = (80, 200, 80)
COLOR_HP_LOW = (200, 80, 80)

# ---------------------------------------------------------------------------
# Tile definitions
# ---------------------------------------------------------------------------

TILE_DEFS: dict[str, TileDef] = {
    "W": TileDef("W", COLOR_WALL, solid=True, tag="wall"),
    ".": TileDef(".", COLOR_FLOOR, solid=False, tag="floor"),
    "G": TileDef("G", COLOR_GRASS, solid=False, tag="grass"),
    "H": TileDef("H", COLOR_HOUSE, solid=True, tag="house"),
    "C": TileDef("C", COLOR_CENTER, solid=False, tag="center"),
    "P": TileDef("P", COLOR_FLOOR, solid=False, tag="spawn"),
    "T": TileDef("T", COLOR_FLOOR, solid=False, tag="trainer"),
    ">": TileDef(">", COLOR_EXIT, solid=False, tag="exit_right"),
    "<": TileDef("<", COLOR_EXIT, solid=False, tag="exit_left"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _levels_dir() -> Path:
    """Absolute path to the levels directory next to this file."""
    return Path(__file__).parent.parent / "levels"


def _build_tilemap(map_name: str) -> Tilemap:
    tm = Tilemap(tile_size=TILE)
    for char, tdef in TILE_DEFS.items():
        tm.define(char, tdef)
    tm.load_from_file(_levels_dir() / f"{map_name}.txt")
    return tm


def _find_spawn(tm: Tilemap, char: str) -> tuple[int, int] | None:
    """Return first occurrence of char, or None."""
    hits = tm.find_tiles(char)
    return hits[0] if hits else None


# ---------------------------------------------------------------------------
# Notification banner
# ---------------------------------------------------------------------------


class _Banner:
    """Temporary text message displayed at the bottom of the screen."""

    def __init__(self):
        self.text = ""
        self.timer = 0.0

    def show(self, text: str, duration: float = 2.5):
        self.text = text
        self.timer = duration

    def update(self, dt: float):
        if self.timer > 0:
            self.timer -= dt

    @property
    def visible(self) -> bool:
        return self.timer > 0

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        if not self.visible:
            return
        sw, sh = screen.get_size()
        box_h = 44
        box = pygame.Surface((sw, box_h), pygame.SRCALPHA)
        box.fill((0, 0, 0, 180))
        screen.blit(box, (0, sh - box_h))
        surf = font.render(self.text, True, (255, 255, 255))
        screen.blit(surf, (12, sh - box_h + 10))


# ---------------------------------------------------------------------------
# OverworldScene
# ---------------------------------------------------------------------------


class OverworldScene(Scene):
    """
    Top-down overworld with grid-based movement, wild encounters,
    map transitions and NPC interaction.

    Attributes passed in from run.py (set before entering the scene):
        self.party      — list[Pokemon]  (at least one pokemon)
        self.pokeballs  — int

    The battle scene (registered as "battle") is expected to expose:
        scene.wild      — Pokemon | None   (set before push)
        scene.trainer   — bool
        scene.party     — shared reference to the same party list
    """

    # Engine flag: we handle all drawing ourselves
    custom_draw = True

    def __init__(self):
        super().__init__()
        # State — callers should set party before entering
        self.party: list[Pokemon] = []
        self.pokeballs: int = 10
        self.current_map: str = "town"

        # Map cache
        self.maps: dict[str, Tilemap] = {}

        # Player grid position (col, row) and pixel position for animation
        self._player_col: int = 0
        self._player_row: int = 0
        self._player_px: float = 0.0  # current rendered pixel x
        self._player_py: float = 0.0  # current rendered pixel y
        self._target_px: float = 0.0
        self._target_py: float = 0.0
        self._move_timer: float = 0.0
        self._moving: bool = False
        self._slide_start_px: float = 0.0
        self._slide_start_py: float = 0.0

        # UI
        self._banner = _Banner()
        self._font_small: pygame.font.Font | None = None
        self._font_med: pygame.font.Font | None = None

        # Suppress repeated encounters while message is shown
        self._in_dialog: bool = False

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------

    def enter(self):
        self._font_small = pygame.font.SysFont(None, 20)
        self._font_med = pygame.font.SysFont(None, 26)

        # Pre-load all maps
        for name in MAP_ORDER:
            if name not in self.maps:
                self.maps[name] = _build_tilemap(name)

        # Place player
        self._spawn_on_map(self.current_map, from_direction=None)

    def exit(self):
        pass

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        self._banner.update(dt)

        if self._moving:
            self._update_slide(dt)
        else:
            self._handle_input()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def _handle_input(self):
        if self._in_dialog:
            # Any key clears dialog state (banner still visible but movement re-enabled)
            inp = self.game.input
            if (
                inp.is_action_just_pressed("action")
                or inp.is_action_just_pressed("cancel")
                or inp.is_action_just_pressed("move_up")
                or inp.is_action_just_pressed("move_down")
                or inp.is_action_just_pressed("move_left")
                or inp.is_action_just_pressed("move_right")
            ):
                self._in_dialog = False
            return

        inp = self.game.input
        dx, dy = 0, 0
        if inp.is_action_just_pressed("move_up"):
            dy = -1
        elif inp.is_action_just_pressed("move_down"):
            dy = 1
        elif inp.is_action_just_pressed("move_left"):
            dx = -1
        elif inp.is_action_just_pressed("move_right"):
            dx = 1

        if dx != 0 or dy != 0:
            self._try_move(dx, dy)

    def _update_slide(self, dt: float):
        self._move_timer += dt
        t = min(self._move_timer / MOVE_DURATION, 1.0)
        self._player_px = (
            self._slide_start_px + (self._target_px - self._slide_start_px) * t
        )
        self._player_py = (
            self._slide_start_py + (self._target_py - self._slide_start_py) * t
        )

        if t >= 1.0:
            self._player_px = self._target_px
            self._player_py = self._target_py
            self._moving = False
            self._on_arrive()

    def _on_arrive(self):
        """Called when the player finishes sliding to the new tile."""
        tm = self.maps[self.current_map]
        tile = tm.get_tile(self._player_col, self._player_row)
        if tile is None:
            return

        tag = TILE_DEFS[tile].tag if tile in TILE_DEFS else ""

        if tag == "grass":
            self._check_encounter()
        elif tag == "center":
            self._heal_party()
        elif tag == "trainer":
            self._start_trainer_battle()

    # ------------------------------------------------------------------
    # Encounters
    # ------------------------------------------------------------------

    def _check_encounter(self):
        table = ENCOUNTERS.get(self.current_map, [])
        if not table:
            return
        if random.random() < ENCOUNTER_CHANCE:
            species, lvl_range = random.choice(table)
            wild = make_wild(species, lvl_range)
            self._start_wild_battle(wild)

    def _start_wild_battle(self, wild: Pokemon):
        scenes = self.game.scenes
        if "battle" not in scenes._scenes:
            self._banner.show(f"A wild {wild.name} appeared! (no battle scene)")
            self._in_dialog = True
            return

        battle = scenes._scenes["battle"]
        battle.party = self.party
        battle.wild = wild
        battle.trainer = False
        scenes.push("battle")

    def _start_trainer_battle(self):
        scenes = self.game.scenes
        if "battle" not in scenes._scenes:
            self._banner.show("A trainer wants to battle! (no battle scene)")
            self._in_dialog = True
            return

        battle = scenes._scenes["battle"]
        battle.party = self.party
        battle.wild = None
        battle.trainer = True
        scenes.push("battle")

    # ------------------------------------------------------------------
    # Pokemon center
    # ------------------------------------------------------------------

    def _heal_party(self):
        for p in self.party:
            p.heal()
        self._banner.show("Your Pokemon have been healed!")
        self._in_dialog = True

    # ------------------------------------------------------------------
    # Map transitions
    # ------------------------------------------------------------------

    def _transition_right(self):
        idx = MAP_ORDER.index(self.current_map)
        if idx + 1 >= len(MAP_ORDER):
            self._banner.show("No more routes this way!")
            self._in_dialog = True
            return
        next_map = MAP_ORDER[idx + 1]
        self.current_map = next_map
        self._spawn_on_map(next_map, from_direction="left")

    def _transition_left(self):
        idx = MAP_ORDER.index(self.current_map)
        if idx - 1 < 0:
            self._banner.show("Can't go back here!")
            self._in_dialog = True
            return
        prev_map = MAP_ORDER[idx - 1]
        self.current_map = prev_map
        self._spawn_on_map(prev_map, from_direction="right")

    def _spawn_on_map(self, map_name: str, from_direction: str | None):
        """Place the player on the map, at spawn point or transition edge."""
        tm = self.maps[map_name]

        if from_direction == "left":
            # Came from left — find < exit tile row, spawn one tile right of it
            exits = tm.find_tiles("<")
            if exits:
                col, row = exits[0]
                spawn_col, spawn_row = col + 1, row
            else:
                spawn_col, spawn_row = 1, tm.height // 2
        elif from_direction == "right":
            # Came from right — find > exit tile row, spawn one tile left of it
            exits = tm.find_tiles(">")
            if exits:
                col, row = exits[0]
                spawn_col, spawn_row = col - 1, row
            else:
                spawn_col, spawn_row = tm.width - 2, tm.height // 2
        else:
            # Find P spawn marker, fall back to (1,1)
            spawn = _find_spawn(tm, "P")
            if spawn:
                spawn_col, spawn_row = spawn
            else:
                spawn_col, spawn_row = 1, 1

        self._player_col = spawn_col
        self._player_row = spawn_row
        self._player_px = float(spawn_col * TILE)
        self._player_py = float(spawn_row * TILE)
        self._target_px = self._player_px
        self._target_py = self._player_py
        # Store slide start as same position (not sliding yet)
        self._slide_start_px = self._player_px
        self._slide_start_py = self._player_py
        self._moving = False

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self):
        screen = self.game.screen
        tm = self.maps[self.current_map]
        sw, sh = screen.get_size()

        # Camera offset: center on player pixel position
        cam_x = self._player_px + TILE / 2 - sw / 2
        cam_y = self._player_py + TILE / 2 - sh / 2
        # Clamp to map bounds
        map_pw = tm.width * TILE
        map_ph = tm.height * TILE
        cam_x = max(0.0, min(cam_x, map_pw - sw))
        cam_y = max(0.0, min(cam_y, map_ph - sh))

        # Draw map tiles
        self._draw_tilemap(screen, tm, cam_x, cam_y)

        # Draw player
        self._draw_player(screen, cam_x, cam_y)

        # HUD overlay
        self._draw_hud(screen)

        # Banner notification
        self._banner.draw(screen, self._font_med)

    def _draw_tilemap(
        self, screen: pygame.Surface, tm: Tilemap, cam_x: float, cam_y: float
    ):
        sw, sh = screen.get_size()
        # Determine visible tile range
        min_col = max(0, int(cam_x // TILE))
        max_col = min(tm.width, int((cam_x + sw) // TILE) + 2)
        min_row = max(0, int(cam_y // TILE))
        max_row = min(tm.height, int((cam_y + sh) // TILE) + 2)

        for row in range(min_row, max_row):
            for col in range(min_col, max_col):
                tile = tm.get_tile(col, row)
                if tile is None:
                    continue
                sx = int(col * TILE - cam_x)
                sy = int(row * TILE - cam_y)
                rect = pygame.Rect(sx, sy, TILE, TILE)
                self._draw_tile(screen, tile, rect)

    def _draw_tile(self, screen: pygame.Surface, tile: str, rect: pygame.Rect):
        if tile == "W":
            pygame.draw.rect(screen, COLOR_WALL, rect)
            # Subtle inner shadow
            pygame.draw.rect(screen, (60, 60, 60), rect, 2)

        elif tile in (".", "P", "T", ">", "<"):
            pygame.draw.rect(screen, COLOR_FLOOR, rect)
            if tile == ">":
                pygame.draw.polygon(
                    screen,
                    COLOR_EXIT,
                    [
                        (rect.left + 8, rect.top + 8),
                        (rect.right - 6, rect.centery),
                        (rect.left + 8, rect.bottom - 8),
                    ],
                )
            elif tile == "<":
                pygame.draw.polygon(
                    screen,
                    COLOR_EXIT,
                    [
                        (rect.right - 8, rect.top + 8),
                        (rect.left + 6, rect.centery),
                        (rect.right - 8, rect.bottom - 8),
                    ],
                )
            elif tile == "T":
                # Trainer marker: small colored figure
                pygame.draw.rect(
                    screen,
                    COLOR_TRAINER,
                    pygame.Rect(rect.left + 8, rect.top + 6, 16, 20),
                )
                pygame.draw.circle(
                    screen, (240, 200, 160), (rect.centerx, rect.top + 8), 7
                )

        elif tile == "G":
            pygame.draw.rect(screen, COLOR_GRASS, rect)
            # Darker grass blades pattern
            for ox, oy in [(4, 4), (14, 10), (22, 5), (8, 18), (20, 20), (2, 26)]:
                if ox < TILE and oy < TILE:
                    pygame.draw.rect(
                        screen,
                        COLOR_GRASS_D,
                        pygame.Rect(rect.left + ox, rect.top + oy, 4, 8),
                    )

        elif tile == "H":
            pygame.draw.rect(screen, COLOR_HOUSE, rect)
            # Roof hint
            pygame.draw.polygon(
                screen,
                (100, 60, 20),
                [
                    (rect.left, rect.top + 12),
                    (rect.centerx, rect.top + 2),
                    (rect.right, rect.top + 12),
                ],
            )
            # Door
            pygame.draw.rect(
                screen,
                (60, 30, 10),
                pygame.Rect(rect.centerx - 4, rect.bottom - 12, 8, 12),
            )

        elif tile == "C":
            pygame.draw.rect(screen, COLOR_CENTER, rect)
            # White cross
            cross_w = TILE // 5
            cx, cy = rect.centerx, rect.centery
            pygame.draw.rect(
                screen,
                COLOR_CROSS,
                pygame.Rect(cx - cross_w // 2, cy - TILE // 3, cross_w, TILE * 2 // 3),
            )
            pygame.draw.rect(
                screen,
                COLOR_CROSS,
                pygame.Rect(cx - TILE // 3, cy - cross_w // 2, TILE * 2 // 3, cross_w),
            )

        else:
            # Unknown tile — floor colour
            pygame.draw.rect(screen, COLOR_FLOOR, rect)

    def _draw_player(self, screen: pygame.Surface, cam_x: float, cam_y: float):
        sx = int(self._player_px - cam_x)
        sy = int(self._player_py - cam_y)
        body = pygame.Rect(sx + 4, sy + 4, TILE - 8, TILE - 8)
        pygame.draw.rect(screen, COLOR_PLAYER, body, border_radius=4)
        # Eyes
        eye_y = sy + 10
        for ex in (sx + 9, sx + 18):
            pygame.draw.circle(screen, COLOR_PLAYER_EYE, (ex, eye_y), 4)
            pygame.draw.circle(screen, COLOR_PLAYER_IRIS, (ex, eye_y), 2)

    def _draw_hud(self, screen: pygame.Surface):
        sw, _ = screen.get_size()

        # Map name — top-left
        map_label = self.current_map.replace("route", "Route ").title()
        if self._font_med:
            lbl = self._font_med.render(map_label, True, (255, 255, 255))
            # Dark backing
            backing = pygame.Surface(
                (lbl.get_width() + 10, lbl.get_height() + 6), pygame.SRCALPHA
            )
            backing.fill((0, 0, 0, 160))
            screen.blit(backing, (4, 4))
            screen.blit(lbl, (9, 7))

        # Lead pokemon — top-right
        if self.party and self._font_small and self._font_med:
            lead = self.party[0]
            info_w = 160
            info_x = sw - info_w - 4
            info_y = 4

            # Background panel
            panel = pygame.Surface((info_w, 44), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 160))
            screen.blit(panel, (info_x, info_y))

            # Name + level
            name_text = f"{lead.name}  Lv.{lead.level}"
            nlbl = self._font_med.render(name_text, True, (255, 255, 255))
            screen.blit(nlbl, (info_x + 6, info_y + 4))

            # HP bar
            bar_x = info_x + 6
            bar_y = info_y + 28
            bar_w = info_w - 12
            bar_h = 8
            pygame.draw.rect(
                screen, (60, 60, 60), pygame.Rect(bar_x, bar_y, bar_w, bar_h)
            )
            hp_ratio = max(0.0, lead.hp_pct)
            filled = int(bar_w * hp_ratio)
            hp_color = COLOR_HP_GOOD if hp_ratio > 0.25 else COLOR_HP_LOW
            if filled > 0:
                pygame.draw.rect(
                    screen, hp_color, pygame.Rect(bar_x, bar_y, filled, bar_h)
                )
            # HP text
            hp_txt = self._font_small.render(
                f"{lead.hp}/{lead.max_hp}", True, (220, 220, 220)
            )
            screen.blit(hp_txt, (bar_x + bar_w + 4, bar_y - 2))

    def _try_move(self, dx: int, dy: int):
        tm = self.maps[self.current_map]
        new_col = self._player_col + dx
        new_row = self._player_row + dy

        tile = tm.get_tile(new_col, new_row)
        if tile is None:
            return

        if tile in TILE_DEFS and TILE_DEFS[tile].solid:
            return

        if tile == ">":
            self._transition_right()
            return
        if tile == "<":
            self._transition_left()
            return

        # Commit move
        self._player_col = new_col
        self._player_row = new_row
        self._slide_start_px = self._player_px
        self._slide_start_py = self._player_py
        self._target_px = float(new_col * TILE)
        self._target_py = float(new_row * TILE)
        self._move_timer = 0.0
        self._moving = True
