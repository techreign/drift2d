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


# ── Helpers ────────────────────────────────────────────────────────────────────


def _hp_color(pct: float) -> tuple:
    if pct > 0.5:
        return COL_HP_GREEN
    if pct > 0.25:
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
        player_party: list["Pokemon"],
        wild_pokemon: "Pokemon",
        pokeballs: int = 5,
    ):
        super().__init__()

        self.player_party = player_party  # live reference — HP/XP changes persist
        self.wild = wild_pokemon
        self.pokeballs = pokeballs

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

        # HP bar animation
        self._player_hp_display = float(self._player.hp)
        self._enemy_hp_display = float(self.wild.hp)

        # Slide-in animation (intro)
        self._intro_timer = 0.0
        self._intro_done = False
        self._enemy_slide = float(W)  # starts off-screen right
        self._player_slide = float(-W)  # starts off-screen left

        # Hit flash / shake
        self._flash_timer = 0.0  # white overlay alpha (0-255)
        self._shake_timer = 0.0
        self._shake_target = "none"  # "player" | "enemy"

        # XP gain messages buffered for VICTORY flow
        self._post_messages: list[str] = []

        # Catch animation timer
        self._catch_timer = 0.0
        self._catch_result = False

        # Deferred next state after MESSAGE drains
        self._after_message: State = State.CHOOSE_ACTION

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def _player(self) -> "Pokemon":
        return self.player_party[self._player_idx]

    @property
    def _screen(self) -> pygame.Surface:
        return self.game.screen  # type: ignore[union-attr]

    # ── Scene lifecycle ───────────────────────────────────────────────────────

    def enter(self):
        self._state = State.INTRO
        self._player_hp_display = float(self._player.hp)
        self._enemy_hp_display = float(self.wild.hp)
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
            # Queue empty — go to deferred state
            self._state = self._after_message
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
            if eff > 1.5:
                msgs.append("It's super effective!")
                self._shake_target = "enemy"
                self._shake_timer = 0.35
            elif eff < 0.5:
                msgs.append("It's not very effective...")
            # trigger flash
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
            if eff > 1.5:
                msgs.append("It's super effective!")
                self._shake_target = "player"
                self._shake_timer = 0.35
            elif eff < 0.5:
                msgs.append("It's not very effective...")
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

    # ── Background ────────────────────────────────────────────────────────────

    def _draw_background(self, screen: pygame.Surface):
        # Vertical gradient: top lighter, bottom darker green
        for y in range(H):
            ratio = y / H
            r = int(_lerp(COL_BG_TOP[0], COL_BG_BOT[0], ratio))
            g = int(_lerp(COL_BG_TOP[1], COL_BG_BOT[1], ratio))
            b = int(_lerp(COL_BG_TOP[2], COL_BG_BOT[2], ratio))
            pygame.draw.line(screen, (r, g, b), (0, y), (W, y))

        # Ground platform for player pokemon
        pygame.draw.ellipse(
            screen,
            (60, 130, 50),
            pygame.Rect(PLAYER_CENTER[0] - 80, PLAYER_CENTER[1] + 50, 160, 30),
        )
        # Ground platform for enemy pokemon
        pygame.draw.ellipse(
            screen,
            (80, 155, 65),
            pygame.Rect(ENEMY_CENTER[0] - 60, ENEMY_CENTER[1] + 40, 120, 22),
        )

    # ── Pokemon circles ───────────────────────────────────────────────────────

    def _draw_pokemon(self, screen: pygame.Surface, t: float):
        # --- Enemy pokemon ---
        ex = int(self._enemy_slide)
        ey = ENEMY_CENTER[1]

        if self._shake_target == "enemy" and self._shake_timer > 0:
            ex += int(math.sin(self._shake_timer * 60) * 6)

        # Shadow
        pygame.draw.ellipse(
            screen,
            (40, 80, 35),
            pygame.Rect(ex - ENEMY_RADIUS, ey + ENEMY_RADIUS - 8, ENEMY_RADIUS * 2, 16),
        )

        if not self.wild.is_fainted:
            # Body circle
            pygame.draw.circle(screen, self.wild.color, (ex, ey), ENEMY_RADIUS)
            # Outline
            pygame.draw.circle(screen, COL_BLACK, (ex, ey), ENEMY_RADIUS, 3)
            # Type initial
            font = self._font(28)
            letter = self.wild.ptype[0].upper()
            lsurf = font.render(letter, True, COL_WHITE)
            lrect = lsurf.get_rect(center=(ex, ey))
            screen.blit(lsurf, lrect)
        else:
            # Fainted: X mark
            pygame.draw.circle(screen, (100, 100, 100), (ex, ey), ENEMY_RADIUS)
            pygame.draw.circle(screen, COL_BLACK, (ex, ey), ENEMY_RADIUS, 3)
            font = self._font(32)
            xs = font.render("X", True, (200, 50, 50))
            screen.blit(xs, xs.get_rect(center=(ex, ey)))

        # --- Player pokemon ---
        px = int(self._player_slide)
        py = PLAYER_CENTER[1]

        if self._shake_target == "player" and self._shake_timer > 0:
            px += int(math.sin(self._shake_timer * 60) * 6)

        # Idle bob animation
        bob = int(math.sin(t * 2.5) * 4)
        py += bob

        # Shadow
        pygame.draw.ellipse(
            screen,
            (40, 80, 35),
            pygame.Rect(
                px - PLAYER_RADIUS, py + PLAYER_RADIUS - 10, PLAYER_RADIUS * 2, 20
            ),
        )

        if not self._player.is_fainted:
            pygame.draw.circle(screen, self._player.color, (px, py), PLAYER_RADIUS)
            pygame.draw.circle(screen, COL_BLACK, (px, py), PLAYER_RADIUS, 3)
            font = self._font(36)
            letter = self._player.ptype[0].upper()
            lsurf = font.render(letter, True, COL_WHITE)
            lrect = lsurf.get_rect(center=(px, py))
            screen.blit(lsurf, lrect)
        else:
            pygame.draw.circle(screen, (100, 100, 100), (px, py), PLAYER_RADIUS)
            pygame.draw.circle(screen, COL_BLACK, (px, py), PLAYER_RADIUS, 3)
            font = self._font(36)
            xs = font.render("X", True, (200, 50, 50))
            screen.blit(xs, xs.get_rect(center=(px, py)))

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
        )

        # Player plate — bottom-right area
        self._draw_name_plate(
            screen,
            x=480,
            y=290,
            pokemon=self._player,
            hp_display=self._player_hp_display,
            show_hp_num=True,
        )

    def _draw_name_plate(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        pokemon: "Pokemon",
        hp_display: float,
        show_hp_num: bool,
    ):
        plate_w, plate_h = 280, 90

        # Background panel
        panel = pygame.Surface((plate_w, plate_h), pygame.SRCALPHA)
        panel.fill((20, 24, 32, 210))
        screen.blit(panel, (x, y))
        pygame.draw.rect(screen, COL_GRAY, pygame.Rect(x, y, plate_w, plate_h), 2)

        font_name = self._font(20)
        font_lv = self._font(16)
        font_hp = self._font(15)

        # Name
        name_surf = font_name.render(pokemon.name, True, COL_WHITE)
        screen.blit(name_surf, (x + 10, y + 8))

        # Level
        lv_surf = font_lv.render(f"Lv.{pokemon.level}", True, (200, 200, 200))
        screen.blit(lv_surf, (x + plate_w - lv_surf.get_width() - 10, y + 8))

        # HP label
        hp_lbl = font_hp.render("HP", True, (180, 180, 180))
        screen.blit(hp_lbl, (x + 10, y + 36))

        # HP bar background
        bar_x = x + 38
        bar_y = y + 38
        bar_w = plate_w - 50
        bar_h = 12
        pygame.draw.rect(screen, COL_HP_BG, pygame.Rect(bar_x, bar_y, bar_w, bar_h))

        # HP bar fill
        pct = hp_display / pokemon.max_hp if pokemon.max_hp > 0 else 0
        pct = max(0.0, min(1.0, pct))
        fill_w = int(bar_w * pct)
        if fill_w > 0:
            pygame.draw.rect(
                screen, _hp_color(pct), pygame.Rect(bar_x, bar_y, fill_w, bar_h)
            )
        pygame.draw.rect(screen, COL_GRAY, pygame.Rect(bar_x, bar_y, bar_w, bar_h), 1)

        # HP numbers (player side only)
        if show_hp_num:
            hp_num = font_hp.render(
                f"{max(0, int(round(hp_display)))}/{pokemon.max_hp}",
                True,
                COL_WHITE,
            )
            screen.blit(hp_num, (x + 10, y + 58))

    # ── Menu / message box ────────────────────────────────────────────────────

    def _draw_menu(self, screen: pygame.Surface, t: float):
        # Dark menu box at bottom
        pygame.draw.rect(screen, COL_PANEL, MENU_BOX_RECT)
        pygame.draw.rect(screen, COL_GRAY, MENU_BOX_RECT, 2)

        state = self._state

        if state == State.MESSAGE or state == State.INTRO:
            self._draw_message_box(screen)
        elif state == State.CHOOSE_ACTION:
            self._draw_action_menu(screen)
        elif state == State.CHOOSE_MOVE:
            self._draw_move_menu(screen)
        elif state == State.CHOOSE_POKEMON:
            self._draw_party_menu(screen)
        elif state == State.CATCH:
            self._draw_message_box(screen)
        elif state == State.VICTORY:
            self._draw_message_box(screen)
        elif state == State.DEFEAT:
            self._draw_message_box(screen)

    def _draw_message_box(self, screen: pygame.Surface):
        font = self._font(22)
        text = self._displayed if self._displayed else self._current_msg

        # Word-wrap naive: split on spaces, fit 44 chars per line
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

        my = MENU_BOX_RECT.y + 20
        for line in lines[:4]:
            surf = font.render(line, True, COL_WHITE)
            screen.blit(surf, (MENU_BOX_RECT.x + 24, my))
            my += 32

        # Blinking cursor when done
        if self._msg_done and int(self.game.time * 4) % 2 == 0:  # type: ignore
            tri_x = MENU_BOX_RECT.right - 30
            tri_y = MENU_BOX_RECT.bottom - 24
            pygame.draw.polygon(
                screen,
                COL_WHITE,
                [(tri_x, tri_y), (tri_x + 10, tri_y), (tri_x + 5, tri_y + 10)],
            )

    def _draw_action_menu(self, screen: pygame.Surface):
        # Left side: what to do text
        font_prompt = self._font(20)
        surf = font_prompt.render("What will", True, COL_WHITE)
        screen.blit(surf, (24, MENU_BOX_RECT.y + 18))
        surf2 = font_prompt.render(f"{self._player.name} do?", True, COL_WHITE)
        screen.blit(surf2, (24, MENU_BOX_RECT.y + 44))

        # Right side: 2x2 grid of action buttons
        font_btn = self._font(22)
        btn_w, btn_h = 160, 60
        start_x = MENU_BOX_RECT.x + 430
        start_y = MENU_BOX_RECT.y + 18

        for i, label in enumerate(ACTION_LABELS):
            col = i % 2
            row = i // 2
            bx = start_x + col * (btn_w + 10)
            by = start_y + row * (btn_h + 8)

            selected = i == self._action_idx
            bg_col = (60, 70, 90) if not selected else (80, 110, 160)
            border = COL_SELECT if selected else COL_GRAY

            pygame.draw.rect(screen, bg_col, pygame.Rect(bx, by, btn_w, btn_h))
            pygame.draw.rect(screen, border, pygame.Rect(bx, by, btn_w, btn_h), 2)

            arrow = "> " if selected else "  "
            txt = font_btn.render(
                arrow + label, True, COL_WHITE if not selected else COL_SELECT
            )
            trect = txt.get_rect(center=(bx + btn_w // 2, by + btn_h // 2))
            screen.blit(txt, trect)

    def _draw_move_menu(self, screen: pygame.Surface):
        moves = self._player.moves
        font_n = self._font(18)
        font_pp = self._font(14)
        font_ty = self._font(13)

        cell_w = (W - 40) // 2
        cell_h = (MENU_BOX_RECT.height - 20) // 2
        ox, oy = MENU_BOX_RECT.x + 10, MENU_BOX_RECT.y + 10

        for i in range(4):
            col = i % 2
            row = i // 2
            cx = ox + col * (cell_w + 10)
            cy = oy + row * (cell_h + 6)

            if i < len(moves):
                move = moves[i]
                selected = i == self._move_idx
                tc = TYPE_COLORS.get(move.type, (168, 168, 168))
                bg = tuple(min(255, int(c * 0.45)) for c in tc)
                border = tc if selected else COL_GRAY

                pygame.draw.rect(screen, bg, pygame.Rect(cx, cy, cell_w, cell_h))
                pygame.draw.rect(
                    screen,
                    border,
                    pygame.Rect(cx, cy, cell_w, cell_h),
                    2 if not selected else 3,
                )

                # Move name
                nsurf = font_n.render(move.name, True, COL_WHITE)
                screen.blit(nsurf, (cx + 8, cy + 8))

                # PP
                pp_col = (
                    COL_HP_GREEN
                    if move.pp_current > move.pp // 2
                    else (COL_HP_YELLOW if move.pp_current > 0 else COL_HP_RED)
                )
                pp_surf = font_pp.render(
                    f"PP {move.pp_current}/{move.pp}", True, pp_col
                )
                screen.blit(pp_surf, (cx + 8, cy + cell_h - 26))

                # Type badge
                type_surf = font_ty.render(move.type.upper(), True, tc)
                trect = type_surf.get_rect(right=cx + cell_w - 6, top=cy + 8)
                screen.blit(type_surf, trect)
            else:
                # Empty slot
                pygame.draw.rect(
                    screen, (40, 44, 55), pygame.Rect(cx, cy, cell_w, cell_h)
                )
                pygame.draw.rect(
                    screen, COL_GRAY, pygame.Rect(cx, cy, cell_w, cell_h), 1
                )
                dash = font_n.render("—", True, COL_GRAY)
                screen.blit(
                    dash, dash.get_rect(center=(cx + cell_w // 2, cy + cell_h // 2))
                )

        # Cancel hint
        hint = self._font(14).render("[X] Back", True, (160, 160, 160))
        screen.blit(hint, (ox + 2, MENU_BOX_RECT.bottom - 20))

    def _draw_party_menu(self, screen: pygame.Surface):
        font_n = self._font(18)
        font_hp = self._font(14)

        ox = MENU_BOX_RECT.x + 16
        oy = MENU_BOX_RECT.y + 10
        row_h = (MENU_BOX_RECT.height - 24) // max(1, len(self.player_party))
        row_h = min(row_h, 50)

        title = self._font(16).render("Choose Pokemon  [X] Back", True, (180, 180, 180))
        screen.blit(title, (ox, oy))
        oy += 22

        for i, p in enumerate(self.player_party):
            selected = i == self._party_idx
            by = oy + i * (row_h + 4)

            bg = (60, 80, 120) if selected else (30, 34, 50)
            pygame.draw.rect(screen, bg, pygame.Rect(ox, by, W - 32, row_h))
            border = COL_SELECT if selected else COL_GRAY
            pygame.draw.rect(screen, border, pygame.Rect(ox, by, W - 32, row_h), 2)

            # Color dot
            pygame.draw.circle(screen, p.color, (ox + 18, by + row_h // 2), 10)
            pygame.draw.circle(screen, COL_BLACK, (ox + 18, by + row_h // 2), 10, 2)

            # Name + level
            label = f"{p.name}  Lv.{p.level}"
            col = (180, 180, 180) if p.is_fainted else COL_WHITE
            nsurf = font_n.render(label, True, col)
            screen.blit(nsurf, (ox + 36, by + 4))

            # HP bar
            bar_w = 150
            bar_x = W - 200
            bar_y = by + 8
            pct = p.hp_pct
            pygame.draw.rect(screen, COL_HP_BG, pygame.Rect(bar_x, bar_y, bar_w, 10))
            if pct > 0:
                pygame.draw.rect(
                    screen,
                    _hp_color(pct),
                    pygame.Rect(bar_x, bar_y, int(bar_w * pct), 10),
                )
            pygame.draw.rect(screen, COL_GRAY, pygame.Rect(bar_x, bar_y, bar_w, 10), 1)

            hp_txt = font_hp.render(
                f"{max(0, p.hp)}/{p.max_hp}" if not p.is_fainted else "Fainted",
                True,
                (200, 200, 200) if not p.is_fainted else (200, 80, 80),
            )
            screen.blit(hp_txt, (bar_x, by + row_h - 18))

    # ── Hit flash overlay ─────────────────────────────────────────────────────

    def _draw_hit_flash(self, screen: pygame.Surface):
        if self._flash_timer > 0:
            alpha = int(min(255, self._flash_timer))
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((255, 255, 255, alpha // 4))
            screen.blit(flash, (0, 0))

    # ── Font helper ───────────────────────────────────────────────────────────

    def _font(self, size: int) -> pygame.font.Font:
        return pygame.font.SysFont(None, size)

    # ── Message state machine override ────────────────────────────────────────
    # We need to intercept _advance_message when queue drains to check sentinel

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
