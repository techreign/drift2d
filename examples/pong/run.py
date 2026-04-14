"""Run the Pong example."""

import sys
from pathlib import Path

engine_src = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(engine_src))

from drift2d import Game
from scenes.main import Main

game = Game.from_project(".")
game.scenes.register("main", Main())
game.run("main")
