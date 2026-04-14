"""Animation system: updates AnimationPlayer components each frame."""

from __future__ import annotations
from .entity import World, AnimationPlayer, Sprite


def update_animations(world: World, dt: float):
    """Advance frame timers on all entities with AnimationPlayer + Sprite."""
    for entity in world.query(AnimationPlayer, Sprite):
        anim = entity.get(AnimationPlayer)
        sprite = entity.get(Sprite)

        if not anim.current or anim.current not in anim.animations:
            continue

        frames = anim.animations[anim.current]
        if not frames:
            continue

        anim._timer += dt
        frame_duration = 1.0 / anim.speed if anim.speed > 0 else 1.0

        if anim._timer >= frame_duration:
            anim._timer -= frame_duration
            anim.frame = (anim.frame + 1) % len(frames)

        sprite.image = frames[anim.frame]


def play_animation(entity, name: str, reset: bool = False):
    """Switch an entity's current animation."""
    anim = entity.get(AnimationPlayer)
    if not anim:
        return
    if anim.current != name or reset:
        anim.current = name
        anim.frame = 0
        anim._timer = 0.0
