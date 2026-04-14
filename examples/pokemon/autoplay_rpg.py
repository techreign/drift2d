"""
RPG AutoPlayer: navigates the overworld, fights battles, catches pokemon.
Injects keyboard events like the platformer bot but with RPG logic.
"""

from __future__ import annotations
import random
import pygame


class RPGAutoPlayer:
    """Bot that plays a Pokemon-style RPG autonomously."""

    def __init__(self, game):
        self.game = game
        self.enabled = True
        self._move_cooldown = 0.0
        self._action_cooldown = 0.0
        self._wander_dir = None
        self._last_pos = (0, 0)
        self._stuck_timer = 0.0
        self._explore_target = "right"  # bias toward right to leave town
        self._steps_taken = 0

    def update(self, dt: float):
        if not self.enabled:
            return

        self._move_cooldown = max(0, self._move_cooldown - dt)
        self._action_cooldown = max(0, self._action_cooldown - dt)

        scene = self.game.scenes.current
        if not scene:
            return

        scene_class = type(scene).__name__

        if scene_class == "TitleScene":
            self._play_title(scene, dt)
        elif scene_class == "OverworldScene":
            self._play_overworld(scene, dt)
        elif scene_class == "BattleScene":
            self._play_battle(scene, dt)

    def _play_title(self, scene, dt):
        """Navigate title screen: pick a starter."""
        if self._action_cooldown > 0:
            return

        if scene.state == "title":
            self._press(pygame.K_SPACE)
            self._action_cooldown = 0.5

        elif scene.state == "choose_starter":
            # Pick a random starter then confirm
            if random.random() < 0.3:
                self._press(pygame.K_RIGHT)
                self._action_cooldown = 0.3
            else:
                self._press(pygame.K_SPACE)
                self._action_cooldown = 0.5

        elif scene.state == "confirm":
            self._press(pygame.K_SPACE)
            self._action_cooldown = 0.5

    def _play_overworld(self, scene, dt):
        """Navigate the overworld: explore, walk into grass, interact."""
        if self._move_cooldown > 0:
            return

        # Check if sliding (don't input during slide)
        if hasattr(scene, "_sliding") and scene._sliding:
            return

        # Detect if stuck
        pos = (getattr(scene, "_player_col", 0), getattr(scene, "_player_row", 0))
        if pos == self._last_pos:
            self._stuck_timer += 0.2
        else:
            self._stuck_timer = 0
        self._last_pos = pos

        # Choose direction — seek grass for encounters, or explore
        directions = [pygame.K_RIGHT, pygame.K_DOWN, pygame.K_UP, pygame.K_LEFT]
        dir_offsets = [(1, 0), (0, 1), (0, -1), (-1, 0)]

        # Try to find nearby grass tiles and move toward them
        col = getattr(scene, "_player_col", 0)
        row = getattr(scene, "_player_row", 0)
        current_map = getattr(scene, "current_map", "town")
        tilemap = scene.maps.get(current_map) if hasattr(scene, "maps") else None

        grass_dir = None
        if tilemap and current_map != "town":
            # Look for grass in each direction (check 3 tiles ahead)
            for i, (dc, dr) in enumerate(dir_offsets):
                for dist in range(1, 4):
                    tc, tr = col + dc * dist, row + dr * dist
                    tile = tilemap.get_tile(tc, tr)
                    if tile == "G":
                        grass_dir = i
                        break
                if grass_dir is not None:
                    break

        if self._stuck_timer > 2.0:
            key = random.choice(directions)
            self._stuck_timer = 0
        elif grass_dir is not None and random.random() < 0.7:
            # Move toward grass 70% of the time
            key = directions[grass_dir]
        elif self._steps_taken < 15:
            # Early: go right to leave town
            key = random.choices(directions, weights=[5, 2, 2, 1])[0]
        else:
            key = random.choices(directions, weights=[3, 3, 3, 1])[0]

        self._press(key)
        self._move_cooldown = 0.2
        self._steps_taken += 1

        # Occasionally try to interact (Z) for pokemon center etc.
        if random.random() < 0.05:
            self._press(pygame.K_z)

    def _play_battle(self, scene, dt):
        """Fight battles: pick moves, catch pokemon, switch."""
        if self._action_cooldown > 0:
            return

        state = getattr(scene, "state", "")

        if state in ("INTRO", "MESSAGE", "ANIMATING", "ENEMY_TURN"):
            # Toggle Z every other frame — no cooldown so just_pressed fires
            if self.game.frame_count % 2 == 0:
                self._release(pygame.K_z)
            else:
                self._press(pygame.K_z)
            return  # no cooldown — keep toggling

        elif state == "CHOOSE_ACTION":
            # Usually fight, sometimes try to catch, rarely run
            r = random.random()
            if r < 0.7:
                # FIGHT (top-left, index 0)
                self._press(pygame.K_z)
            elif r < 0.85:
                # BAG/catch (top-right, index 1)
                self._press(pygame.K_RIGHT)
                self._action_cooldown = 0.15
                return
            else:
                # RUN (bottom-right, index 3)
                self._press(pygame.K_DOWN)
                self._action_cooldown = 0.15
                return
            self._action_cooldown = 0.3

        elif state == "CHOOSE_MOVE":
            # Pick a random move
            move_idx = random.randint(0, 3)
            if move_idx == 1:
                self._press(pygame.K_RIGHT)
            elif move_idx == 2:
                self._press(pygame.K_DOWN)
            elif move_idx == 3:
                self._press(pygame.K_RIGHT)
                self._action_cooldown = 0.1
                return
            self._press(pygame.K_z)
            self._action_cooldown = 0.4

        elif state == "CHOOSE_POKEMON":
            # Just pick first alive pokemon
            self._press(pygame.K_z)
            self._action_cooldown = 0.3

        elif state == "CATCH":
            self._press(pygame.K_z)
            self._action_cooldown = 0.5

        elif state in ("VICTORY", "DEFEAT"):
            self._press(pygame.K_z)
            self._action_cooldown = 0.5

        else:
            # Unknown state — press Z to advance
            if self.game.frame_count % 20 < 10:
                self._press(pygame.K_z)
            else:
                self._release(pygame.K_z)
            self._action_cooldown = 0.2

    def _press(self, key):
        """Inject key press."""
        pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0)
        )

    def _release(self, key):
        """Inject key release."""
        pygame.event.post(
            pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode="", scancode=0)
        )
