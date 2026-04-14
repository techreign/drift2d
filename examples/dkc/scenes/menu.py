"""Title screen with jungle vibes."""

import math
import random
import pygame
from drift2d import Scene, ParticleEmitter, ParticleConfig


class MenuScene(Scene):
    def __init__(self):
        super().__init__()
        self.custom_draw = True
        self.fireflies = ParticleEmitter(
            ParticleConfig(
                count=1,
                lifetime=(2.0, 4.0),
                speed=(10, 30),
                spread=360,
                color=(180, 255, 100),
                color_end=(50, 100, 30),
                size=(1, 3),
                gravity=-5,
                fade=True,
            )
        )
        self.timer = 0.0

    def enter(self):
        pass

    def update(self, dt):
        self.timer += dt
        self.fireflies.update(dt)

        # Emit fireflies randomly
        if self.game.frame_count % 20 == 0:
            x = random.randint(50, self.game.width - 50)
            y = random.randint(200, self.game.height - 50)
            self.fireflies.emit(x, y, count=1)

        if self.game.input.is_action_just_pressed(
            "jump"
        ) or self.game.input.is_action_just_pressed("action"):
            from scenes.game import GameScene

            game_scene = GameScene(level_num=1)
            self.game.scenes.register("level_1", game_scene)
            self.game.scenes.switch("level_1")

    def draw(self):
        screen = self.game.screen
        W, H = self.game.width, self.game.height
        r = self.game.renderer

        # Dark jungle gradient
        for y in range(0, H, 4):
            t = y / H
            c = (int(5 + 10 * t), int(15 + 10 * t), int(5 + 15 * t))
            pygame.draw.rect(screen, c, (0, y, W, 4))

        # Ground silhouette
        pygame.draw.rect(screen, (20, 40, 15), (0, H - 80, W, 80))
        for x in range(0, W, 40):
            h = random.Random(x).randint(10, 40)
            pygame.draw.rect(screen, (15, 35, 12), (x, H - 80 - h, 30, h))

        # Vine silhouettes
        for i in range(8):
            vx = 100 * i + 50
            sway = math.sin(self.timer * 1.2 + i) * 12
            pygame.draw.line(
                screen, (20, 50, 18), (vx, 0), (int(vx + sway), 150 + i * 20), 2
            )

        # Title
        bob = math.sin(self.timer * 2) * 5
        r.draw_text("JUNGLE", W // 2 - 115, 120 + bob, color=(100, 200, 80), size=52)
        r.draw_text("KONG", W // 2 - 70, 175 + bob, color=(255, 220, 50), size=48)

        # Subtitle
        alpha = int(128 + 127 * math.sin(self.timer * 3))
        r.draw_text(
            "Press SPACE to start",
            W // 2 - 105,
            300,
            color=(alpha, alpha, alpha // 2),
            size=20,
        )

        # Controls hint
        r.draw_text(
            "WASD/Arrows: Move   SPACE: Jump",
            W // 2 - 155,
            H - 40,
            color=(60, 80, 50),
            size=16,
        )

        # Fireflies
        self.fireflies.draw(screen)
