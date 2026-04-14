"""Pokemon: stats, leveling, evolution, the whole deal."""

from __future__ import annotations
from dataclasses import dataclass
import random
from .moves import get_move, Move


@dataclass
class PokemonSpecies:
    """Template for a pokemon species."""

    name: str
    ptype: str
    base_hp: int
    base_attack: int
    base_defense: int
    base_sp_attack: int
    base_sp_defense: int
    base_speed: int
    moves_by_level: dict  # {level: move_name}
    catch_rate: int = 100  # 0-255
    xp_yield: int = 50
    color: tuple = (200, 200, 200)
    evolves_to: str = ""
    evolve_level: int = 0


# ── Pokedex ──

POKEDEX: dict[str, PokemonSpecies] = {
    "blaziken": PokemonSpecies(
        "Blaziken",
        "fire",
        80,
        120,
        70,
        110,
        70,
        80,
        {
            1: "scratch",
            5: "ember",
            10: "karate_chop",
            16: "fire_punch",
            22: "flamethrower",
        },
        catch_rate=45,
        xp_yield=120,
        color=(240, 100, 40),
    ),
    "feraligatr": PokemonSpecies(
        "Feraligatr",
        "water",
        85,
        105,
        100,
        79,
        83,
        78,
        {1: "scratch", 5: "water_gun", 12: "headbutt", 18: "surf"},
        catch_rate=45,
        xp_yield=120,
        color=(80, 130, 220),
    ),
    "sceptile": PokemonSpecies(
        "Sceptile",
        "grass",
        70,
        85,
        65,
        105,
        85,
        120,
        {
            1: "pound",
            5: "vine_whip",
            10: "quick_attack",
            16: "razor_leaf",
            22: "solar_beam",
        },
        catch_rate=45,
        xp_yield=120,
        color=(80, 190, 60),
    ),
    "pikachu": PokemonSpecies(
        "Pikachu",
        "electric",
        35,
        55,
        40,
        50,
        50,
        90,
        {1: "tackle", 5: "thunder_shock", 15: "quick_attack", 22: "thunderbolt"},
        catch_rate=190,
        xp_yield=82,
        color=(248, 208, 48),
        evolves_to="raichu",
        evolve_level=25,
    ),
    "raichu": PokemonSpecies(
        "Raichu",
        "electric",
        60,
        90,
        55,
        90,
        80,
        110,
        {1: "thunder_shock", 1: "thunderbolt"},
        catch_rate=75,
        xp_yield=122,
        color=(248, 180, 48),
    ),
    "geodude": PokemonSpecies(
        "Geodude",
        "rock",
        40,
        80,
        100,
        30,
        30,
        20,
        {1: "tackle", 6: "rock_throw", 15: "dig", 20: "earthquake"},
        catch_rate=255,
        xp_yield=60,
        color=(180, 160, 100),
    ),
    "zubat": PokemonSpecies(
        "Zubat",
        "flying",
        40,
        45,
        35,
        30,
        40,
        55,
        {1: "peck", 8: "wing_attack", 15: "confusion"},
        catch_rate=255,
        xp_yield=49,
        color=(150, 100, 200),
    ),
    "gastly": PokemonSpecies(
        "Gastly",
        "ghost",
        30,
        35,
        30,
        100,
        35,
        80,
        {1: "lick", 8: "confusion", 16: "shadow_ball"},
        catch_rate=190,
        xp_yield=62,
        color=(100, 70, 150),
    ),
    "machop": PokemonSpecies(
        "Machop",
        "fighting",
        70,
        80,
        50,
        35,
        35,
        35,
        {1: "karate_chop", 10: "headbutt", 18: "slam"},
        catch_rate=180,
        xp_yield=61,
        color=(160, 160, 180),
    ),
    "bulbasaur": PokemonSpecies(
        "Bulbasaur",
        "grass",
        45,
        49,
        49,
        65,
        65,
        45,
        {1: "tackle", 5: "vine_whip", 13: "razor_leaf", 20: "solar_beam"},
        catch_rate=45,
        xp_yield=64,
        color=(100, 180, 120),
    ),
    "charmander": PokemonSpecies(
        "Charmander",
        "fire",
        39,
        52,
        43,
        60,
        50,
        65,
        {1: "scratch", 5: "ember", 15: "fire_punch", 22: "flamethrower"},
        catch_rate=45,
        xp_yield=62,
        color=(240, 140, 50),
    ),
    "squirtle": PokemonSpecies(
        "Squirtle",
        "water",
        44,
        48,
        65,
        50,
        64,
        43,
        {1: "tackle", 5: "bubble", 12: "water_gun", 20: "surf"},
        catch_rate=45,
        xp_yield=63,
        color=(100, 160, 230),
    ),
    "rattata": PokemonSpecies(
        "Rattata",
        "normal",
        30,
        56,
        35,
        25,
        35,
        72,
        {1: "tackle", 7: "quick_attack", 14: "headbutt"},
        catch_rate=255,
        xp_yield=51,
        color=(160, 130, 180),
    ),
    "pidgey": PokemonSpecies(
        "Pidgey",
        "flying",
        40,
        45,
        40,
        35,
        35,
        56,
        {1: "tackle", 5: "peck", 12: "wing_attack", 18: "quick_attack"},
        catch_rate=255,
        xp_yield=50,
        color=(180, 160, 120),
    ),
    "caterpie": PokemonSpecies(
        "Caterpie",
        "bug",
        45,
        30,
        35,
        20,
        20,
        45,
        {1: "tackle", 8: "bug_bite"},
        catch_rate=255,
        xp_yield=39,
        color=(120, 200, 80),
    ),
    "nidoran": PokemonSpecies(
        "Nidoran",
        "poison",
        46,
        57,
        40,
        40,
        40,
        50,
        {1: "poison_sting", 8: "peck", 16: "headbutt"},
        catch_rate=235,
        xp_yield=55,
        color=(180, 100, 180),
    ),
}


