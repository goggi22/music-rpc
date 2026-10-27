"""
Универсальный менеджер плееров с поддержкой ручного выбора и авто-режима.
"""

import logging
from typing import Optional, Dict
from .base import BasePlayerWatcher, TrackState
from .spotify import SpotifyWatcher
from .telegram import TelegramWatcher
from .soundcloud import SoundCloudWatcher
from ..core.artist_finder import ArtistFinder

logger = logging.getLogger("MusicRPC.PlayerManager")


class PlayerManager:
    """Управление активными наблюдателями за плеерами."""

    def __init__(self, mode: str = "auto", artist_finder: Optional[ArtistFinder] = None):
        self.mode = mode.lower().strip()
        self.artist_finder = artist_finder or ArtistFinder()

        self.watchers: Dict[str, BasePlayerWatcher] = {
            "spotify": SpotifyWatcher(),
            "telegram": TelegramWatcher(artist_finder=self.artist_finder),
            "soundcloud": SoundCloudWatcher()
        }

    def set_mode(self, mode: str):
        self.mode = mode.lower().strip()
        logger.info("Режим плеера переключен на: %s", self.mode)

    def get_active_state(self) -> Optional[TrackState]:
        """Возвращает текущий трек в зависимости от выбранного режима."""
        if self.mode in self.watchers:
            watcher = self.watchers[self.mode]
            return watcher.get_state()

        # Режим "auto" (умный автовыбор):
        # 1. Проверяем, кто сейчас активно играет (Playing)
        states = {}
        for name in ("spotify", "telegram", "soundcloud"):
            st = self.watchers[name].get_state()
            if st:
                states[name] = st
                if st.status == "Playing":
                    return st

        # 2. Если никто не играет, берем плеер на паузе (Paused)
        for name in ("spotify", "telegram", "soundcloud"):
            st = states.get(name)
            if st and st.status == "Paused":
                return st

        return None
