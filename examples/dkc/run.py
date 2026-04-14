"""Jungle Kong — a DKC-style platformer built with Drift2D."""

import sys
from pathlib import Path

engine_src = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(engine_src))

from drift2d import Game
from scenes.menu import MenuScene
from scenes.gameover import GameOverScene
from scenes.victory import VictoryScene

game = Game.from_project(".")

# Enable dev loop — Claude watches the game live
game.enable_dev(
    output_dir=".drift-dev",
    screenshot_interval=3.0,
    watch_dirs=["scenes"],
)

# Register persistent scenes
game.scenes.register("menu", MenuScene())
game.scenes.register("gameover", GameOverScene())
game.scenes.register("victory", VictoryScene())

game.run("menu")
