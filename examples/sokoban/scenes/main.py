"""Drift Sokoban — grid-based puzzle game using Drift2D."""

from __future__ import annotations
from pathlib import Path
import pygame
from drift2d import Scene

# Tile characters
WALL = "W"
FLOOR = "."
PLAYER = "P"
BOX = "B"
TARGET = "T"
BOX_ON_TARGET = "X"  # internal state only — box sitting on a target
PLAYER_ON_TARGET = "Y"  # internal state only

LEVEL_FILES = [
    "level1.txt",
    "level2.txt",
    "level3.txt",
]

# Colors
COLOR_BG = (10, 12, 28)
COLOR_FLOOR = (30, 35, 55)
COLOR_FLOOR_ALT = (35, 40, 62)
COLOR_WALL = (45, 50, 80)
COLOR_WALL_EDGE = (60, 65, 100)
COLOR_PLAYER = (80, 160, 255)
COLOR_PLAYER_OUTLINE = (40, 100, 200)
COLOR_BOX = (160, 100, 50)
COLOR_BOX_OUTLINE = (120, 75, 35)
COLOR_BOX_ON_TARGET = (200, 170, 60)
COLOR_BOX_ON_TARGET_OUTLINE = (240, 210, 80)
COLOR_TARGET = (220, 200, 60)
COLOR_WIN_OVERLAY = (10, 12, 28, 180)
COLOR_HUD = (180, 190, 220)
COLOR_HUD_DIM = (80, 90, 120)


class SokobanState:
    """Pure game state — no engine coupling."""

    def __init__(self, grid: list[list[str]]):
        # grid[row][col] — chars: W . P B T X Y
        self.grid = [row[:] for row in grid]
        self.rows = len(grid)
        self.cols = max(len(r) for r in grid) if grid else 0
        self._find_entities()

    def _find_entities(self):
        self.player_col = 0
        self.player_row = 0
        self.boxes: set[tuple[int, int]] = set()
        self.targets: set[tuple[int, int]] = set()

        for r, row in enumerate(self.grid):
            for c, ch in enumerate(row):
                if ch in (PLAYER, PLAYER_ON_TARGET):
                    self.player_col, self.player_row = c, r
                if ch in (BOX, BOX_ON_TARGET):
                    self.boxes.add((c, r))
                if ch in (TARGET, BOX_ON_TARGET, PLAYER_ON_TARGET):
                    self.targets.add((c, r))

    def _get(self, col: int, row: int) -> str:
        if 0 <= row < self.rows and 0 <= col < len(self.grid[row]):
            return self.grid[row][col]
        return WALL

    def _set(self, col: int, row: int, ch: str):
        if 0 <= row < self.rows and 0 <= col < len(self.grid[row]):
            self.grid[row][col] = ch

    def try_move(self, dc: int, dr: int) -> bool:
        """Attempt to move player by (dc, dr). Returns True if move succeeded."""
        pc, pr = self.player_col, self.player_row
        nc, nr = pc + dc, pr + dr  # new player pos

        dest = self._get(nc, nr)

        if dest == WALL:
            return False

        # Check if pushing a box
        if dest in (BOX, BOX_ON_TARGET):
            bc, br = nc + dc, nr + dr  # where box would go
            box_dest = self._get(bc, br)
            if box_dest in (WALL, BOX, BOX_ON_TARGET):
                return False  # can't push

            # Move the box
            self.boxes.discard((nc, nr))
            self.boxes.add((bc, br))

            # Update grid for box source
            if (nc, nr) in self.targets:
                self._set(nc, nr, TARGET)
            else:
                self._set(nc, nr, FLOOR)

            # Update grid for box dest
            if (bc, br) in self.targets:
                self._set(bc, br, BOX_ON_TARGET)
            else:
                self._set(bc, br, BOX)

        # Move player
        if (pc, pr) in self.targets:
            self._set(pc, pr, TARGET)
        else:
            self._set(pc, pr, FLOOR)

        if (nc, nr) in self.targets:
            self._set(nc, nr, PLAYER_ON_TARGET)
        else:
            self._set(nc, nr, PLAYER)

        self.player_col, self.player_row = nc, nr
        return True

    def is_solved(self) -> bool:
        return self.boxes == self.targets and len(self.targets) > 0

    def snapshot(self) -> tuple:
        """Return a serialisable snapshot for undo."""
        return (
            self.player_col,
            self.player_row,
            frozenset(self.boxes),
            tuple(tuple(row) for row in self.grid),
        )

    @classmethod
    def from_snapshot(
        cls,
        snap: tuple,
        targets: set[tuple[int, int]],
    ) -> "SokobanState":
        pc, pr, boxes, grid_rows = snap
        grid = [list(row) for row in grid_rows]
        obj = cls.__new__(cls)
        obj.grid = grid
        obj.rows = len(grid)
        obj.cols = max(len(r) for r in grid) if grid else 0
        obj.player_col = pc
        obj.player_row = pr
        obj.boxes = set(boxes)
        obj.targets = set(targets)
        return obj


