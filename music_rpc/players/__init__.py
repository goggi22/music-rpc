"""
Пакет источников воспроизведения (Spotify, Telegram, SoundCloud).
"""

from .base import TrackState, BasePlayerWatcher
from .spotify import SpotifyWatcher
from .telegram import TelegramWatcher
from .soundcloud import SoundCloudWatcher
from .manager import PlayerManager

__all__ = [
    "TrackState",
    "BasePlayerWatcher",
    "SpotifyWatcher",
    "TelegramWatcher",
    "SoundCloudWatcher",
    "PlayerManager",
]
