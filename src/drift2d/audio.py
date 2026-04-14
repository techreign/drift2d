"""Simple audio manager for sounds and music."""

from __future__ import annotations
from pathlib import Path
import pygame


class Audio:
    """Load and play sounds/music from assets/sounds/."""

    def __init__(self, asset_root: Path):
        self.asset_root = asset_root / "sounds"
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._music_playing: str = ""

    def _load_sound(self, name: str) -> pygame.mixer.Sound | None:
        if name not in self._sounds:
            path = self.asset_root / name
            if path.exists():
                self._sounds[name] = pygame.mixer.Sound(str(path))
            else:
                print(f"[drift] Sound not found: {path}")
                return None
        return self._sounds[name]

    def play(self, name: str, volume: float = 1.0, loops: int = 0):
        sound = self._load_sound(name)
        if sound:
            sound.set_volume(volume)
            sound.play(loops=loops)

    def play_music(self, name: str, volume: float = 0.5, loops: int = -1):
        path = self.asset_root / name
        if path.exists() and self._music_playing != name:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=loops)
            self._music_playing = name

    def stop_music(self):
        pygame.mixer.music.stop()
        self._music_playing = ""
