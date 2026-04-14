"""Victory screen — all levels complete!"""

import math
import random
import pygame
from drift2d import Scene, ParticleEmitter, ParticleConfig


class VictoryScene(Scene):
    def __init__(self):
        super().__init__()
        self.custom_draw = True
        self.timer = 0.0

    def enter(self):
        self.timer = 0.0
        self.game.world.clear()
        self.confetti = ParticleEmitter(
            ParticleConfig(
                count=5,
                lifetime=(1.5, 3.0),
                speed=(40, 120),
                direction=-90,
                spread=160,
                color=(255, 220, 50),
                color_end=(100, 200, 80),
                size=(2, 5),
                gravity=40,
                fade=True,
            )
        )

    def update(self, dt):
        self.timer += dt
        self.confetti.update(dt)

        if self.game.frame_count % 8 == 0:
            x = random.randint(100, self.game.width - 100)
            self.confetti.emit(x, self.game.height + 10, count=3)

        if self.timer > 2.0 and self.game.input.is_action_just_pressed("jump"):
            self.game.scenes.switch("menu")

    def draw(self):
        screen = self.game.screen
        W, H = self.game.width, self.game.height
        r = self.game.renderer

        # Gold gradient
        for y in range(0, H, 4):
            t = y / H
            c = (int(40 - 20 * t), int(30 - 10 * t), int(5))
            pygame.draw.rect(screen, c, (0, y, W, 4))

        bob = math.sin(self.timer * 2) * 8

        r.draw_text(
            "YOU WIN!", W // 2 - 90, H // 3 + bob, color=(255, 220, 50), size=48
        )

        r.draw_text(
            "All levels completed!",
            W // 2 - 105,
            H // 3 + 60,
            color=(200, 180, 80),
            size=22,
        )

        if self.timer > 2.0:
            alpha = int(min(255, (self.timer - 2.0) * 200))
            r.draw_text(
                "Press SPACE for menu",
                W // 2 - 100,
                H // 2 + 60,
                color=(alpha, alpha, alpha // 2),
                size=18,
            )

        self.confetti.draw(screen)
