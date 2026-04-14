"""CLI: drift new / drift run."""

from __future__ import annotations
from pathlib import Path
import click
import subprocess
import sys


GAME_TOML_TEMPLATE = """[game]
title = "{name}"

[window]
width = 800
height = 600
fps = 60
bg_color = [20, 20, 30]

[physics]
gravity = 980.0

[input]
# action = ["key1", "key2"]
# jump = ["SPACE"]
"""

MAIN_SCENE_TEMPLATE = '''"""Main game scene."""

from drift2d import Scene, Entity, Transform, Sprite, RigidBody, BoxCollider, Vec2


class Main(Scene):
    def enter(self):
        # Create a player
        player = Entity("player")
        player.add(Transform(position=Vec2(400, 300)))
        player.add(Sprite(color=(100, 200, 255), width=32, height=32))
        player.add(RigidBody(gravity_scale=0.0))
        player.add(BoxCollider(width=32, height=32))
        self.game.world.spawn(player)

    def update(self, dt):
        player = self.game.world.find("player")
        if player:
            rb = player.get(RigidBody)
            direction = self.game.input.get_vector()
            rb.velocity = direction * 200

    def draw(self):
        self.game.renderer.draw_text("{name}", 10, 10, size=20)
'''

RUN_TEMPLATE = '''"""Entry point — run with: drift run  OR  python run.py"""

from drift2d import Game
from scenes.main import Main

game = Game.from_project(".")
game.scenes.register("main", Main())
game.run("main")
'''


@click.group()
def main():
    """Drift — a Claude-first 2D game engine."""
    pass


@main.command()
@click.argument("name")
def new(name: str):
    """Create a new Drift game project."""
    root = Path(name)
    if root.exists():
        click.echo(f"Error: '{name}' already exists.")
        return

    # Create directories
    (root / "scenes").mkdir(parents=True)
    (root / "entities").mkdir(parents=True)
    (root / "assets" / "sprites").mkdir(parents=True)
    (root / "assets" / "sounds").mkdir(parents=True)

    # Write files
    (root / "game.toml").write_text(GAME_TOML_TEMPLATE.format(name=name))
    (root / "scenes" / "__init__.py").write_text("")
    (root / "scenes" / "main.py").write_text(MAIN_SCENE_TEMPLATE.format(name=name))
    (root / "run.py").write_text(RUN_TEMPLATE)
    (root / ".gitignore").write_text("__pycache__/\n*.pyc\n.env\n")

    click.echo(f"Created '{name}/'")
    click.echo(f"  cd {name}")
    click.echo("  drift run")


@main.command()
@click.option("--debug", is_flag=True, help="Show FPS and entity count")
def run(debug: bool):
    """Run the game in the current directory."""
    root = Path(".")
    run_file = root / "run.py"

    if not run_file.exists():
        click.echo("Error: No run.py found. Are you in a Drift project directory?")
        click.echo("Create one with: drift new <name>")
        return

    args = [sys.executable, str(run_file)]
    env = None
    if debug:
        import os

        env = {**os.environ, "DRIFT_DEBUG": "1"}

    subprocess.run(args, cwd=str(root), env=env)


if __name__ == "__main__":
    main()
