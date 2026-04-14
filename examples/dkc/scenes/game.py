"""
Jungle Kong — DKC-style platformer with multiple levels.

Tile legend:
  G = ground/platform (solid, jungle green)
  P = player spawn
  B = banana collectible
  b = barrel launcher (shoots player upward)
  E = enemy (patrols platform)
  D = level door/exit
  . = air
"""

import math
import random
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
)
from drift2d.utils import Rect


# ── Colors ──────────────────────────────────────────────

C_GROUND = (45, 90, 35)
C_GROUND_TOP = (60, 120, 45)
C_PLAYER = (180, 120, 60)
C_PLAYER_BELLY = (220, 180, 100)
C_BANANA = (255, 220, 50)
C_BARREL = (140, 80, 30)
C_BARREL_RIM = (100, 55, 20)
C_ENEMY = (180, 50, 50)
C_ENEMY_EYE = (255, 255, 200)
C_DOOR = (220, 180, 50)
C_VINE = (30, 80, 25)
C_SKY_TOP = (15, 40, 25)
C_SKY_BOT = (8, 20, 12)
C_LEAF = (40, 100, 30)
C_CLOUD = (20, 50, 30)


class GameScene(Scene):
    def __init__(self, level_num: int = 1):
        super().__init__()
        self.custom_draw = True  # we handle all rendering in draw()
        self.level_num = level_num
        self.tilemap = Tilemap(tile_size=32)
        self.lives = 3
        self.bananas = 0
        self.total_bananas = 0
        self.on_ground = False
        self.jump_held = False
        self.jump_timer = 0.0
        self.coyote_time = 0.0
        self.was_on_ground = False
        self.facing_right = True
        self.barrel_cooldown = 0.0
        self.total_deaths = 0
        self.total_kills = 0
        self.squish_effects: list[tuple[float, float, float]] = []  # (x, y, timer)
        self.level_complete = False
        self.level_transition_timer = 0.0
        self.death_timer = 0.0
        self.dying = False
        self.shake_timer = 0.0
        self.shake_intensity = 0.0
        self.scroll_x = 0.0

        # Score system
        self.score = 0
        self.combo = 0  # consecutive aerial kills
        self.combo_timer = 0.0  # resets when player touches ground
        self.banana_flash_timer = 0.0  # > 0 means flash the banana count

        # Particles
        self.dust = ParticleEmitter(
            ParticleConfig(
                count=4,
                lifetime=(0.15, 0.35),
                speed=(15, 50),
                direction=-90,
                spread=120,
                color=(100, 80, 50),
                color_end=(60, 50, 30),
                size=(1.5, 3.0),
                gravity=80,
                fade=True,
            )
        )
        self.banana_pop = ParticleEmitter(
            ParticleConfig(
                count=8,
                lifetime=(0.3, 0.6),
                speed=(60, 140),
                spread=360,
                color=C_BANANA,
                color_end=(255, 255, 200),
                size=(2, 4),
                gravity=-20,
                fade=True,
            )
        )
        self.stomp_burst = ParticleEmitter(
            ParticleConfig(
                count=12,
                lifetime=(0.2, 0.5),
                speed=(80, 180),
                spread=360,
                color=(255, 120, 80),
                color_end=(100, 30, 10),
                size=(2, 5),
                gravity=100,
                fade=True,
            )
        )
        self.door_sparkle = ParticleEmitter(
            ParticleConfig(
                count=3,
                lifetime=(0.5, 1.0),
                speed=(20, 60),
                direction=-90,
                spread=60,
                color=C_DOOR,
                color_end=(255, 255, 200),
                size=(1, 3),
                gravity=-30,
                fade=True,
            )
        )

        # Background decoration positions (generated per level)
        self.bg_trees = []
        self.bg_vines = []
        self.bg_clouds = []

    def enter(self):
        self.game.world.clear()

        # Setup tilemap
        self.tilemap = Tilemap(tile_size=32)
        self.tilemap.define("G", TileDef(char="G", color=C_GROUND, solid=True))

        # Load level
        level_path = (
            Path(__file__).parent.parent / "levels" / f"level{self.level_num}.txt"
        )
        if not level_path.exists():
            # Won the game!
            self.game.scenes.switch("victory")
            return
        self.tilemap.load_from_file(level_path)

        # Generate background decorations
        self._generate_background()

        # Find spawn
        spawns = self.tilemap.find_tiles("P")
        px, py = spawns[0] if spawns else (2, 5)
        spawn_pos = self.tilemap.tile_to_world(px, py) + Vec2(16, 16)

        # Player
        player = Entity("player")
        player.tags.add("player")
        player.add(Transform(position=spawn_pos))
        player.add(Sprite(color=C_PLAYER, width=24, height=30, layer=20))
        player.add(RigidBody(gravity_scale=0.0, friction=6.0, kinematic=True))
        player.add(BoxCollider(width=20, height=28, tag="player"))
        self.game.world.spawn(player)
        self.game.camera.follow(player, smoothing=4.0)

        # Spawn bananas
        self.total_bananas = 0
        for i, (bx, by) in enumerate(self.tilemap.find_tiles("B")):
            bpos = self.tilemap.tile_to_world(bx, by) + Vec2(16, 16)
            banana = Entity(f"banana_{i}")
            banana.tags.add("banana")
            banana.add(Transform(position=bpos))
            banana.add(Sprite(color=C_BANANA, width=14, height=14, layer=5))
            banana.add(BoxCollider(width=14, height=14, tag="banana", solid=False))
            self.game.world.spawn(banana)
            self.total_bananas += 1

        # Spawn enemies
        for i, (ex, ey) in enumerate(self.tilemap.find_tiles("E")):
            epos = self.tilemap.tile_to_world(ex, ey) + Vec2(16, 16)
            enemy = Entity(f"enemy_{i}")
            enemy.tags.add("enemy")
            enemy.add(Transform(position=epos))
            enemy.add(Sprite(color=C_ENEMY, width=26, height=22, layer=10))
            enemy.add(RigidBody(kinematic=True))
            enemy.add(BoxCollider(width=24, height=20, tag="enemy", solid=False))
            # Store patrol data
            enemy._patrol_dir = random.choice([-1, 1])
            enemy._patrol_speed = random.uniform(60, 110)  # faster enemies
            enemy._start_x = epos.x
            self.game.world.spawn(enemy)

        # Spawn barrels
        for i, (bx, by) in enumerate(self.tilemap.find_tiles("b")):
            bpos = self.tilemap.tile_to_world(bx, by) + Vec2(16, 16)
            barrel = Entity(f"barrel_{i}")
            barrel.tags.add("barrel")
            barrel.add(Transform(position=bpos))
            barrel.add(Sprite(color=C_BARREL, width=28, height=28, layer=8))
            barrel.add(BoxCollider(width=28, height=28, tag="barrel", solid=False))
            self.game.world.spawn(barrel)

        # Spawn door/exit
        for dx, dy in self.tilemap.find_tiles("D"):
            dpos = self.tilemap.tile_to_world(dx, dy) + Vec2(16, 16)
            door = Entity("door")
            door.tags.add("door")
            door.add(Transform(position=dpos))
            door.add(Sprite(color=C_DOOR, width=24, height=36, layer=3))
            door.add(BoxCollider(width=24, height=36, tag="door", solid=False))
            self.game.world.spawn(door)

        self.on_ground = False
        self.dying = False
        self.level_complete = False
        self.combo = 0
        self.combo_timer = 0.0
        self.banana_flash_timer = 0.0
        # Don't reset bananas or score — they carry over between levels

    def _generate_background(self):
        """Create random background decoration positions."""
        random.seed(self.level_num * 42)
        map_w = self.tilemap.width * self.tilemap.tile_size

        self.bg_trees = [
            (
                random.randint(0, map_w),
                random.randint(100, 500),
                random.uniform(0.6, 1.2),
            )
            for _ in range(15)
        ]
        self.bg_vines = [
            (random.randint(0, map_w), random.randint(0, 100), random.randint(60, 180))
            for _ in range(20)
        ]
        self.bg_clouds = [
            (
                random.randint(0, map_w + 400),
                random.randint(20, 150),
                random.randint(60, 120),
            )
            for _ in range(8)
        ]

    def update(self, dt):
        if self.level_complete:
            self.level_transition_timer -= dt
            if self.level_transition_timer <= 0:
                # Next level
                next_scene = GameScene(self.level_num + 1)
                next_scene.lives = self.lives
                next_scene.bananas = self.bananas
                next_scene.score = self.score
                self.game.scenes.register(f"level_{self.level_num + 1}", next_scene)
                self.game.scenes.switch(f"level_{self.level_num + 1}")
            return

        if self.dying:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.lives -= 1
                if self.lives <= 0:
                    self.game.scenes.switch("gameover")
                else:
                    self.enter()  # respawn
            return

        self.barrel_cooldown = max(0, self.barrel_cooldown - dt)
        self.shake_timer = max(0, self.shake_timer - dt)
        self.banana_flash_timer = max(0.0, self.banana_flash_timer - dt)
        # Combo decays when player lands (handled below) or after 3s in air
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0

        player = self.game.world.find("player")
        if not player:
            return

        transform = player.get(Transform)
        rb = player.get(RigidBody)
        sprite = player.get(Sprite)

        # ── Horizontal movement (DKC-style momentum) ──
        h = self.game.input.get_axis("move_left", "move_right")
        accel = 800.0 if self.on_ground else 500.0
        max_speed = 220.0

        if h != 0:
            rb.velocity.x += h * accel * dt
            rb.velocity.x = max(-max_speed, min(max_speed, rb.velocity.x))
            self.facing_right = h > 0
            sprite.flip_x = h < 0
        elif self.on_ground:
            # Decelerate on ground
            rb.velocity.x *= max(0, 1.0 - 10.0 * dt)

        # ── Coyote time ──
        if self.on_ground:
            self.coyote_time = 0.1
        else:
            self.coyote_time -= dt

        # ── Jump (variable height) ──
        if self.game.input.is_action_just_pressed("jump") and self.coyote_time > 0:
            rb.velocity.y = -430.0
            self.jump_held = True
            self.jump_timer = 0.25
            self.on_ground = False
            self.coyote_time = 0
            # Jump dust
            self.dust.emit(transform.position.x, transform.position.y + 14, count=6)

        if self.jump_held and self.game.input.is_action_pressed("jump"):
            self.jump_timer -= dt
            if self.jump_timer > 0:
                rb.velocity.y -= 600 * dt  # extend jump
        else:
            self.jump_held = False

        # ── Tilemap collision (manual, since physics is for entity-entity) ──
        # We handle tilemap collision ourselves for precision
        self.was_on_ground = self.on_ground
        self.on_ground = False

        # Apply gravity manually
        rb.velocity.y += self.game.gravity * dt
        rb.velocity.y = min(rb.velocity.y, 600)  # terminal velocity

        # Move X, then check
        transform.position.x += rb.velocity.x * dt
        # Clamp to left boundary
        if transform.position.x < 10:
            transform.position.x = 10
            rb.velocity.x = 0
        player_rect = self._player_rect(transform)
        for tile_rect in self.tilemap.collide_rect(player_rect):
            if rb.velocity.x > 0:
                transform.position.x = tile_rect.left - 10
            elif rb.velocity.x < 0:
                transform.position.x = tile_rect.right + 10
            rb.velocity.x = 0

        # Move Y, then check
        transform.position.y += rb.velocity.y * dt
        player_rect = self._player_rect(transform)
        for tile_rect in self.tilemap.collide_rect(player_rect):
            if rb.velocity.y > 0:
                transform.position.y = tile_rect.top - 14
                rb.velocity.y = 0
                self.on_ground = True
            elif rb.velocity.y < 0:
                transform.position.y = tile_rect.bottom + 14
                rb.velocity.y = 0

        # Landing dust; also break aerial combo
        if self.on_ground and not self.was_on_ground:
            self.dust.emit(transform.position.x, transform.position.y + 14, count=5)
            self.combo = 0
            self.combo_timer = 0.0

        # Running dust
        if (
            self.on_ground
            and abs(rb.velocity.x) > 100
            and self.game.frame_count % 10 == 0
        ):
            self.dust.emit(transform.position.x, transform.position.y + 14, count=2)

        # ── Check entity overlaps ──
        prect = self._player_rect(transform)

        for banana in list(self.game.world.query_tag("banana")):
            bt = banana.get(Transform)
            brect = Rect(bt.position.x - 7, bt.position.y - 7, 14, 14)
            if prect.overlaps(brect):
                self.bananas += 1
                self.score += 10
                self.banana_flash_timer = 0.4
                self.banana_pop.emit(bt.position.x, bt.position.y)
                self.game.world.despawn(banana)
                if self.game.dev:
                    self.game.dev.log_collectible()
                # Extra life every 50 bananas
                if self.bananas % 50 == 0:
                    self.lives += 1

        for enemy in list(self.game.world.query_tag("enemy")):
            et = enemy.get(Transform)
            erect = Rect(et.position.x - 12, et.position.y - 10, 24, 20)
            if prect.overlaps(erect):
                # Stomp if coming from above
                if rb.velocity.y > 0 and transform.position.y < et.position.y - 5:
                    self.stomp_burst.emit(et.position.x, et.position.y)
                    self.squish_effects.append((et.position.x, et.position.y, 0.3))
                    self.game.world.despawn(enemy)
                    rb.velocity.y = -380  # bigger bounce off enemy
                    self.total_kills += 1
                    if self.game.dev:
                        self.game.dev.log_enemy_kill()
                    self.shake_timer = 0.15
                    self.shake_intensity = 4.0
                else:
                    self._die(transform, cause="enemy_contact")

        for barrel in self.game.world.query_tag("barrel"):
            bt = barrel.get(Transform)
            brect = Rect(bt.position.x - 14, bt.position.y - 14, 28, 28)
            if prect.overlaps(brect) and self.barrel_cooldown <= 0:
                # Barrel launch!
                rb.velocity.y = -600
                rb.velocity.x = self.facing_right and 150 or -150
                self.barrel_cooldown = 0.5
                self.shake_timer = 0.2
                self.shake_intensity = 5.0
                self.dust.emit(bt.position.x, bt.position.y, count=10)

        door = self.game.world.find("door")
        if door:
            dt2 = door.get(Transform)
            drect = Rect(dt2.position.x - 12, dt2.position.y - 18, 24, 36)
            if prect.overlaps(drect) and self.on_ground:
                self.level_complete = True
                self.level_transition_timer = 1.5

            # Door sparkle
            if self.game.frame_count % 15 == 0:
                self.door_sparkle.emit(
                    dt2.position.x + random.uniform(-10, 10),
                    dt2.position.y - 18,
                    count=1,
                )

        # ── Enemy patrol ──
        for enemy in self.game.world.query_tag("enemy"):
            et = enemy.get(Transform)
            et.position.x += enemy._patrol_dir * enemy._patrol_speed * dt

            # Check wall collision and reverse
            erect = Rect(et.position.x - 12, et.position.y - 10, 24, 20)
            wall_hits = self.tilemap.collide_rect(erect)
            if wall_hits:
                et.position.x -= enemy._patrol_dir * enemy._patrol_speed * dt
                enemy._patrol_dir *= -1

            # Check if about to walk off edge
            check_x = et.position.x + enemy._patrol_dir * 16
            below = Rect(check_x - 4, et.position.y + 12, 8, 8)
            if not self.tilemap.collide_rect(below):
                enemy._patrol_dir *= -1

        # ── Fall death ──
        if transform.position.y > self.tilemap.height * 32 + 100:
            self._die(transform, cause="fell_off_map")

        # ── Update particles + effects ──
        self.dust.update(dt)
        self.banana_pop.update(dt)
        self.stomp_burst.update(dt)
        self.door_sparkle.update(dt)
        self.squish_effects = [
            (x, y, t - dt) for x, y, t in self.squish_effects if t - dt > 0
        ]

    def _player_rect(self, transform: Transform) -> Rect:
        return Rect(transform.position.x - 10, transform.position.y - 14, 20, 28)

    def _die(self, transform, cause: str = "unknown"):
        self.dying = True
        self.death_timer = 1.0
        self.total_deaths += 1
        self.stomp_burst.emit(transform.position.x, transform.position.y, count=20)
        self.shake_timer = 0.3
        self.shake_intensity = 8.0
        # Log to dev loop
        if self.game.dev:
            self.game.dev.log_death(transform.position.x, transform.position.y, cause)

    def draw(self):
        screen = self.game.screen
        cam = self.game.camera.position

        # Camera shake offset
        shake_x, shake_y = 0, 0
        if self.shake_timer > 0:
            shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)

        # ── Parallax background ──
        self._draw_background(screen, cam, shake_x, shake_y)

        # ── Tilemap ──
        offset = Vec2(cam.x + shake_x, cam.y + shake_y)
        self.tilemap.draw(screen, offset)

        # ── Draw ground top highlights ──
        self._draw_ground_details(screen, cam, shake_x, shake_y)

        # ── Draw entities manually for custom rendering ──

        for entity in self.game.world.query(Transform, Sprite):
            t = entity.get(Transform)
            s = entity.get(Sprite)
            if not s.visible:
                continue

            sx = int(t.position.x - cam.x - shake_x)
            sy = int(t.position.y - cam.y - shake_y)

            if "player" in entity.tags and not self.dying:
                self._draw_player(screen, sx, sy, entity)
            elif "banana" in entity.tags:
                self._draw_banana(screen, sx, sy)
            elif "barrel" in entity.tags:
                self._draw_barrel(screen, sx, sy)
            elif "enemy" in entity.tags:
                self._draw_enemy(screen, sx, sy, entity)
            elif "door" in entity.tags:
                self._draw_door(screen, sx, sy)

        # ── Squish effects (dead enemies) ──
        import pygame

        for sx_e, sy_e, timer in self.squish_effects:
            ex = int(sx_e - cam.x - shake_x)
            ey = int(sy_e - cam.y - shake_y)
            squish = timer / 0.3  # 1.0 → 0.0
            w = int(26 * (2.0 - squish))
            h = int(22 * squish * 0.5)
            alpha = int(255 * squish)
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill((*C_ENEMY, alpha))
            screen.blit(surf, (ex - w // 2, ey - h // 2 + 8))

        # ── Particles ──
        poff = Vec2(cam.x + shake_x, cam.y + shake_y)
        self.dust.draw(screen, poff)
        self.banana_pop.draw(screen, poff)
        self.stomp_burst.draw(screen, poff)
        self.door_sparkle.draw(screen, poff)

        # ── HUD ──
        self._draw_hud(screen)

        # ── Level transition overlay ──
        if self.level_complete:
            self._draw_transition(screen)

        if self.dying:
            self._draw_death(screen)

    def _draw_background(self, screen, cam, sx, sy):
        import pygame

        W, H = self.game.width, self.game.height

        # Sky gradient (drawn as strips)
        for y in range(0, H, 4):
            t = y / H
            r = int(C_SKY_TOP[0] + (C_SKY_BOT[0] - C_SKY_TOP[0]) * t)
            g = int(C_SKY_TOP[1] + (C_SKY_BOT[1] - C_SKY_TOP[1]) * t)
            b = int(C_SKY_TOP[2] + (C_SKY_BOT[2] - C_SKY_TOP[2]) * t)
            pygame.draw.rect(screen, (r, g, b), (0, y, W, 4))

        # Parallax clouds (far)
        for cx, cy, cw in self.bg_clouds:
            dx = int(cx - cam.x * 0.1 - sx) % (W + 200) - 100
            pygame.draw.ellipse(screen, C_CLOUD, (dx, cy, cw, cw // 3))
            pygame.draw.ellipse(
                screen, C_CLOUD, (dx + cw // 4, cy - 10, cw // 2, cw // 4)
            )

        # Parallax trees (mid)
        for tx, ty, scale in self.bg_trees:
            dx = int(tx - cam.x * 0.3 - sx) % (W + 300) - 150
            trunk_h = int(80 * scale)
            crown_r = int(30 * scale)
            # Trunk
            pygame.draw.rect(screen, (35, 55, 25), (dx - 4, ty, 8, trunk_h))
            # Crown
            pygame.draw.circle(screen, (25, 60, 20), (dx, ty), crown_r)
            pygame.draw.circle(
                screen, (30, 70, 22), (dx - 15, ty + 10), int(crown_r * 0.7)
            )
            pygame.draw.circle(
                screen, (20, 55, 18), (dx + 12, ty + 5), int(crown_r * 0.8)
            )

        # Parallax vines (near)
        for vx, vy, vlen in self.bg_vines:
            dx = int(vx - cam.x * 0.5 - sx) % (W + 100) - 50
            sway = math.sin(self.game.time * 1.5 + vx * 0.01) * 8
            pygame.draw.line(screen, C_VINE, (dx, vy), (int(dx + sway), vy + vlen), 2)
            # Leaf at end
            pygame.draw.circle(screen, C_LEAF, (int(dx + sway), vy + vlen), 3)

    def _draw_ground_details(self, screen, cam, sx, sy):
        """Draw grass/highlights on top of ground tiles."""
        import pygame

        ts = self.tilemap.tile_size
        start_col = max(0, int(cam.x // ts))
        end_col = min(self.tilemap.width, int((cam.x + self.game.width) // ts) + 2)

        for row in range(self.tilemap.height):
            for col in range(start_col, end_col):
                if self.tilemap.get_tile(col, row) != "G":
                    continue
                # Only draw highlight if tile above is not ground
                above = self.tilemap.get_tile(col, row - 1)
                if above == "G":
                    continue

                x = int(col * ts - cam.x - sx)
                y = int(row * ts - cam.y - sy)
                # Grass highlight strip
                pygame.draw.rect(screen, C_GROUND_TOP, (x, y, ts, 4))
                # Little grass tufts
                for gx in range(0, ts, 8):
                    gh = random.Random(col * 100 + row * 10 + gx).randint(2, 6)
                    pygame.draw.line(
                        screen, C_LEAF, (x + gx, y), (x + gx + 2, y - gh), 1
                    )

    def _draw_player(self, screen, sx, sy, entity):
        import pygame

        s = entity.get(Sprite)
        # Body
        body_rect = pygame.Rect(sx - 12, sy - 15, 24, 30)
        pygame.draw.rect(screen, C_PLAYER, body_rect, border_radius=6)
        # Belly
        belly_rect = pygame.Rect(sx - 7, sy - 2, 14, 14)
        pygame.draw.rect(screen, C_PLAYER_BELLY, belly_rect, border_radius=4)
        # Eyes
        eye_offset = 4 if self.facing_right else -4
        pygame.draw.circle(screen, (255, 255, 255), (sx + eye_offset, sy - 8), 4)
        pygame.draw.circle(
            screen,
            (30, 20, 10),
            (sx + eye_offset + (1 if self.facing_right else -1), sy - 8),
            2,
        )
        # Mouth/nose
        pygame.draw.circle(screen, (140, 90, 50), (sx + eye_offset - 1, sy - 3), 2)

    def _draw_banana(self, screen, sx, sy):
        import pygame

        # Banana shape (curved rect)
        bob = math.sin(self.game.time * 4 + sx * 0.1) * 3
        pygame.draw.ellipse(screen, C_BANANA, (sx - 7, sy - 5 + bob, 14, 10))
        pygame.draw.ellipse(screen, (255, 240, 120), (sx - 4, sy - 3 + bob, 8, 6))
        # Stem
        pygame.draw.line(
            screen, (140, 120, 30), (sx, sy - 5 + bob), (sx + 2, sy - 8 + bob), 2
        )

    def _draw_barrel(self, screen, sx, sy):
        import pygame

        # Barrel body
        pygame.draw.rect(screen, C_BARREL, (sx - 14, sy - 14, 28, 28), border_radius=4)
        # Rims
        pygame.draw.rect(screen, C_BARREL_RIM, (sx - 14, sy - 14, 28, 4))
        pygame.draw.rect(screen, C_BARREL_RIM, (sx - 14, sy + 10, 28, 4))
        # Arrow indicator
        pygame.draw.polygon(
            screen, (255, 255, 200), [(sx, sy - 8), (sx - 5, sy), (sx + 5, sy)]
        )

    def _draw_enemy(self, screen, sx, sy, entity):
        import pygame

        # Body (rounded)
        pygame.draw.ellipse(screen, C_ENEMY, (sx - 13, sy - 11, 26, 22))
        # Eyes
        pygame.draw.circle(screen, C_ENEMY_EYE, (sx - 5, sy - 5), 4)
        pygame.draw.circle(screen, C_ENEMY_EYE, (sx + 5, sy - 5), 4)
        pygame.draw.circle(screen, (40, 10, 10), (sx - 4, sy - 5), 2)
        pygame.draw.circle(screen, (40, 10, 10), (sx + 6, sy - 5), 2)
        # Angry brows
        d = getattr(entity, "_patrol_dir", 1)
        pygame.draw.line(screen, (100, 20, 20), (sx - 8, sy - 10), (sx - 2, sy - 8), 2)
        pygame.draw.line(screen, (100, 20, 20), (sx + 8, sy - 10), (sx + 2, sy - 8), 2)

    def _draw_door(self, screen, sx, sy):
        import pygame

        # Door frame
        pygame.draw.rect(
            screen, (100, 80, 30), (sx - 14, sy - 20, 28, 40), border_radius=3
        )
        pygame.draw.rect(screen, C_DOOR, (sx - 11, sy - 17, 22, 34), border_radius=2)
        # Arch
        pygame.draw.arc(screen, (255, 220, 100), (sx - 11, sy - 25, 22, 16), 0, 3.14, 2)
        # Star
        glow = int(128 + 127 * math.sin(self.game.time * 3))
        pygame.draw.circle(screen, (255, 255, glow), (sx, sy - 5), 4)

    def _draw_hud(self, screen):
        import pygame

        r = self.game.renderer

        # Semi-transparent HUD bar
        hud_surf = pygame.Surface((self.game.width, 40), pygame.SRCALPHA)
        hud_surf.fill((0, 0, 0, 120))
        screen.blit(hud_surf, (0, 0))

        # Level
        r.draw_text(f"LEVEL {self.level_num}", 15, 10, color=(200, 200, 200), size=20)

        # Lives
        for i in range(self.lives):
            pygame.draw.circle(screen, C_PLAYER, (200 + i * 22, 20), 8)
            pygame.draw.circle(screen, C_PLAYER_BELLY, (200 + i * 22, 22), 4)

        # Bananas
        pygame.draw.ellipse(screen, C_BANANA, (310, 12, 16, 12))
        r.draw_text(f"x{self.bananas}", 330, 10, color=C_BANANA, size=18)

        # Kills
        pygame.draw.ellipse(screen, C_ENEMY, (400, 11, 16, 14))
        r.draw_text(f"x{self.total_kills}", 420, 10, color=(255, 150, 150), size=18)

        # Progress
        if self.total_bananas > 0:
            pct = min(1.0, self.bananas / max(1, self.total_bananas))
            bar_w = 120
            pygame.draw.rect(
                screen,
                (40, 40, 40),
                (self.game.width - bar_w - 20, 14, bar_w, 12),
                border_radius=3,
            )
            pygame.draw.rect(
                screen,
                C_BANANA,
                (self.game.width - bar_w - 20, 14, int(bar_w * pct), 12),
                border_radius=3,
            )

    def _draw_transition(self, screen):
        import pygame

        alpha = min(255, int((1.5 - self.level_transition_timer) / 1.5 * 255))
        overlay = pygame.Surface((self.game.width, self.game.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))

        if alpha > 100:
            self.game.renderer.draw_text(
                f"LEVEL {self.level_num} COMPLETE!",
                self.game.width // 2 - 120,
                self.game.height // 2 - 15,
                color=C_DOOR,
                size=28,
            )

    def _draw_death(self, screen):
        import pygame

        alpha = min(200, int((1.0 - self.death_timer) / 1.0 * 200))
        overlay = pygame.Surface((self.game.width, self.game.height), pygame.SRCALPHA)
        overlay.fill((80, 0, 0, alpha))
        screen.blit(overlay, (0, 0))
