"""
Drift2D — A Claude-first 2D game engine.

    from drift2d import Game, Scene, Entity, Vec2

    class MyScene(Scene):
        def enter(self):
            player = Entity("player")
            player.add(Transform(position=Vec2(100, 100)))
            player.add(Sprite(color=(0, 200, 255), width=32, height=32))
            self.game.world.spawn(player)

    game = Game(title="My Game", width=800, height=600)
    game.scenes.register("main", MyScene())
    game.run("main")
"""

from .utils import Vec2, Rect, Timer
from .entity import (
    Entity,
    World,
    Transform,
    Sprite,
    RigidBody,
    BoxCollider,
    AnimationPlayer,
)
from .scene import Scene, SceneManager
from .engine import Game
from .input import Input
from .renderer import Camera, Renderer
from .audio import Audio
from .physics import Collision, update_physics
from .loader import load_entity, load_entities, entity_from_yaml, register_component
from .tilemap import Tilemap, TileDef
from .particles import ParticleEmitter, ParticleConfig
from .animation import update_animations, play_animation
from .devloop import DevLoop, DevState

__version__ = "0.1.0"

__all__ = [
    # Core
    "Game",
    "Scene",
    "SceneManager",
    # ECS
    "Entity",
    "World",
    "Transform",
    "Sprite",
    "RigidBody",
    "BoxCollider",
    "AnimationPlayer",
    # Systems
    "Input",
    "Camera",
    "Renderer",
    "Audio",
    "Collision",
    "update_physics",
    "update_animations",
    "play_animation",
    # Tilemap
    "Tilemap",
    "TileDef",
    # Particles
    "ParticleEmitter",
    "ParticleConfig",
    # Loader
    "load_entity",
    "load_entities",
    "entity_from_yaml",
    "register_component",
    # Dev Loop
    "DevLoop",
    "DevState",
    # Utils
    "Vec2",
    "Rect",
    "Timer",
]
