"""Game Over screen."""

import math
import pygame
from drift2d import Scene


class GameOverScene(Scene):
    def __init__(self):
        super().__init__()
        self.timer = 0.0

    def update(self, dt):
        self.timer += dt
        if self.timer > 1.0 and (
            self.game.input.is_action_just_pressed("jump")
            or self.game.input.is_action_just_pressed("action")
        ):
            self.game.scenes.switch("menu")

    def draw(self):
        screen = self.game.screen
        W, H = self.game.width, self.game.height
        r = self.game.renderer

        # Dark red gradient
        for y in range(0, H, 4):
            t = y / H
            c = (int(30 * (1 - t)), int(5 * (1 - t)), int(5 * (1 - t)))
            pygame.draw.rect(screen, c, (0, y, W, 4))

        shake = math.sin(self.timer * 10) * max(0, 2 - self.timer) * 3

        r.draw_text(
            "GAME OVER", W // 2 - 100 + shake, H // 2 - 30, color=(200, 50, 50), size=40
        )

        if self.timer > 1.5:
            alpha = int(min(255, (self.timer - 1.5) * 200))
            r.draw_text(
                "Press SPACE to try again",
                W // 2 - 120,
                H // 2 + 30,
                color=(alpha, alpha // 2, alpha // 2),
                size=18,
            )
