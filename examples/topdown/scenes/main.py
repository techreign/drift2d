"""Top-down dungeon crawler scene — tilemap + particles + enemies."""

from pathlib import Path
from drift2d import (
    Scene,
    Entity,
    Transform,
    Sprite,
    RigidBody,
    BoxCollider,
    Vec2,
    Tilemap,
    TileDef,
    ParticleEmitter,
    ParticleConfig,
    Collision,
)


class Main(Scene):
    def __init__(self):
        super().__init__()
        self.tilemap = Tilemap(tile_size=32)
        self.move_speed = 160.0
        self.dust_emitter = ParticleEmitter(
            ParticleConfig(
                count=5,
                lifetime=(0.2, 0.5),
                speed=(20.0, 60.0),
                direction=-90,
                spread=120,
                color=(80, 90, 70),
                color_end=(40, 50, 30),
                size=(1.5, 3.0),
                gravity=50.0,
                fade=True,
            )
        )
        self.hit_emitter = ParticleEmitter(
            ParticleConfig(
                count=15,
                lifetime=(0.3, 0.8),
                speed=(80.0, 200.0),
                spread=360,
                color=(255, 100, 100),
                color_end=(100, 0, 0),
                size=(2.0, 4.0),
                fade=True,
            )
        )
        self.score = 0

    def enter(self):
        # Define tile types
        self.tilemap.define("W", TileDef(char="W", color=(50, 45, 40), solid=True))

        # Load level
        level_path = Path(__file__).parent.parent / "levels" / "dungeon.txt"
        self.tilemap.load_from_file(level_path)

        # Find spawn point
        spawns = self.tilemap.find_tiles("P")
        px, py = spawns[0] if spawns else (5, 5)
        spawn_pos = self.tilemap.tile_to_world(px, py)
        spawn_pos += Vec2(16, 16)  # center in tile

        # Create player
        player = Entity("player")
        player.tags.add("player")
        player.add(Transform(position=spawn_pos))
        player.add(Sprite(color=(100, 220, 140), width=24, height=24, layer=10))
        player.add(RigidBody(kinematic=True))
        player.add(BoxCollider(width=24, height=24, tag="player"))
        self.game.world.spawn(player)

        # Create enemies at 'E' tiles
        for i, (ex, ey) in enumerate(self.tilemap.find_tiles("E")):
            epos = self.tilemap.tile_to_world(ex, ey) + Vec2(16, 16)
            enemy = Entity(f"enemy_{i}")
            enemy.tags.add("enemy")
            enemy.add(Transform(position=epos))
            enemy.add(Sprite(color=(220, 80, 80), width=24, height=24, layer=5))
            enemy.add(RigidBody(kinematic=True))
            enemy.add(BoxCollider(width=24, height=24, tag="enemy"))
            self.game.world.spawn(enemy)

        # Camera
        self.game.camera.follow(player, smoothing=8.0)

    def update(self, dt):
        player = self.game.world.find("player")
        if not player:
            return

        transform = player.get(Transform)
        direction = self.game.input.get_vector()

        if direction.length > 0:
            move = direction.normalized * self.move_speed * dt
            new_pos = transform.position + move

            # Tilemap collision check
            from drift2d.utils import Rect

            test_rect = Rect(new_pos.x - 12, new_pos.y - 12, 24, 24)
            hits = self.tilemap.collide_rect(test_rect)

            if not hits:
                transform.position = new_pos
                # Dust particles while moving
                if self.game.frame_count % 8 == 0:
                    self.dust_emitter.emit(
                        transform.position.x, transform.position.y + 12, count=3
                    )

        # Simple enemy patrol (bounce horizontally)
        for enemy in self.game.world.query_tag("enemy"):
            et = enemy.get(Transform)
            rb = enemy.get(RigidBody)
            if not hasattr(rb, "_dir"):
                rb._dir = 1.0
            et.position.x += rb._dir * 40 * dt

            # Bounce off walls
            from drift2d.utils import Rect

            test = Rect(et.position.x - 12, et.position.y - 12, 24, 24)
            if self.tilemap.collide_rect(test):
                et.position.x -= rb._dir * 40 * dt
                rb._dir *= -1

        # Update particles
        self.dust_emitter.update(dt)
        self.hit_emitter.update(dt)

    def on_collision(self, collision: Collision):
        a, b = collision.entity_a, collision.entity_b
        player = self.game.world.find("player")
        if not player:
            return

        if player in (a, b):
            other = b if a == player else a
            if "enemy" in other.tags:
                # Kill enemy
                pos = other.get(Transform).position
                self.hit_emitter.emit(pos.x, pos.y, count=15)
                self.game.world.despawn(other)
                self.score += 100

    def draw(self):
        # Draw tilemap
        self.tilemap.draw(self.game.screen, self.game.camera.position)

        # Draw particles (after tilemap, before UI)
        self.dust_emitter.draw(self.game.screen, self.game.camera.position)
        self.hit_emitter.draw(self.game.screen, self.game.camera.position)

        # UI
        self.game.renderer.draw_text(f"Score: {self.score}", 10, 10, size=20)
        self.game.renderer.draw_text(
            "WASD to move, touch enemies to destroy",
            10,
            35,
            size=14,
            color=(120, 120, 120),
        )
