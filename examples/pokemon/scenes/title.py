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
            bob = math.sin(self.timer * 2) * 5
            r.draw_text("DRIFT", W // 2 - 60, 100 + bob, color=(200, 200, 255), size=48)
            r.draw_text(
                "POKEMON", W // 2 - 85, 155 + bob, color=(255, 220, 80), size=44
            )

            alpha = int(128 + 127 * math.sin(self.timer * 3))
            r.draw_text(
                "Press SPACE", W // 2 - 65, 280, color=(alpha, alpha, alpha), size=20
            )

            # Version text
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

                # Pokemon circle
                pcolor = species.color
                radius = 35 if is_selected else 30
                bob2 = math.sin(self.timer * 3 + i) * 3 if is_selected else 0
                pygame.draw.circle(screen, pcolor, (x + 65, y + 50 + int(bob2)), radius)
                # Eye
                pygame.draw.circle(
                    screen, (255, 255, 255), (x + 75, y + 43 + int(bob2)), 6
                )
                pygame.draw.circle(
                    screen, (30, 30, 30), (x + 77, y + 43 + int(bob2)), 3
                )

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
