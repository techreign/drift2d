"""Simple AABB physics: gravity, velocity integration, collision detection."""

from __future__ import annotations
from dataclasses import dataclass
from .utils import Vec2, Rect
from .entity import Entity, Transform, RigidBody, BoxCollider, World


GRAVITY = 980.0  # pixels per second squared


@dataclass
class Collision:
    entity_a: Entity
    entity_b: Entity
    overlap: Vec2
    normal: Vec2


def _get_bounds(entity: Entity) -> Rect | None:
    transform = entity.get(Transform)
    collider = entity.get(BoxCollider)
    if not transform or not collider:
        return None
    return Rect(
        transform.position.x - collider.width / 2 + collider.offset.x,
        transform.position.y - collider.height / 2 + collider.offset.y,
        collider.width,
        collider.height,
    )


def update_physics(
    world: World, dt: float, gravity: float = GRAVITY
) -> list[Collision]:
    """Integrate velocities and resolve collisions. Returns collision list."""

    # 1. Apply gravity + integrate velocity
    for entity in world.query(Transform, RigidBody):
        rb = entity.get(RigidBody)
        transform = entity.get(Transform)

        if rb.kinematic:
            continue

        # Gravity
        rb.velocity.y += gravity * rb.gravity_scale * dt

        # Friction (horizontal only)
        if rb.friction > 0:
            rb.velocity.x *= max(0.0, 1.0 - rb.friction * dt)

        # Acceleration
        rb.velocity += rb.acceleration * dt

        # Integrate
        transform.position += rb.velocity * dt

    # 2. Detect collisions (brute force — fine for <200 entities)
    collisions: list[Collision] = []
    collidables = list(world.query(Transform, BoxCollider))

    for i, a in enumerate(collidables):
        for b in collidables[i + 1 :]:
            bounds_a = _get_bounds(a)
            bounds_b = _get_bounds(b)
            if not bounds_a or not bounds_b:
                continue
            if not bounds_a.overlaps(bounds_b):
                continue

            # Calculate overlap
            ox = min(bounds_a.right - bounds_b.left, bounds_b.right - bounds_a.left)
            oy = min(bounds_a.bottom - bounds_b.top, bounds_b.bottom - bounds_a.top)

            if ox < oy:
                normal = Vec2(-1 if bounds_a.center.x < bounds_b.center.x else 1, 0)
                overlap = Vec2(ox, 0)
            else:
                normal = Vec2(0, -1 if bounds_a.center.y < bounds_b.center.y else 1)
                overlap = Vec2(0, oy)

            collision = Collision(a, b, overlap, normal)
            collisions.append(collision)

            # 3. Resolve solid collisions
            col_a = a.get(BoxCollider)
            col_b = b.get(BoxCollider)
            if col_a.solid and col_b.solid:
                _resolve(a, b, overlap, normal)

    return collisions


def _resolve(a: Entity, b: Entity, overlap: Vec2, normal: Vec2):
    """Push entities apart based on their kinematic status."""
    rb_a = a.get(RigidBody)
    rb_b = b.get(RigidBody)
    t_a = a.get(Transform)
    t_b = b.get(Transform)

    a_kinematic = rb_a.kinematic if rb_a else True
    b_kinematic = rb_b.kinematic if rb_b else True

    push = Vec2(overlap.x * normal.x, overlap.y * normal.y)

    if a_kinematic and not b_kinematic:
        t_b.position -= push
        if rb_b:
            if normal.x != 0:
                rb_b.velocity.x = 0
            if normal.y != 0:
                rb_b.velocity.y = 0
    elif b_kinematic and not a_kinematic:
        t_a.position += push
        if rb_a:
            if normal.x != 0:
                rb_a.velocity.x = 0
            if normal.y != 0:
                rb_a.velocity.y = 0
    elif not a_kinematic and not b_kinematic:
        half_push = push * 0.5
        t_a.position += half_push
        t_b.position -= half_push
        if rb_a:
            if normal.x != 0:
                rb_a.velocity.x = 0
            if normal.y != 0:
                rb_a.velocity.y = 0
        if rb_b:
            if normal.x != 0:
                rb_b.velocity.x = 0
            if normal.y != 0:
                rb_b.velocity.y = 0
