"""
AutoPlay: AI controller that plays the game so Claude can watch and improve.

Simulates basic player behavior: move right, jump gaps, avoid enemies,
collect items. Not meant to be good — meant to exercise the game and
expose bugs, unfair sections, and design issues.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .engine import Game


class AutoPlayer:
    """
    Injects synthetic input to play the game automatically.
    Replaces human keyboard input with heuristic-driven actions.
    """

    def __init__(self, game: Game):
        self.game = game
        self.enabled = False
        self._jump_cooldown = 0.0
        self._stuck_timer = 0.0
        self._last_x = 0.0
        self._direction = 1  # 1 = right, -1 = left
        self._jump_requested = False
        self._frames_since_ground = 0

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def update(self, dt: float):
        """Called each frame before input.update(). Injects synthetic events."""
        if not self.enabled:
            return

        from .entity import Transform, RigidBody

        player = self.game.world.find("player")
        if not player:
            # On menu/gameover — press space to proceed
            self._inject_key(pygame.K_SPACE, press=True)
            return

        transform = player.get(Transform)
        rb = player.get(RigidBody)
        if not transform:
            return

        px, py = transform.position.x, transform.position.y
        vx = rb.velocity.x if rb else 0
        vy = rb.velocity.y if rb else 0

        # Detect if stuck
        if abs(px - self._last_x) < 2.0:
            self._stuck_timer += dt
        else:
            self._stuck_timer = 0.0
        self._last_x = px

        # Track air time
        on_ground = vy == 0 or abs(vy) < 5
        if on_ground:
            self._frames_since_ground = 0
        else:
            self._frames_since_ground += 1

        self._jump_cooldown = max(0, self._jump_cooldown - dt)

        # ── Decision making ──

        should_jump = False
        move_dir = self._direction

        # Check for gaps ahead (look at tilemap if available)
        scene = self.game.scenes.current
        tilemap = getattr(scene, "tilemap", None)

        if tilemap:
            ts = tilemap.tile_size
            # Check ground ahead
            check_x = px + move_dir * 40
            check_y = py + 20
            col, row = int(check_x // ts), int(check_y // ts)

            # Is there ground below-ahead?
            ground_ahead = False
            for r in range(row, min(row + 4, tilemap.height)):
                tile = tilemap.get_tile(col, r)
                if tile == "G":
                    ground_ahead = True
                    break

            if not ground_ahead and on_ground:
                should_jump = True  # Jump over gap

            # Is there a wall ahead?
            wall_col = int((px + move_dir * 16) // ts)
            wall_row = int(py // ts)
            wall_tile = tilemap.get_tile(wall_col, wall_row)
            if wall_tile == "G":
                should_jump = True  # Jump over wall

        # If stuck for too long, try jumping or reversing
        if self._stuck_timer > 0.5:
            should_jump = True
        if self._stuck_timer > 1.5:
            self._direction *= -1
            self._stuck_timer = 0

        # Check for enemies nearby — jump if close
        for enemy in self.game.world.query_tag("enemy"):
            et = enemy.get(Transform)
            if et:
                dx = et.position.x - px
                dy = et.position.y - py
                if abs(dx) < 80 and abs(dy) < 50:
                    should_jump = True
                    # Try to land on top of enemy
                    if dx > 0:
                        move_dir = 1
                    else:
                        move_dir = -1

        # Check for bananas nearby — move toward them
        closest_banana = None
        closest_dist = 999999
        for banana in self.game.world.query_tag("banana"):
            bt = banana.get(Transform)
            if bt:
                dist = abs(bt.position.x - px) + abs(bt.position.y - py)
                if dist < closest_dist and dist < 200:
                    closest_dist = dist
                    closest_banana = bt

        if closest_banana:
            if closest_banana.position.x > px + 10:
                move_dir = 1
            elif closest_banana.position.x < px - 10:
                move_dir = -1
            if closest_banana.position.y < py - 20:
                should_jump = True

        # Check for door — move toward it
        door = self.game.world.find("door")
        if door:
            dt2 = door.get(Transform)
            if dt2 and abs(dt2.position.x - px) < 300:
                move_dir = 1 if dt2.position.x > px else -1

        # ── Inject inputs ──

        # Movement
        if move_dir > 0:
            self._inject_key(pygame.K_RIGHT, press=True)
            self._inject_key(pygame.K_LEFT, press=False)
        else:
            self._inject_key(pygame.K_LEFT, press=True)
            self._inject_key(pygame.K_RIGHT, press=False)

        # Jump
        if should_jump and self._jump_cooldown <= 0 and on_ground:
            self._inject_key(pygame.K_SPACE, press=True)
            self._jump_cooldown = 0.4
        elif not should_jump or not on_ground:
            self._inject_key(pygame.K_SPACE, press=False)

    def _inject_key(self, key: int, press: bool):
        """Inject a synthetic keyboard event into pygame's event queue."""
        if press:
            event = pygame.event.Event(
                pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0
            )
        else:
            event = pygame.event.Event(
                pygame.KEYUP, key=key, mod=0, unicode="", scancode=0
            )
        pygame.event.post(event)
