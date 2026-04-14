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
        self._vert_stuck_timer = 0.0
        self._last_x = 0.0
        self._last_y = 0.0
        self._direction = 1  # 1 = right, -1 = left
        self._jump_requested = False
        self._frames_since_ground = 0
        # Random jump variation: offset in [-0.15, +0.15] seconds, changes periodically
        self._jump_variation = 0.0
        self._jump_variation_timer = 0.0

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
            # On menu/gameover — toggle space every 30 frames to trigger just_pressed
            if self.game.frame_count % 30 < 15:
                self._inject_key(pygame.K_SPACE, press=True)
            else:
                self._inject_key(pygame.K_SPACE, press=False)
            return

        transform = player.get(Transform)
        rb = player.get(RigidBody)
        if not transform:
            return

        px, py = transform.position.x, transform.position.y
        vx = rb.velocity.x if rb else 0
        vy = rb.velocity.y if rb else 0

        # Detect if stuck horizontally
        if abs(px - self._last_x) < 2.0:
            self._stuck_timer += dt
        else:
            self._stuck_timer = 0.0
        self._last_x = px

        # Detect if stuck vertically (not moving up or down for 2s)
        if abs(py - self._last_y) < 2.0:
            self._vert_stuck_timer += dt
        else:
            self._vert_stuck_timer = 0.0
        self._last_y = py

        # Randomize jump timing variation periodically so the bot isn't robotic
        self._jump_variation_timer -= dt
        if self._jump_variation_timer <= 0:
            import random as _rnd

            self._jump_variation = _rnd.uniform(-0.12, 0.12)
            self._jump_variation_timer = _rnd.uniform(0.8, 2.0)

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

        # If stuck horizontally for too long, escalate unstuck strategies
        if self._stuck_timer > 0.5:
            should_jump = True
        if self._stuck_timer > 1.5:
            self._direction *= -1
            self._stuck_timer = 0
        if self._stuck_timer > 3.0:
            # Desperate: just jump and move toward the door
            should_jump = True
            door = self.game.world.find("door")
            if door:
                dt3 = door.get(Transform)
                if dt3:
                    move_dir = 1 if dt3.position.x > px else -1
            self._stuck_timer = 0

        # If stuck vertically (not gaining/losing height) for 2s, try jumping
        if self._vert_stuck_timer > 2.0 and on_ground:
            should_jump = True
            self._vert_stuck_timer = 0.0

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

        # Check for barrels nearby — move toward them and jump into them
        for barrel in self.game.world.query_tag("barrel"):
            bt = barrel.get(Transform)
            if bt:
                bdx = bt.position.x - px
                bdy = bt.position.y - py
                if abs(bdx) < 120 and abs(bdy) < 80:
                    # Move toward the barrel
                    if bdx > 10:
                        move_dir = 1
                    elif bdx < -10:
                        move_dir = -1
                    # Jump into it if close and on ground
                    if abs(bdx) < 50 and on_ground:
                        should_jump = True

        # If falling fast, steer toward nearest platform below
        if vy > 200:
            best_platform_x = None
            best_dist = 999999
            if tilemap:
                ts = tilemap.tile_size
                look_rows = range(int(py // ts), min(int(py // ts) + 8, tilemap.height))
                for r in look_rows:
                    for c in range(
                        max(0, int(px // ts) - 6), min(tilemap.width, int(px // ts) + 6)
                    ):
                        if tilemap.get_tile(c, r) == "G":
                            tile_cx = c * ts + ts / 2
                            dist = abs(tile_cx - px)
                            if dist < best_dist:
                                best_dist = dist
                                best_platform_x = tile_cx
            if best_platform_x is not None:
                if best_platform_x > px + 8:
                    move_dir = 1
                elif best_platform_x < px - 8:
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

        # Always move toward the door (primary goal)
        door = self.game.world.find("door")
        if door:
            dt2 = door.get(Transform)
            if dt2:
                dx_door = dt2.position.x - px
                # Always bias toward door direction
                if abs(dx_door) > 30:
                    move_dir = 1 if dx_door > 0 else -1

        # ── Inject inputs ──

        # Movement
        if move_dir > 0:
            self._inject_key(pygame.K_RIGHT, press=True)
            self._inject_key(pygame.K_LEFT, press=False)
        else:
            self._inject_key(pygame.K_LEFT, press=True)
            self._inject_key(pygame.K_RIGHT, press=False)

        # Jump — apply random variation so the bot isn't frame-perfect every time
        effective_cooldown = max(0.0, self._jump_cooldown + self._jump_variation)
        if should_jump and effective_cooldown <= 0 and on_ground:
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
