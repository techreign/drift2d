"""Platformer main scene — player runs and jumps on platforms."""

from pathlib import Path
from drift2d import (
    Scene,
    Entity,
    Transform,
    Sprite,
    RigidBody,
    BoxCollider,
    Vec2,
    load_entities,
    Collision,
)


class Main(Scene):
    def __init__(self):
        super().__init__()
        self.on_ground = False
        self.jump_strength = -420.0
        self.move_speed = 250.0

    def enter(self):
        # Load all entities from YAML
        entity_dir = Path(__file__).parent.parent / "entities"
        for entity in load_entities(entity_dir):
            self.game.world.spawn(entity)

        # Add some platforms
        positions = [(200, 450), (500, 380), (350, 300), (650, 250)]
        for i, (x, y) in enumerate(positions):
            plat = Entity(f"platform_{i}")
            plat.tags.add("solid")
            plat.add(Transform(position=Vec2(x, y)))
            plat.add(Sprite(color=(80, 80, 110), width=120, height=16))
            plat.add(RigidBody(kinematic=True))
            plat.add(BoxCollider(width=120, height=16))
            self.game.world.spawn(plat)

        # Camera follows player
        player = self.game.world.find("player")
        if player:
            self.game.camera.follow(player, smoothing=3.0)

    def update(self, dt):
        player = self.game.world.find("player")
        if not player:
            return

        rb = player.get(RigidBody)
        sprite = player.get(Sprite)

        # Horizontal movement
        h = self.game.input.get_axis("move_left", "move_right")
        rb.velocity.x = h * self.move_speed

        # Flip sprite based on direction
        if h < 0:
            sprite.flip_x = True
        elif h > 0:
            sprite.flip_x = False

        # Jump
        if self.game.input.is_action_just_pressed("jump") and self.on_ground:
            rb.velocity.y = self.jump_strength
            self.on_ground = False

        # Reset if fallen off
        transform = player.get(Transform)
        if transform.position.y > 800:
            transform.position = Vec2(400, 400)
            rb.velocity = Vec2()

    def on_collision(self, collision: Collision):
        # Check if player landed on something
        player = self.game.world.find("player")
        if not player:
            return

        a, b = collision.entity_a, collision.entity_b
        if player in (a, b):
            other = b if a == player else a
            if "solid" in other.tags and collision.normal.y != 0:
                if collision.normal.y > 0:  # landed on top
                    self.on_ground = True

    def draw(self):
        self.game.renderer.draw_text(
            "WASD/Arrows to move, Space to jump", 10, 10, size=16
        )
        self.game.renderer.draw_text(
            f"FPS: {self.game.clock.get_fps():.0f}",
            10,
            30,
            size=16,
            color=(100, 100, 100),
        )