def xp_for_level(level: int) -> int:
    """XP needed to reach a given level (medium-fast growth)."""
    return int(level**3)


class Pokemon:
    """A single pokemon instance with stats, moves, HP."""

    def __init__(self, species_name: str, level: int):
        self.species = POKEDEX[species_name]
        self.name = self.species.name
        self.ptype = self.species.ptype
        self.level = level
        self.xp = xp_for_level(level)
        self.color = self.species.color

        # Calculate stats
        self.stats = self._calc_stats()
        self.hp = self.stats["hp"]
        self.max_hp = self.stats["hp"]

        # Learn moves up to current level
        self.moves: list[Move] = []
        for lvl, move_name in sorted(self.species.moves_by_level.items()):
            if lvl <= level:
                self.moves.append(get_move(move_name))
        # Keep last 4
        self.moves = self.moves[-4:]

    def _calc_stats(self) -> dict:
        s = self.species
        level = self.level
        return {
            "hp": int((2 * s.base_hp * level / 100) + level + 10),
            "attack": int((2 * s.base_attack * level / 100) + 5),
            "defense": int((2 * s.base_defense * level / 100) + 5),
            "sp_attack": int((2 * s.base_sp_attack * level / 100) + 5),
            "sp_defense": int((2 * s.base_sp_defense * level / 100) + 5),
            "speed": int((2 * s.base_speed * level / 100) + 5),
        }

    def gain_xp(self, amount: int) -> list[str]:
        """Gain XP. Returns list of messages (level up, new move, evolution)."""
        messages = []
        self.xp += amount
        while self.xp >= xp_for_level(self.level + 1):
            self.level += 1
            old_hp_pct = self.hp / self.max_hp
            self.stats = self._calc_stats()
            self.max_hp = self.stats["hp"]
            self.hp = int(self.max_hp * old_hp_pct)
            messages.append(f"{self.name} grew to Lv.{self.level}!")

            # Learn new move
            move_name = self.species.moves_by_level.get(self.level)
            if move_name:
                new_move = get_move(move_name)
                if len(self.moves) < 4:
                    self.moves.append(new_move)
                    messages.append(f"{self.name} learned {new_move.name}!")
                else:
                    # Replace weakest move
                    weakest = min(
                        range(len(self.moves)), key=lambda i: self.moves[i].power
                    )
                    old_name = self.moves[weakest].name
                    self.moves[weakest] = new_move
                    messages.append(
                        f"{self.name} forgot {old_name} and learned {new_move.name}!"
                    )

            # Check evolution
            if self.species.evolves_to and self.level >= self.species.evolve_level:
                old_name = self.name
                self.species = POKEDEX[self.species.evolves_to]
                self.name = self.species.name
                self.ptype = self.species.ptype
                self.color = self.species.color
                self.stats = self._calc_stats()
                self.max_hp = self.stats["hp"]
                self.hp = self.max_hp
                messages.append(f"{old_name} evolved into {self.name}!")

        return messages

    def heal(self):
        """Full heal."""
        self.hp = self.max_hp
        for move in self.moves:
            move.pp_current = move.pp

    @property
    def is_fainted(self) -> bool:
        return self.hp <= 0

    @property
    def hp_pct(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0

    def __repr__(self):
        return f"{self.name} Lv.{self.level} ({self.hp}/{self.max_hp})"


def make_wild(species_name: str, level_range: tuple[int, int]) -> Pokemon:
    """Create a wild pokemon at a random level in range."""
    level = random.randint(*level_range)
    return Pokemon(species_name, level)
