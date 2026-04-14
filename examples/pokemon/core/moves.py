"""Move definitions and damage calculation."""

from __future__ import annotations
from dataclasses import dataclass
import random
from .types import get_effectiveness


@dataclass
class Move:
    name: str
    type: str
    power: int  # 0 = status move
    accuracy: int  # 0-100
    pp: int  # max uses
    pp_current: int = -1
    category: str = "physical"  # physical, special, status
    effect: str = ""  # special effect key

    def __post_init__(self):
        if self.pp_current < 0:
            self.pp_current = self.pp


# ── Move Database ──

MOVES = {
    # Normal
    "tackle": Move("Tackle", "normal", 40, 100, 35, category="physical"),
    "scratch": Move("Scratch", "normal", 40, 100, 35, category="physical"),
    "pound": Move("Pound", "normal", 40, 100, 35, category="physical"),
    "quick_attack": Move("Quick Attack", "normal", 40, 100, 30, category="physical"),
    "headbutt": Move("Headbutt", "normal", 70, 100, 15, category="physical"),
    "slam": Move("Slam", "normal", 80, 75, 20, category="physical"),
    "hyper_beam": Move("Hyper Beam", "normal", 150, 90, 5, category="special"),
    # Fire
    "ember": Move("Ember", "fire", 40, 100, 25, category="special"),
    "flamethrower": Move("Flamethrower", "fire", 90, 100, 15, category="special"),
    "fire_punch": Move("Fire Punch", "fire", 75, 100, 15, category="physical"),
    # Water
    "water_gun": Move("Water Gun", "water", 40, 100, 25, category="special"),
    "surf": Move("Surf", "water", 90, 100, 15, category="special"),
    "bubble": Move("Bubble", "water", 40, 100, 30, category="special"),
    # Grass
    "vine_whip": Move("Vine Whip", "grass", 45, 100, 25, category="physical"),
    "razor_leaf": Move("Razor Leaf", "grass", 55, 95, 25, category="physical"),
    "solar_beam": Move("Solar Beam", "grass", 120, 100, 10, category="special"),
    # Electric
    "thunder_shock": Move("Thunder Shock", "electric", 40, 100, 30, category="special"),
    "thunderbolt": Move("Thunderbolt", "electric", 90, 100, 15, category="special"),
    # Ice
    "ice_beam": Move("Ice Beam", "ice", 90, 100, 10, category="special"),
    # Fighting
    "karate_chop": Move("Karate Chop", "fighting", 50, 100, 25, category="physical"),
    # Poison
    "poison_sting": Move("Poison Sting", "poison", 15, 100, 35, category="physical"),
    "sludge_bomb": Move("Sludge Bomb", "poison", 90, 100, 10, category="special"),
    # Ground
    "earthquake": Move("Earthquake", "ground", 100, 100, 10, category="physical"),
    "dig": Move("Dig", "ground", 80, 100, 10, category="physical"),
    # Flying
    "peck": Move("Peck", "flying", 35, 100, 35, category="physical"),
    "wing_attack": Move("Wing Attack", "flying", 60, 100, 35, category="physical"),
    # Psychic
    "confusion": Move("Confusion", "psychic", 50, 100, 25, category="special"),
    "psychic_move": Move("Psychic", "psychic", 90, 100, 10, category="special"),
    # Bug
    "bug_bite": Move("Bug Bite", "bug", 60, 100, 20, category="physical"),
    # Rock
    "rock_throw": Move("Rock Throw", "rock", 50, 90, 15, category="physical"),
    # Ghost
    "shadow_ball": Move("Shadow Ball", "ghost", 80, 100, 15, category="special"),
    "lick": Move("Lick", "ghost", 30, 100, 30, category="physical"),
    # Dragon
    "dragon_rage": Move("Dragon Rage", "dragon", 60, 100, 10, category="special"),
}


def get_move(name: str) -> Move:
    """Get a fresh copy of a move."""
    m = MOVES[name]
    return Move(m.name, m.type, m.power, m.accuracy, m.pp, m.pp, m.category, m.effect)


def calc_damage(attacker, defender, move: Move) -> tuple[int, float, bool]:
    """
    Calculate damage. Returns (damage, effectiveness, is_crit).
    attacker/defender are Pokemon objects.
    """
    if move.power == 0:
        return 0, 1.0, False

    # Miss check
    if random.randint(1, 100) > move.accuracy:
        return 0, 1.0, False

    # Base damage formula (simplified Gen 1)
    level = attacker.level
    if move.category == "physical":
        atk = attacker.stats["attack"]
        dfn = defender.stats["defense"]
    else:
        atk = attacker.stats["sp_attack"]
        dfn = defender.stats["sp_defense"]

    base = ((2 * level / 5 + 2) * move.power * atk / dfn) / 50 + 2

    # STAB (Same Type Attack Bonus)
    stab = 1.5 if move.type == attacker.ptype else 1.0

    # Type effectiveness
    effectiveness = get_effectiveness(move.type, defender.ptype)

    # Critical hit (6.25% chance)
    is_crit = random.random() < 0.0625
    crit_mult = 1.5 if is_crit else 1.0

    # Random factor
    rand_factor = random.uniform(0.85, 1.0)

    damage = int(base * stab * effectiveness * crit_mult * rand_factor)
    damage = max(1, damage)  # minimum 1 damage

    return damage, effectiveness, is_crit
