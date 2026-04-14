"""Overworld scene — grid-based movement, map transitions, wild encounters."""

from __future__ import annotations

import math
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
COLOR_WALL = (60, 60, 70)
COLOR_WALL_HIGHLIGHT = (100, 100, 110)
COLOR_FLOOR = (205, 188, 152)
COLOR_FLOOR_GRID = (185, 170, 136)
COLOR_GRASS = (34, 139, 34)
COLOR_GRASS_DARK = (22, 100, 22)
COLOR_GRASS_BLADE = (50, 180, 50)
COLOR_HOUSE = (139, 90, 43)
COLOR_HOUSE_ROOF = (90, 50, 20)
COLOR_HOUSE_WINDOW = (255, 230, 100)
COLOR_HOUSE_DOOR = (70, 35, 10)
COLOR_CENTER_BASE = (240, 240, 255)
COLOR_CENTER_ROOF = (210, 40, 40)
COLOR_CENTER_CROSS = (255, 255, 255)
COLOR_EXIT = (255, 230, 0)
COLOR_TRAINER = (100, 100, 200)

# Player colours
COLOR_JACKET_DOWN = (60, 100, 200)
COLOR_JACKET_UP = (50, 80, 180)
COLOR_JACKET_LEFT = (40, 90, 190)
COLOR_JACKET_RIGHT = (70, 110, 210)
COLOR_SKIN = (240, 195, 145)
COLOR_HAIR = (50, 30, 10)
COLOR_PLAYER_EYE = (30, 30, 80)
COLOR_PANTS = (40, 40, 120)
COLOR_SHOES = (30, 20, 10)

# UI colours
COLOR_UI_BG = (0, 0, 0, 160)
COLOR_HP_GOOD = (80, 200, 80)
COLOR_HP_MID = (230, 200, 40)
COLOR_HP_LOW = (220, 60, 60)
COLOR_HP_BORDER = (20, 20, 20)

# Prof NPC
PROF_NPC_COL = 14
PROF_NPC_ROW = 3
PROF_NPC_MAP = "town"
PROF_DIALOG = "Welcome to the world of Pokemon!\nGo explore Route 1!"

# Flash/fade effect types
_FLASH_WHITE = "white"
_FLASH_PINK = "pink"
_FADE_BLACK = "black"

# ---------------------------------------------------------------------------
# Tile definitions
# ---------------------------------------------------------------------------

