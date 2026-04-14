"""Pokemon type system with effectiveness chart."""

TYPES = [
    "normal",
    "fire",
    "water",
    "grass",
    "electric",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
]

# Effectiveness: attacker_type -> {defender_type: multiplier}
# Only listing non-1.0 matchups
CHART = {
    "fire": {
        "grass": 2,
        "ice": 2,
        "bug": 2,
        "fire": 0.5,
        "water": 0.5,
        "rock": 0.5,
        "dragon": 0.5,
    },
    "water": {
        "fire": 2,
        "ground": 2,
        "rock": 2,
        "water": 0.5,
        "grass": 0.5,
        "dragon": 0.5,
    },
    "grass": {
        "water": 2,
        "ground": 2,
        "rock": 2,
        "fire": 0.5,
        "grass": 0.5,
        "poison": 0.5,
        "flying": 0.5,
        "bug": 0.5,
        "dragon": 0.5,
    },
    "electric": {
        "water": 2,
        "flying": 2,
        "electric": 0.5,
        "grass": 0.5,
        "ground": 0,
        "dragon": 0.5,
    },
    "ice": {
        "grass": 2,
        "ground": 2,
        "flying": 2,
        "dragon": 2,
        "fire": 0.5,
        "water": 0.5,
        "ice": 0.5,
    },
    "fighting": {
        "normal": 2,
        "ice": 2,
        "rock": 2,
        "poison": 0.5,
        "flying": 0.5,
        "psychic": 0.5,
        "bug": 0.5,
        "ghost": 0,
    },
    "poison": {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5},
    "ground": {
        "fire": 2,
        "electric": 2,
        "poison": 2,
        "rock": 2,
        "grass": 0.5,
        "bug": 0.5,
        "flying": 0,
    },
    "flying": {"grass": 2, "fighting": 2, "bug": 2, "electric": 0.5, "rock": 0.5},
    "psychic": {"fighting": 2, "poison": 2, "psychic": 0.5},
    "bug": {
        "grass": 2,
        "psychic": 2,
        "fire": 0.5,
        "fighting": 0.5,
        "flying": 0.5,
        "poison": 0.5,
        "ghost": 0.5,
    },
    "rock": {
        "fire": 2,
        "ice": 2,
        "flying": 2,
        "bug": 2,
        "fighting": 0.5,
        "ground": 0.5,
    },
    "ghost": {"ghost": 2, "psychic": 2, "normal": 0},
    "dragon": {"dragon": 2},
    "normal": {"rock": 0.5, "ghost": 0},
}


def get_effectiveness(attack_type: str, defend_type: str) -> float:
    """Get type effectiveness multiplier."""
    if attack_type not in CHART:
        return 1.0
    return CHART[attack_type].get(defend_type, 1.0)


def get_type_color(ptype: str) -> tuple:
    """Get display color for a type."""
    colors = {
        "normal": (168, 168, 120),
        "fire": (240, 128, 48),
        "water": (104, 144, 240),
        "grass": (120, 200, 80),
        "electric": (248, 208, 48),
        "ice": (152, 216, 216),
        "fighting": (192, 48, 40),
        "poison": (160, 64, 160),
        "ground": (224, 192, 104),
        "flying": (168, 144, 240),
        "psychic": (248, 88, 136),
        "bug": (168, 184, 32),
        "rock": (184, 160, 56),
        "ghost": (112, 88, 152),
        "dragon": (112, 56, 248),
    }
    return colors.get(ptype, (200, 200, 200))
