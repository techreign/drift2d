"""Title screen with starter pokemon selection."""

import math
import pygame
from drift2d import Scene
from core.pokemon import Pokemon, POKEDEX
from core.types import get_type_color


STARTERS = ["charmander", "squirtle", "bulbasaur"]
STARTER_DESCRIPTIONS = {
    "charmander": "Fire type. High Sp.Attack and Speed.",
    "squirtle": "Water type. High Defense and Sp.Defense.",
    "bulbasaur": "Grass type. Balanced stats all around.",
}


class TitleScene(Scene):
    def __init__(self):
        super().__init__()
        self.custom_draw = True
        self.state = "title"  # title -> choose_starter -> confirm
        self.timer = 0.0
        self.selected = 0
        self.chosen_starter = None

    def enter(self):
        self.timer = 0.0
        self.state = "title"
        self.selected = 0

    def update(self, dt):
        self.timer += dt

        if self.state == "title":
            if self.game.input.is_action_just_pressed(
                "jump"
            ) or self.game.input.is_action_just_pressed("action"):
                self.state = "choose_starter"

        elif self.state == "choose_starter":
            if self.game.input.is_action_just_pressed("move_left"):
                self.selected = (self.selected - 1) % 3
            elif self.game.input.is_action_just_pressed("move_right"):
                self.selected = (self.selected + 1) % 3
            elif self.game.input.is_action_just_pressed(
                "jump"
            ) or self.game.input.is_action_just_pressed("action"):
                self.state = "confirm"
                self.timer = 0.0

        elif self.state == "confirm":
            if self.timer > 0.5 and (
                self.game.input.is_action_just_pressed("jump")
                or self.game.input.is_action_just_pressed("action")
            ):
                # Create starter and go to overworld
                starter_name = STARTERS[self.selected]
                starter = Pokemon(starter_name, 5)
                party = [starter]

                from scenes.overworld import OverworldScene
                from scenes.battle import BattleScene

                overworld = OverworldScene()
                overworld.party = party
                overworld.pokeballs = 10
                self.game.scenes.register("overworld", overworld)
                battle = BattleScene()
                battle.pokeballs = 10
                self.game.scenes.register("battle", battle)
                self.game.scenes.switch("overworld")

    def draw(self):
        screen = self.game.screen
        W, H = self.game.width, self.game.height
        r = self.game.renderer

        # Dark gradient background
        for y in range(0, H, 4):
            t = y / H
            c = (int(10 + 15 * t), int(10 + 20 * t), int(30 + 20 * t))
            pygame.draw.rect(screen, c, (0, y, W, 4))

        if self.state == "title":
            # Pokeball decoration in background
            ball_y = H // 2 + 20
            ball_r = 80
            pygame.draw.circle(screen, (30, 30, 50), (W // 2, ball_y), ball_r)
            pygame.draw.circle(screen, (200, 40, 40), (W // 2, ball_y), ball_r - 2)
            pygame.draw.rect(
                screen, (240, 240, 240), (W // 2 - ball_r, ball_y - 3, ball_r * 2, 6)
            )
            pygame.draw.circle(
                screen,
                (240, 240, 240),
                (W // 2, ball_y - ball_r + 2),
                ball_r - 2,
                draw_top_left=True,
                draw_top_right=True,
            )
            pygame.draw.circle(screen, (30, 30, 50), (W // 2, ball_y), 18)
            pygame.draw.circle(screen, (240, 240, 240), (W // 2, ball_y), 12)
            pygame.draw.circle(screen, (30, 30, 50), (W // 2, ball_y), 6)

            bob = math.sin(self.timer * 2) * 5

            # Title with shadow
            r.draw_text("DRIFT", W // 2 - 58, 102 + bob, color=(20, 20, 40), size=48)
            r.draw_text("DRIFT", W // 2 - 60, 100 + bob, color=(220, 220, 255), size=48)
            r.draw_text(
                "POKEMON", W // 2 - 83, 157 + bob, color=(180, 140, 20), size=44
            )
            r.draw_text(
                "POKEMON", W // 2 - 85, 155 + bob, color=(255, 220, 80), size=44
            )

            alpha = int(128 + 127 * math.sin(self.timer * 3))
            r.draw_text(
                "Press SPACE or Z",
                W // 2 - 80,
                300,
                color=(alpha, alpha, alpha),
                size=20,
            )

            r.draw_text(
                "Powered by Drift2D", W // 2 - 85, H - 40, color=(60, 60, 80), size=14
            )

        elif self.state == "choose_starter":
            r.draw_text(
                "Choose your starter!", W // 2 - 110, 40, color=(255, 255, 255), size=24
            )

            # Draw three starter options
            for i, name in enumerate(STARTERS):
                species = POKEDEX[name]
                x = 100 + i * 180
                y = 150
                is_selected = i == self.selected

                # Box
                box_color = (80, 80, 120) if is_selected else (40, 40, 60)
                border_color = (255, 220, 80) if is_selected else (60, 60, 80)
                pygame.draw.rect(
                    screen, box_color, (x - 10, y - 10, 150, 200), border_radius=8
                )
                pygame.draw.rect(
                    screen, border_color, (x - 10, y - 10, 150, 200), 2, border_radius=8
                )

                # Pokemon drawn shape
                pcolor = species.color
                bob2 = math.sin(self.timer * 3 + i) * 3 if is_selected else 0
                cx, cy = x + 65, y + 50 + int(bob2)
                sz = 38 if is_selected else 32

                # Shadow
                pygame.draw.ellipse(
                    screen, (0, 0, 0, 60), (cx - sz, cy + sz - 6, sz * 2, 12)
                )

                if name == "charmander":
                    # Body
                    pygame.draw.ellipse(
                        screen,
                        (240, 140, 50),
                        (cx - sz // 2, cy - sz // 2, sz, int(sz * 1.1)),
                    )
                    # Belly
                    pygame.draw.ellipse(
                        screen,
                        (255, 220, 140),
                        (cx - sz // 4, cy - sz // 6, sz // 2, sz // 2),
                    )
                    # Flame tail
                    pygame.draw.polygon(
                        screen,
                        (255, 100, 30),
                        [
                            (cx - sz // 2 - 5, cy),
                            (cx - sz // 2 - 18, cy - 15),
                            (cx - sz // 2 - 8, cy + 5),
                        ],
                    )
                    pygame.draw.polygon(
                        screen,
                        (255, 200, 50),
                        [
                            (cx - sz // 2 - 8, cy - 2),
                            (cx - sz // 2 - 14, cy - 10),
                            (cx - sz // 2 - 5, cy + 2),
                        ],
                    )
                    # Eyes
                    pygame.draw.circle(screen, (255, 255, 255), (cx + 5, cy - 6), 5)
                    pygame.draw.circle(screen, (30, 30, 120), (cx + 7, cy - 6), 3)
                elif name == "squirtle":
                    # Shell
                    pygame.draw.ellipse(
                        screen,
                        (140, 100, 50),
                        (cx - sz // 2 - 3, cy - sz // 3, sz + 6, int(sz * 0.9)),
                    )
                    # Body
                    pygame.draw.ellipse(
                        screen,
                        (100, 160, 230),
                        (cx - sz // 2, cy - sz // 2, sz, int(sz * 1.1)),
                    )
                    # Belly
                    pygame.draw.ellipse(
                        screen,
                        (200, 220, 240),
                        (cx - sz // 4, cy - sz // 6, sz // 2, sz // 2),
                    )
                    # Eyes
                    pygame.draw.circle(screen, (255, 255, 255), (cx + 4, cy - 8), 5)
                    pygame.draw.circle(screen, (120, 30, 30), (cx + 6, cy - 8), 3)
                elif name == "bulbasaur":
                    # Body
                    pygame.draw.ellipse(
                        screen,
                        (100, 180, 120),
                        (cx - sz // 2, cy - sz // 3, sz, int(sz * 0.8)),
                    )
                    # Bulb
                    pygame.draw.ellipse(
                        screen,
                        (40, 120, 50),
                        (cx - sz // 3, cy - sz // 2 - 8, int(sz * 0.7), int(sz * 0.5)),
                    )
                    pygame.draw.ellipse(
                        screen,
                        (60, 150, 70),
                        (cx - sz // 4, cy - sz // 2 - 4, int(sz * 0.5), int(sz * 0.35)),
                    )
                    # Spots
                    pygame.draw.circle(screen, (70, 140, 90), (cx - 8, cy + 2), 4)
                    pygame.draw.circle(screen, (70, 140, 90), (cx + 6, cy + 4), 3)
                    # Eyes
                    pygame.draw.circle(screen, (255, 255, 255), (cx + 6, cy - 4), 5)
                    pygame.draw.circle(screen, (200, 30, 30), (cx + 8, cy - 4), 3)

                # Name
                r.draw_text(
                    species.name, x + 10, y + 100, color=(255, 255, 255), size=18
                )

                # Type badge
                type_color = get_type_color(species.ptype)
                pygame.draw.rect(
                    screen, type_color, (x + 10, y + 125, 60, 18), border_radius=4
                )
                r.draw_text(
                    species.ptype.upper(),
                    x + 15,
                    y + 126,
                    color=(255, 255, 255),
                    size=12,
                )

                # Description
                if is_selected:
                    desc = STARTER_DESCRIPTIONS.get(name, "")
                    r.draw_text(desc, 100, 380, color=(180, 180, 200), size=14)

            # Controls
            r.draw_text(
                "< LEFT/RIGHT to choose, SPACE to confirm >",
                W // 2 - 190,
                H - 40,
                color=(100, 100, 120),
                size=14,
            )

        elif self.state == "confirm":
            name = STARTERS[self.selected]
            species = POKEDEX[name]

            r.draw_text(
                f"You chose {species.name}!",
                W // 2 - 100,
                H // 2 - 40,
                color=(255, 220, 80),
                size=28,
            )
            pygame.draw.circle(screen, species.color, (W // 2, H // 2 + 40), 40)
            pygame.draw.circle(screen, (255, 255, 255), (W // 2 + 10, H // 2 + 32), 7)
            pygame.draw.circle(screen, (30, 30, 30), (W // 2 + 12, H // 2 + 32), 4)

            if self.timer > 0.5:
                alpha = int(min(255, (self.timer - 0.5) * 300))
                r.draw_text(
                    "Press SPACE to begin!",
                    W // 2 - 100,
                    H // 2 + 100,
                    color=(alpha, alpha, alpha),
                    size=18,
                )
