"""Pong — the simplest possible Drift game. ~80 lines."""

import random
from drift2d import (
    Scene,
    Entity,
    Transform,
    Sprite,
    RigidBody,
    BoxCollider,
    Vec2,
    Collision,
)


class Main(Scene):
    def __init__(self):
        super().__init__()
        self.score_left = 0
        self.score_right = 0
        self.paddle_speed = 300.0

    def enter(self):
        W, H = self.game.width, self.game.height

        # Left paddle (player)
        left = Entity("paddle_left")
        left.add(Transform(position=Vec2(30, H / 2)))
        left.add(Sprite(color=(100, 200, 255), width=12, height=80))
        left.add(RigidBody(kinematic=True))
        left.add(BoxCollider(width=12, height=80, tag="paddle"))
        self.game.world.spawn(left)

        # Right paddle (AI)
        right = Entity("paddle_right")
        right.add(Transform(position=Vec2(W - 30, H / 2)))
        right.add(Sprite(color=(255, 100, 100), width=12, height=80))
        right.add(RigidBody(kinematic=True))
        right.add(BoxCollider(width=12, height=80, tag="paddle"))
        self.game.world.spawn(right)

        # Ball
        self._spawn_ball()

        # Walls (top + bottom)
        for name, y in [("wall_top", -5), ("wall_bottom", H + 5)]:
            wall = Entity(name)
            wall.add(Transform(position=Vec2(W / 2, y)))
            wall.add(BoxCollider(width=W, height=10, tag="wall"))
            wall.add(RigidBody(kinematic=True))
            self.game.world.spawn(wall)

    def _spawn_ball(self):
        old = self.game.world.find("ball")
        if old:
            self.game.world.despawn(old)

        W, H = self.game.width, self.game.height
        ball = Entity("ball")
        ball.add(Transform(position=Vec2(W / 2, H / 2)))
        ball.add(Sprite(color=(255, 255, 255), width=10, height=10))
        vx = random.choice([-1, 1]) * 250
        vy = random.uniform(-100, 100)
        ball.add(RigidBody(velocity=Vec2(vx, vy), kinematic=True))
        ball.add(BoxCollider(width=10, height=10, tag="ball"))
        self.game.world.spawn(ball)

    def update(self, dt):
        W, H = self.game.width, self.game.height

        # Player paddle
        left = self.game.world.find("paddle_left")
        if left:
            v = self.game.input.get_axis("move_up", "move_down")
            t = left.get(Transform)
            t.position.y += v * self.paddle_speed * dt
            t.position.y = max(40, min(H - 40, t.position.y))

        # AI paddle — follows ball
        right = self.game.world.find("paddle_right")
        ball = self.game.world.find("ball")
        if right and ball:
            bt = ball.get(Transform)
            rt = right.get(Transform)
            diff = bt.position.y - rt.position.y
            rt.position.y += max(-1, min(1, diff)) * self.paddle_speed * 0.7 * dt
            rt.position.y = max(40, min(H - 40, rt.position.y))

        # Move ball manually (kinematic)
        if ball:
            bt = ball.get(Transform)
            rb = ball.get(RigidBody)
            bt.position += rb.velocity * dt

            # Top/bottom bounce
            if bt.position.y < 5 or bt.position.y > H - 5:
                rb.velocity.y *= -1
                bt.position.y = max(5, min(H - 5, bt.position.y))

            # Score detection
            if bt.position.x < 0:
                self.score_right += 1
                self._spawn_ball()
            elif bt.position.x > W:
                self.score_left += 1
                self._spawn_ball()

    def on_collision(self, collision: Collision):
        a, b = collision.entity_a, collision.entity_b
        ball = self.game.world.find("ball")
        if not ball:
            return

        if ball in (a, b):
            other = b if a == ball else a
            col = other.get(BoxCollider)
            if col and col.tag == "paddle":
                rb = ball.get(RigidBody)
                rb.velocity.x *= -1.1  # speed up slightly
                rb.velocity.y += random.uniform(-30, 30)

    def draw(self):
        W = self.game.width
        r = self.game.renderer

        # Center line
        for y in range(0, self.game.height, 20):
            r.draw_screen_rect(W // 2 - 1, y, 2, 10, color=(40, 40, 60))

        # Score
        r.draw_text(
            str(self.score_left), W // 2 - 50, 20, size=36, color=(100, 200, 255)
        )
        r.draw_text(
            str(self.score_right), W // 2 + 30, 20, size=36, color=(255, 100, 100)
        )
        r.draw_text(
            "W/S or Up/Down to move",
            10,
            self.game.height - 25,
            size=14,
            color=(60, 60, 60),
        )
