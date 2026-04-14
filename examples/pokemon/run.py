"""Drift Pokemon — a Pokemon-style RPG built with Drift2D."""

import sys
from pathlib import Path

engine_src = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(engine_src))
sys.path.insert(0, str(Path(__file__).parent))

from drift2d import Game
from scenes.title import TitleScene
from autoplay_rpg import RPGAutoPlayer

game = Game.from_project(".")

# Enable dev loop — Claude watches the game live
game.enable_dev(
    output_dir=".drift-dev",
    screenshot_interval=2.0,
    watch_dirs=["scenes"],
)

# RPG autoplay bot
bot = RPGAutoPlayer(game)
# Hook bot into the engine loop (before events)
_orig_run = game.run


def _patched_run(start_scene=None):
    import pygame

    if start_scene:
        game.scenes.switch(start_scene)
    game.running = True
    while game.running:
        game.dt = game.clock.tick(game.fps) / 1000.0
        game.dt = min(game.dt, 0.05)
        game.time += game.dt
        game.frame_count += 1

        # Bot injects input
        bot.update(game.dt)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                game.running = False
                break
        game.input.update(events)
        game.world.flush()

        scene = game.scenes.current
        if scene:
            scene.update(game.dt)

        from drift2d.physics import update_physics
        from drift2d.animation import update_animations

        collisions = update_physics(game.world, game.dt, game.gravity)
        if scene:
            for col in collisions:
                scene.on_collision(col)
        update_animations(game.world, game.dt)
        game.camera.update(game.dt)

        game.screen.fill(game.bg_color)
        if scene:
            scene.draw()
        if not getattr(scene, "custom_draw", False):
            game.renderer.draw_entities(game.world.query())
        if game.debug:
            game._draw_debug()
        if game.dev:
            game.dev.update(game.dt)

        pygame.display.flip()
    pygame.quit()


game.scenes.register("title", TitleScene())
_patched_run("title")