TILE_DEFS: dict[str, TileDef] = {
    "W": TileDef("W", COLOR_WALL, solid=True, tag="wall"),
    ".": TileDef(".", COLOR_FLOOR, solid=False, tag="floor"),
    "G": TileDef("G", COLOR_GRASS, solid=False, tag="grass"),
    "H": TileDef("H", COLOR_HOUSE, solid=True, tag="house"),
    "C": TileDef("C", COLOR_CENTER_BASE, solid=False, tag="center"),
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


def _pokemon_dot_color(name: str) -> tuple[int, int, int]:
    """Return a simple color to represent a pokemon species."""
    colors = {
        "charmander": (255, 100, 30),
        "squirtle": (60, 120, 220),
        "bulbasaur": (80, 180, 80),
        "pikachu": (255, 220, 0),
        "rattata": (160, 100, 140),
        "pidgey": (180, 150, 100),
        "caterpie": (60, 160, 60),
        "nidoran": (160, 80, 180),
        "geodude": (140, 120, 100),
        "zubat": (100, 80, 160),
    }
    return colors.get(name.lower(), (150, 150, 200))


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
        box_h = 50
        box = pygame.Surface((sw, box_h), pygame.SRCALPHA)
        # Gradient-ish: darker at top of box
        for i in range(box_h):
            alpha = int(160 + (i / box_h) * 40)
            pygame.draw.line(box, (0, 0, 0, alpha), (0, i), (sw, i))
        screen.blit(box, (0, sh - box_h))
        # White border line at top of banner
        pygame.draw.line(screen, (255, 255, 255, 80), (0, sh - box_h), (sw, sh - box_h))
        # Split multi-line text (for Prof dialog)
        lines = self.text.split("\n")
        for i, line in enumerate(lines):
            surf = font.render(line, True, (255, 255, 255))
            screen.blit(surf, (14, sh - box_h + 8 + i * 18))


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

        # Player visual state
        self._facing: str = "down"  # "up" | "down" | "left" | "right"
        self._bob_phase: float = 0.0  # oscillates while moving
        self._step_count: int = 0

        # Held-key movement: initial delay then repeat (like real Pokemon)
        self._held_dir: tuple[int, int] = (0, 0)
        self._held_timer: float = 0.0
        self._held_initial_delay: float = 0.12  # seconds before first repeat
        self._held_repeat_rate: float = 0.08  # seconds between repeats after initial

        # Global time accumulator (drives animations)
        self._time: float = 0.0

        # Grass rustle: set of (col, row) with rustle_timer
        self._rustle_tiles: dict[tuple[int, int], float] = {}

        # Screen flash / fade overlay
        self._overlay_color: tuple[int, int, int] = (0, 0, 0)
        self._overlay_alpha: float = 0.0  # 0..255
        self._overlay_dir: int = 0  # -1 fade out, +1 fade in, 0 idle
        self._overlay_speed: float = 400.0  # alpha units per second

        # Battle flash: brief white/pink before fade
        self._flash_timer: float = 0.0
        self._flash_color: tuple[int, int, int] = (255, 255, 255)
        self._pending_battle_wild: Pokemon | None = None
        self._pending_map_transition: str | None = None  # "left" | "right"

        # UI
        self._banner = _Banner()
        self._font_small: pygame.font.Font | None = None
        self._font_med: pygame.font.Font | None = None
        self._font_tiny: pygame.font.Font | None = None

        # Suppress repeated encounters while message is shown
        self._in_dialog: bool = False

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------

    def enter(self):
        self._font_small = pygame.font.SysFont(None, 20)
        self._font_med = pygame.font.SysFont(None, 26)
        self._font_tiny = pygame.font.SysFont(None, 16)

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
        self._time += dt
        self._banner.update(dt)

        # Advance rustle timers
        expired = [k for k, v in self._rustle_tiles.items() if v <= 0]
        for k in expired:
            del self._rustle_tiles[k]
        for k in list(self._rustle_tiles):
            self._rustle_tiles[k] -= dt

        # Flash timer (white/pink flash before battle)
        if self._flash_timer > 0:
            self._flash_timer -= dt
            if self._flash_timer <= 0:
                self._flash_timer = 0.0
                # Now start fade to black
                if (
                    self._pending_battle_wild is not None
                    or self._pending_map_transition is not None
                ):
                    self._overlay_color = (0, 0, 0)
                    self._overlay_alpha = 0.0
                    self._overlay_dir = 1  # fade in (darken)
            return  # hold input during flash

        # Overlay fade
        if self._overlay_dir != 0:
            self._overlay_alpha += self._overlay_dir * self._overlay_speed * dt
            if self._overlay_dir == 1 and self._overlay_alpha >= 255:
                self._overlay_alpha = 255.0
                self._overlay_dir = 0
                # Execute the deferred action
                self._execute_deferred_transition()
            elif self._overlay_dir == -1 and self._overlay_alpha <= 0:
                self._overlay_alpha = 0.0
                self._overlay_dir = 0
            return  # hold input during fade

        # Bob animation while moving
        if self._moving:
            self._bob_phase += dt * 20.0
            self._update_slide(dt)
        else:
            self._bob_phase = 0.0
            self._handle_input()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def _handle_input(self):
        if self._in_dialog:
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

        # Check action key for NPC interaction
        if inp.is_action_just_pressed("action"):
            self._try_interact()
            return

        # Check for just_pressed first (single tap = one tile, works for bot too)
        dx, dy = 0, 0
        just = False
        if inp.is_action_just_pressed("move_up"):
            dy, just = -1, True
        elif inp.is_action_just_pressed("move_down"):
            dy, just = 1, True
        elif inp.is_action_just_pressed("move_left"):
            dx, just = -1, True
        elif inp.is_action_just_pressed("move_right"):
            dx, just = 1, True

        # Also check held keys for continuous movement
        if not just:
            if inp.is_action_pressed("move_up"):
                dy = -1
            elif inp.is_action_pressed("move_down"):
                dy = 1
            elif inp.is_action_pressed("move_left"):
                dx = -1
            elif inp.is_action_pressed("move_right"):
                dx = 1

        if dx == 0 and dy == 0:
            self._held_dir = (0, 0)
            self._held_timer = 0.0
            return

        new_dir = (dx, dy)

        # Update facing direction
        if dy == -1:
            self._facing = "up"
        elif dy == 1:
            self._facing = "down"
        elif dx == -1:
            self._facing = "left"
        elif dx == 1:
            self._facing = "right"

        if just:
            # Single tap — move immediately, no repeat logic
            self._held_dir = new_dir
            self._held_timer = 0.0
            self._try_move(dx, dy)
        elif new_dir != self._held_dir:
            # Changed held direction — move immediately
            self._held_dir = new_dir
            self._held_timer = 0.0
            self._try_move(dx, dy)
        else:
            # Same direction held — repeat after delay
            self._held_timer += self.game.dt
            if self._held_timer >= self._held_initial_delay:
                self._try_move(dx, dy)
                self._held_timer -= self._held_repeat_rate

    def _try_interact(self):
        """Check if facing an NPC and trigger dialog."""
        if self.current_map != PROF_NPC_MAP:
            return
        # Face-direction offset
        offsets = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        dxo, dyo = offsets.get(self._facing, (0, 1))
        target_col = self._player_col + dxo
        target_row = self._player_row + dyo
        if target_col == PROF_NPC_COL and target_row == PROF_NPC_ROW:
            self._banner.show(PROF_DIALOG, duration=4.0)
            self._in_dialog = True

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
        self._step_count += 1
        tm = self.maps[self.current_map]
        tile = tm.get_tile(self._player_col, self._player_row)
        if tile is None:
            return

        tag = TILE_DEFS[tile].tag if tile in TILE_DEFS else ""

        if tag == "grass":
            # Register rustle visual effect
            self._rustle_tiles[(self._player_col, self._player_row)] = 0.4
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
            self._trigger_battle_flash(wild)

    def _trigger_battle_flash(self, wild: Pokemon):
        """White flash then fade to black before launching battle."""
        self._pending_battle_wild = wild
        self._flash_color = (255, 255, 255)
        self._flash_timer = 0.12

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

    def _execute_deferred_transition(self):
        """Run the pending action after fade-to-black completes."""
        if self._pending_battle_wild is not None:
            wild = self._pending_battle_wild
            self._pending_battle_wild = None
            self._start_wild_battle(wild)
            # Fade back in
            self._overlay_dir = -1
        elif self._pending_map_transition is not None:
            direction = self._pending_map_transition
            self._pending_map_transition = None
            if direction == "right":
                self._do_transition_right()
            else:
                self._do_transition_left()
            # Fade back in
            self._overlay_dir = -1

    # ------------------------------------------------------------------
    # Pokemon center
    # ------------------------------------------------------------------

    def _heal_party(self):
        for p in self.party:
            p.heal()
        # Brief pink flash + banner
        self._flash_color = (255, 180, 210)
        self._flash_timer = 0.25
        self._banner.show("Your Pokemon have been healed!", duration=3.0)
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
        # Trigger fade-out, then do transition
        self._pending_map_transition = "right"
        self._overlay_color = (0, 0, 0)
        self._overlay_alpha = 0.0
        self._overlay_dir = 1

    def _do_transition_right(self):
        idx = MAP_ORDER.index(self.current_map)
        next_map = MAP_ORDER[idx + 1]
        self.current_map = next_map
        self._spawn_on_map(next_map, from_direction="left")

    def _transition_left(self):
        idx = MAP_ORDER.index(self.current_map)
        if idx - 1 < 0:
            self._banner.show("Can't go back here!")
            self._in_dialog = True
            return
        self._pending_map_transition = "left"
        self._overlay_color = (0, 0, 0)
        self._overlay_alpha = 0.0
        self._overlay_dir = 1

    def _do_transition_left(self):
        idx = MAP_ORDER.index(self.current_map)
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
        self._rustle_tiles.clear()

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

        # Draw Prof NPC if on the right map
        if self.current_map == PROF_NPC_MAP:
            self._draw_prof_npc(screen, cam_x, cam_y)

        # Draw player
        self._draw_player(screen, cam_x, cam_y)

        # HUD overlay
        self._draw_hud(screen)

        # Banner notification
        self._banner.draw(screen, self._font_med)

        # Flash overlay (white/pink)
        if self._flash_timer > 0:
            flash_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            alpha = int(200 * (self._flash_timer / 0.25))
            alpha = max(0, min(255, alpha))
            flash_surf.fill((*self._flash_color, alpha))
            screen.blit(flash_surf, (0, 0))

        # Fade overlay (black)
        if self._overlay_alpha > 0:
            fade_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            fade_surf.fill((0, 0, 0, int(self._overlay_alpha)))
            screen.blit(fade_surf, (0, 0))

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
                rustled = (col, row) in self._rustle_tiles
                self._draw_tile(screen, tile, rect, col, row, rustled)

    def _draw_tile(
        self,
        screen: pygame.Surface,
        tile: str,
        rect: pygame.Rect,
        col: int,
        row: int,
        rustled: bool = False,
    ):
        t = self._time

        if tile == "W":
            # Dark stone base with slight variation per tile
            shade = (col * 7 + row * 13) % 20
            base = (
                max(0, COLOR_WALL[0] - shade),
                max(0, COLOR_WALL[1] - shade),
                max(0, COLOR_WALL[2] - shade + 5),
            )
            pygame.draw.rect(screen, base, rect)
            # 3D top highlight edge
            pygame.draw.line(
                screen, COLOR_WALL_HIGHLIGHT, rect.topleft, rect.topright, 2
            )
            pygame.draw.line(
                screen, COLOR_WALL_HIGHLIGHT, rect.topleft, (rect.left, rect.top + 4), 1
            )
            # Dark bottom/right shadow
            pygame.draw.line(screen, (30, 30, 35), rect.bottomleft, rect.bottomright, 1)
            pygame.draw.line(screen, (30, 30, 35), rect.topright, rect.bottomright, 1)

        elif tile in (".", "P", "T"):
            # Tan/beige floor with subtle tile grid lines
            pygame.draw.rect(screen, COLOR_FLOOR, rect)
            pygame.draw.line(
                screen, COLOR_FLOOR_GRID, rect.topright, rect.bottomright, 1
            )
            pygame.draw.line(
                screen, COLOR_FLOOR_GRID, rect.bottomleft, rect.bottomright, 1
            )

            if tile == "T":
                # Trainer marker: small colored figure on floor
                pygame.draw.rect(
                    screen,
                    COLOR_TRAINER,
                    pygame.Rect(rect.left + 9, rect.top + 8, 14, 18),
                )
                pygame.draw.circle(screen, COLOR_SKIN, (rect.centerx, rect.top + 10), 6)

        elif tile in (">", "<"):
            # Floor base
            pygame.draw.rect(screen, COLOR_FLOOR, rect)
            pygame.draw.line(
                screen, COLOR_FLOOR_GRID, rect.topright, rect.bottomright, 1
            )
            pygame.draw.line(
                screen, COLOR_FLOOR_GRID, rect.bottomleft, rect.bottomright, 1
            )
            # Pulsing arrow brightness
            pulse = int(200 + 55 * math.sin(t * 4.0))
            arrow_col = (pulse, pulse, 0)
            if tile == ">":
                pygame.draw.polygon(
                    screen,
                    arrow_col,
                    [
                        (rect.left + 7, rect.top + 8),
                        (rect.right - 5, rect.centery),
                        (rect.left + 7, rect.bottom - 8),
                    ],
                )
                # Arrow border
                pygame.draw.polygon(
                    screen,
                    (120, 100, 0),
                    [
                        (rect.left + 7, rect.top + 8),
                        (rect.right - 5, rect.centery),
                        (rect.left + 7, rect.bottom - 8),
                    ],
                    1,
                )
            else:
                pygame.draw.polygon(
                    screen,
                    arrow_col,
                    [
                        (rect.right - 7, rect.top + 8),
                        (rect.left + 5, rect.centery),
                        (rect.right - 7, rect.bottom - 8),
                    ],
                )
                pygame.draw.polygon(
                    screen,
                    (120, 100, 0),
                    [
                        (rect.right - 7, rect.top + 8),
                        (rect.left + 5, rect.centery),
                        (rect.right - 7, rect.bottom - 8),
                    ],
                    1,
                )

        elif tile == "G":
            # Vibrant green base with darker bottom strip
            pygame.draw.rect(screen, COLOR_GRASS, rect)
            pygame.draw.rect(
                screen,
                COLOR_GRASS_DARK,
                pygame.Rect(rect.left, rect.bottom - 6, TILE, 6),
            )

            if rustled:
                # Darker rustle patch
                rustle_surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                rustle_surf.fill((0, 0, 0, 60))
                screen.blit(rustle_surf, rect.topleft)

            # Animated grass blades (sin wave based on time + position)
            blade_positions = [(5, 22), (12, 20), (19, 24), (26, 21), (9, 26), (22, 27)]
            for bx, by in blade_positions:
                # Phase offset per blade using position hash
                phase = (col * 3 + row * 7 + bx) * 0.5
                sway = math.sin(t * 2.5 + phase) * 2.0
                bx_s = int(rect.left + bx + sway)
                by_base = rect.top + by
                pygame.draw.line(
                    screen,
                    COLOR_GRASS_BLADE,
                    (bx_s, by_base + 6),
                    (bx_s + int(sway), by_base),
                    1,
                )

        elif tile == "H":
            # Brown house base
            pygame.draw.rect(screen, COLOR_HOUSE, rect)
            # Darker roof triangle
            pygame.draw.polygon(
                screen,
                COLOR_HOUSE_ROOF,
                [
                    (rect.left, rect.top + 14),
                    (rect.centerx, rect.top),
                    (rect.right, rect.top + 14),
                ],
            )
            # Yellow window
            pygame.draw.rect(
                screen,
                COLOR_HOUSE_WINDOW,
                pygame.Rect(rect.left + 5, rect.top + 16, 8, 7),
            )
            pygame.draw.rect(
                screen,
                (200, 170, 60),
                pygame.Rect(rect.left + 5, rect.top + 16, 8, 7),
                1,
            )
            # Door
            pygame.draw.rect(
                screen,
                COLOR_HOUSE_DOOR,
                pygame.Rect(rect.centerx - 4, rect.bottom - 11, 8, 11),
            )
            # Door knob
            pygame.draw.circle(
                screen, (200, 160, 60), (rect.centerx + 2, rect.bottom - 6), 1
            )

        elif tile == "C":
            # White/pink Pokemon Center
            pygame.draw.rect(screen, COLOR_CENTER_BASE, rect)
            # Red roof
            pygame.draw.polygon(
                screen,
                COLOR_CENTER_ROOF,
                [
                    (rect.left, rect.top + 13),
                    (rect.centerx, rect.top + 1),
                    (rect.right, rect.top + 13),
                ],
            )
            # White cross (medical)
            cross_w = 4
            cx, cy = rect.centerx, rect.top + 20
            pygame.draw.rect(
                screen,
                COLOR_CENTER_CROSS,
                pygame.Rect(cx - cross_w // 2, cy - 5, cross_w, 10),
            )
            pygame.draw.rect(
                screen,
                COLOR_CENTER_CROSS,
                pygame.Rect(cx - 5, cy - cross_w // 2, 10, cross_w),
            )
            # "PC" label tiny
            if self._font_tiny:
                pc_lbl = self._font_tiny.render("PC", True, (180, 40, 40))
                screen.blit(pc_lbl, (rect.left + 2, rect.bottom - 13))

        else:
            # Unknown tile — floor colour
            pygame.draw.rect(screen, COLOR_FLOOR, rect)

    def _draw_prof_npc(self, screen: pygame.Surface, cam_x: float, cam_y: float):
        """Draw the Professor NPC as a circle-P figure."""
        sx = int(PROF_NPC_COL * TILE - cam_x)
        sy = int(PROF_NPC_ROW * TILE - cam_y)
        # Only draw if on screen
        sw, sh = screen.get_size()
        if sx < -TILE or sy < -TILE or sx > sw or sy > sh:
            return

        cx = sx + TILE // 2
        # Body (white lab coat)
        pygame.draw.rect(screen, (240, 240, 240), pygame.Rect(sx + 9, sy + 14, 14, 16))
        # Head
        pygame.draw.circle(screen, COLOR_SKIN, (cx, sy + 10), 7)
        # Hair (grey)
        pygame.draw.arc(
            screen,
            (160, 160, 160),
            pygame.Rect(cx - 7, sy + 3, 14, 10),
            0,
            math.pi,
            3,
        )
        # Eyes
        pygame.draw.circle(screen, (30, 30, 30), (cx - 3, sy + 10), 1)
        pygame.draw.circle(screen, (30, 30, 30), (cx + 3, sy + 10), 1)
        # "P" label badge above head
        pygame.draw.circle(screen, (80, 120, 200), (cx, sy - 4), 6)
        if self._font_tiny:
            p_lbl = self._font_tiny.render("P", True, (255, 255, 255))
            screen.blit(p_lbl, (cx - p_lbl.get_width() // 2, sy - 10))

    def _draw_player(self, screen: pygame.Surface, cam_x: float, cam_y: float):
        sx = int(self._player_px - cam_x)
        sy = int(self._player_py - cam_y)

        # Bob offset while moving
        bob = int(math.sin(self._bob_phase) * 1.5) if self._moving else 0

        facing = self._facing
        jacket_colors = {
            "down": COLOR_JACKET_DOWN,
            "up": COLOR_JACKET_UP,
            "left": COLOR_JACKET_LEFT,
            "right": COLOR_JACKET_RIGHT,
        }
        jacket_col = jacket_colors.get(facing, COLOR_JACKET_DOWN)

        # Shoes
        pygame.draw.rect(screen, COLOR_SHOES, pygame.Rect(sx + 8, sy + 26 + bob, 6, 4))
        pygame.draw.rect(screen, COLOR_SHOES, pygame.Rect(sx + 18, sy + 26 + bob, 6, 4))

        # Pants
        pygame.draw.rect(screen, COLOR_PANTS, pygame.Rect(sx + 8, sy + 19 + bob, 16, 8))

        # Jacket body
        pygame.draw.rect(
            screen,
            jacket_col,
            pygame.Rect(sx + 7, sy + 12 + bob, 18, 10),
            border_radius=2,
        )

        # Arms (jacket color, slightly offset for left/right)
        if facing == "left":
            pygame.draw.rect(
                screen, jacket_col, pygame.Rect(sx + 4, sy + 13 + bob, 5, 8)
            )
        elif facing == "right":
            pygame.draw.rect(
                screen, jacket_col, pygame.Rect(sx + 23, sy + 13 + bob, 5, 8)
            )
        else:
            pygame.draw.rect(
                screen, jacket_col, pygame.Rect(sx + 4, sy + 13 + bob, 4, 7)
            )
            pygame.draw.rect(
                screen, jacket_col, pygame.Rect(sx + 24, sy + 13 + bob, 4, 7)
            )

        # Head (skin)
        head_cx = sx + TILE // 2
        head_cy = sy + 8 + bob
        pygame.draw.circle(screen, COLOR_SKIN, (head_cx, head_cy), 7)

        # Hair
        pygame.draw.arc(
            screen,
            COLOR_HAIR,
            pygame.Rect(head_cx - 7, head_cy - 7, 14, 10),
            0,
            math.pi,
            3,
        )

        # Eyes based on facing direction
        if facing == "down":
            for ex in (head_cx - 3, head_cx + 3):
                pygame.draw.circle(screen, COLOR_PLAYER_EYE, (ex, head_cy + 2), 1)
        elif facing == "up":
            # No visible eyes from back — just hair
            pass
        elif facing == "left":
            pygame.draw.circle(screen, COLOR_PLAYER_EYE, (head_cx - 4, head_cy + 1), 1)
        elif facing == "right":
            pygame.draw.circle(screen, COLOR_PLAYER_EYE, (head_cx + 4, head_cy + 1), 1)

    def _draw_hud(self, screen: pygame.Surface):
        sw, sh = screen.get_size()

        # Top gradient bar
        bar_h = 30
        bar_surf = pygame.Surface((sw, bar_h), pygame.SRCALPHA)
        for i in range(bar_h):
            alpha = int(180 - i * 4)
            alpha = max(0, alpha)
            pygame.draw.line(bar_surf, (0, 0, 0, alpha), (0, i), (sw, i))
        screen.blit(bar_surf, (0, 0))

        # Map name badge — top-left
        if self._font_med:
            map_label = self.current_map.replace("route", "Route ").title()
            lbl = self._font_med.render(map_label, True, (255, 255, 255))
            lbl_w = lbl.get_width()
            lbl_h = lbl.get_height()
            # Badge color: green for routes, brown for town
            if "route" in self.current_map.lower():
                badge_color = (30, 100, 50, 200)
            else:
                badge_color = (100, 60, 20, 200)
            badge = pygame.Surface((lbl_w + 14, lbl_h + 8), pygame.SRCALPHA)
            pygame.draw.rect(badge, badge_color, badge.get_rect(), border_radius=6)
            badge.blit(lbl, (7, 4))
            screen.blit(badge, (6, 4))

        # Step counter — bottom-left of top bar
        if self._font_tiny:
            step_lbl = self._font_tiny.render(
                f"Steps: {self._step_count}", True, (200, 200, 200)
            )
            screen.blit(step_lbl, (8, bar_h + 4))

        # Lead pokemon panel — top-right
        if self.party and self._font_small and self._font_med:
            lead = self.party[0]
            info_w = 170
            info_h = 56
            info_x = sw - info_w - 6
            info_y = 4

            # Panel background
            panel = pygame.Surface((info_w, info_h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (0, 0, 0, 170), panel.get_rect(), border_radius=8)
            screen.blit(panel, (info_x, info_y))

            # Mini colored pokemon dot
            dot_color = _pokemon_dot_color(lead.name)
            dot_cx = info_x + 12
            dot_cy = info_y + 13
            pygame.draw.circle(screen, dot_color, (dot_cx, dot_cy), 7)
            pygame.draw.circle(screen, (255, 255, 255), (dot_cx, dot_cy), 7, 1)
            # Pokeball divider line on dot
            pygame.draw.line(
                screen, (255, 255, 255), (dot_cx - 7, dot_cy), (dot_cx + 7, dot_cy), 1
            )

            # Name + level
            name_text = f"{lead.name}  Lv.{lead.level}"
            nlbl = self._font_med.render(name_text, True, (255, 255, 255))
            screen.blit(nlbl, (info_x + 24, info_y + 5))

            # HP bar
            bar_x = info_x + 8
            bar_y = info_y + 30
            bar_w = info_w - 16
            bar_h_px = 7
            # Border
            pygame.draw.rect(
                screen,
                COLOR_HP_BORDER,
                pygame.Rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h_px + 2),
            )
            # Background
            pygame.draw.rect(
                screen, (60, 60, 60), pygame.Rect(bar_x, bar_y, bar_w, bar_h_px)
            )
            hp_ratio = max(0.0, lead.hp_pct)
            filled = int(bar_w * hp_ratio)
            if hp_ratio > 0.5:
                hp_color = COLOR_HP_GOOD
            elif hp_ratio > 0.25:
                hp_color = COLOR_HP_MID
            else:
                hp_color = COLOR_HP_LOW
            if filled > 0:
                pygame.draw.rect(
                    screen, hp_color, pygame.Rect(bar_x, bar_y, filled, bar_h_px)
                )

            # HP numbers
            hp_txt = self._font_small.render(
                f"HP {lead.hp}/{lead.max_hp}", True, (200, 220, 200)
            )
            screen.blit(hp_txt, (info_x + 8, info_y + 40))

            # Pokeball count — right side of panel
            pb_txt = self._font_small.render(
                f"({chr(9679)}) x{self.pokeballs}", True, (200, 200, 255)
            )
            screen.blit(pb_txt, (info_x + info_w - pb_txt.get_width() - 6, info_y + 40))

    def _try_move(self, dx: int, dy: int):
        tm = self.maps[self.current_map]
        new_col = self._player_col + dx
        new_row = self._player_row + dy

        tile = tm.get_tile(new_col, new_row)
        if tile is None:
            return

        if tile in TILE_DEFS and TILE_DEFS[tile].solid:
            return

        # Block movement into NPC tile
        if (
            self.current_map == PROF_NPC_MAP
            and new_col == PROF_NPC_COL
            and new_row == PROF_NPC_ROW
        ):
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