def _load_grid(path: Path) -> list[list[str]]:
    text = path.read_text().rstrip("\n")
    return [list(line) for line in text.splitlines()]


class Main(Scene):
    """Sokoban puzzle scene."""

    custom_draw = True  # we handle all rendering ourselves

    def __init__(self):
        super().__init__()
        self.level_index = 0
        self.state: SokobanState | None = None
        self.history: list[tuple] = []
        self.move_count = 0
        self.push_count = 0
        self.win = False
        self.all_done = False
        self._win_timer = 0.0
        self._tile_size = 64
        self._offset_x = 0
        self._offset_y = 0

    @property
    def _levels_dir(self) -> Path:
        return Path(__file__).parent.parent / "levels"

    def enter(self):
        self._load_level(self.level_index)

    def exit(self):
        pass

    def _load_level(self, idx: int):
        path = self._levels_dir / LEVEL_FILES[idx]
        grid = _load_grid(path)
        self.state = SokobanState(grid)
        self.history = [self.state.snapshot()]
        self.move_count = 0
        self.push_count = 0
        self.win = False
        self._win_timer = 0.0
        self._recalculate_tile_size()

    def _recalculate_tile_size(self):
        """Fit the level grid into the window with padding."""
        if not self.state:
            return
        W, H = self.game.width, self.game.height
        pad = 80  # top HUD reserve + border
        avail_w = W - pad
        avail_h = H - pad
        ts_w = avail_w // self.state.cols
        ts_h = avail_h // self.state.rows
        self._tile_size = max(16, min(ts_w, ts_h, 64))
        grid_w = self.state.cols * self._tile_size
        grid_h = self.state.rows * self._tile_size
        self._offset_x = (W - grid_w) // 2
        self._offset_y = (H - grid_h) // 2 + 20  # nudge down slightly for HUD

    def update(self, dt: float):
        if self.all_done:
            return

        if self.win:
            self._win_timer += dt
            if self._win_timer > 1.5:
                self._advance_level()
            return

        inp = self.game.input
        moved = False
        pushed = False

        directions = [
            ("move_up", 0, -1),
            ("move_down", 0, 1),
            ("move_left", -1, 0),
            ("move_right", 1, 0),
        ]

        for action, dc, dr in directions:
            if inp.is_action_just_pressed(action):
                prev_boxes = frozenset(self.state.boxes)
                ok = self.state.try_move(dc, dr)
                if ok:
                    moved = True
                    if frozenset(self.state.boxes) != prev_boxes:
                        pushed = True
                    self.history.append(self.state.snapshot())
                break  # only one direction per frame

        if moved:
            self.move_count += 1
            if pushed:
                self.push_count += 1

        # Undo with Z
        if inp.is_action_just_pressed("action"):
            self._undo()

        # Check win
        if self.state.is_solved():
            self.win = True
            self._win_timer = 0.0

    def _undo(self):
        if len(self.history) > 1:
            self.history.pop()  # discard current
            snap = self.history[-1]
            self.state = SokobanState.from_snapshot(snap, self.state.targets)
            if self.move_count > 0:
                self.move_count -= 1

    def _advance_level(self):
        next_idx = self.level_index + 1
        if next_idx >= len(LEVEL_FILES):
            self.all_done = True
        else:
            self.level_index = next_idx
            self._load_level(self.level_index)

    def draw(self):
        if not self.state:
            return

        screen = self.game.screen
        r = self.game.renderer
        ts = self._tile_size
        ox, oy = self._offset_x, self._offset_y

        # Draw floor background panel
        panel_w = self.state.cols * ts
        panel_h = self.state.rows * ts
        pygame.draw.rect(
            screen, (20, 22, 40), pygame.Rect(ox - 2, oy - 2, panel_w + 4, panel_h + 4)
        )

        # Draw tiles
        for row in range(self.state.rows):
            for col in range(len(self.state.grid[row])):
                ch = self.state.grid[row][col]
                px = ox + col * ts
                py = oy + row * ts

                if ch == WALL:
                    # Wall body
                    pygame.draw.rect(screen, COLOR_WALL, pygame.Rect(px, py, ts, ts))
                    # Wall top edge highlight
                    pygame.draw.rect(
                        screen, COLOR_WALL_EDGE, pygame.Rect(px, py, ts, 3)
                    )
                    pygame.draw.rect(
                        screen, COLOR_WALL_EDGE, pygame.Rect(px, py, 3, ts)
                    )
                else:
                    # Floor (checkerboard subtle pattern)
                    floor_col = COLOR_FLOOR if (row + col) % 2 == 0 else COLOR_FLOOR_ALT
                    pygame.draw.rect(screen, floor_col, pygame.Rect(px, py, ts, ts))

                    # Target dot
                    if ch in (TARGET, BOX_ON_TARGET, PLAYER_ON_TARGET):
                        cx = px + ts // 2
                        cy = py + ts // 2
                        r_dot = max(4, ts // 5)
                        pygame.draw.circle(screen, COLOR_TARGET, (cx, cy), r_dot)
                        pygame.draw.circle(
                            screen, (255, 240, 120), (cx, cy), max(2, r_dot - 2), 1
                        )

                    # Box
                    if ch in (BOX, BOX_ON_TARGET):
                        margin = max(3, ts // 8)
                        bx = px + margin
                        by = py + margin
                        bw = ts - margin * 2
                        bh = ts - margin * 2
                        box_col = (
                            COLOR_BOX_ON_TARGET if ch == BOX_ON_TARGET else COLOR_BOX
                        )
                        box_out = (
                            COLOR_BOX_ON_TARGET_OUTLINE
                            if ch == BOX_ON_TARGET
                            else COLOR_BOX_OUTLINE
                        )
                        pygame.draw.rect(
                            screen,
                            box_col,
                            pygame.Rect(bx, by, bw, bh),
                            border_radius=3,
                        )
                        pygame.draw.rect(
                            screen,
                            box_out,
                            pygame.Rect(bx, by, bw, bh),
                            2,
                            border_radius=3,
                        )
                        # Cross pattern on box face
                        mid_x = bx + bw // 2
                        mid_y = by + bh // 2
                        pygame.draw.line(
                            screen, box_out, (bx + 4, mid_y), (bx + bw - 4, mid_y), 1
                        )
                        pygame.draw.line(
                            screen, box_out, (mid_x, by + 4), (mid_x, by + bh - 4), 1
                        )

                    # Player
                    if ch in (PLAYER, PLAYER_ON_TARGET):
                        cx = px + ts // 2
                        cy = py + ts // 2
                        p_r = max(5, ts // 2 - 4)
                        pygame.draw.circle(screen, COLOR_PLAYER, (cx, cy), p_r)
                        pygame.draw.circle(
                            screen, COLOR_PLAYER_OUTLINE, (cx, cy), p_r, 2
                        )
                        # Eyes
                        eye_r = max(2, p_r // 4)
                        pygame.draw.circle(
                            screen, (255, 255, 255), (cx - eye_r - 1, cy - 2), eye_r
                        )
                        pygame.draw.circle(
                            screen, (255, 255, 255), (cx + eye_r + 1, cy - 2), eye_r
                        )

        # HUD
        hud_y = 8
        r.draw_text(
            f"Level {self.level_index + 1}/{len(LEVEL_FILES)}",
            10,
            hud_y,
            color=COLOR_HUD,
            size=18,
        )
        r.draw_text(
            f"Moves: {self.move_count}  Pushes: {self.push_count}",
            self.game.width // 2 - 80,
            hud_y,
            color=COLOR_HUD,
            size=18,
        )
        r.draw_text(
            "Arrows/WASD: move   Z: undo",
            10,
            self.game.height - 24,
            color=COLOR_HUD_DIM,
            size=14,
        )

        # Win overlay
        if self.win and not self.all_done:
            overlay = pygame.Surface(
                (self.game.width, self.game.height), pygame.SRCALPHA
            )
            overlay.fill((10, 12, 28, 160))
            screen.blit(overlay, (0, 0))
            r.draw_text(
                "Level Clear!",
                self.game.width // 2 - 90,
                self.game.height // 2 - 20,
                color=(100, 240, 160),
                size=40,
            )
            r.draw_text(
                f"Moves: {self.move_count}   Pushes: {self.push_count}",
                self.game.width // 2 - 90,
                self.game.height // 2 + 30,
                color=COLOR_HUD,
                size=20,
            )

        # All levels done
        if self.all_done:
            overlay = pygame.Surface(
                (self.game.width, self.game.height), pygame.SRCALPHA
            )
            overlay.fill((10, 12, 28, 200))
            screen.blit(overlay, (0, 0))
            r.draw_text(
                "You Win!",
                self.game.width // 2 - 70,
                self.game.height // 2 - 40,
                color=(240, 220, 80),
                size=56,
            )
            r.draw_text(
                "All puzzles solved!",
                self.game.width // 2 - 100,
                self.game.height // 2 + 30,
                color=COLOR_HUD,
                size=24,
            )
