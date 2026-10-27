"""
Ядро сервиса Music RPC.
"""

from .config import ConfigManager, DEFAULT_CONFIG
from .discord_ipc import DiscordIPC
from .cover_finder import CoverFinder
from .artist_finder import ArtistFinder
from .cleaner import clean_text, sanitize_str, split_artist_title

__all__ = [
    "ConfigManager",
    "DEFAULT_CONFIG",
    "DiscordIPC",
    "CoverFinder",
    "ArtistFinder",
    "clean_text",
    "sanitize_str",
    "split_artist_title",
]
