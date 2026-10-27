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

    def __init__(self, mode: str = "auto", artist_finder: Optional[ArtistFinder] = None, config: Optional[object] = None):
        self.mode = mode.lower().strip()
        self.artist_finder = artist_finder or ArtistFinder()
        self.manual_state: Optional[TrackState] = None
        self.config = config

        filter_tg = True
        min_dur = 12.0
        hints = None
        auto_detect = True
        if self.config and hasattr(self.config, "get"):
            filter_tg = self.config.get("telegram_filter_non_music", True)
            min_dur = float(self.config.get("telegram_min_duration_seconds", 12.0))
            hints = self.config.get("player_name_hints", None)
            auto_detect = self.config.get("auto_detect_missing_artist", True)

        self.watchers: Dict[str, BasePlayerWatcher] = {
            "spotify": SpotifyWatcher(),
            "telegram": TelegramWatcher(
                hints=hints,
                artist_finder=self.artist_finder,
                auto_detect=auto_detect,
                filter_non_music=filter_tg,
                min_duration=min_dur
            ),
            "soundcloud": SoundCloudWatcher()
        }

    def set_mode(self, mode: str):
        self.mode = mode.lower().strip()
        logger.info("Режим плеера переключен на: %s", self.mode)

    def set_manual_track(self, artist: str, title: str, album: str = "", duration: float = 0.0):
        self.mode = "manual"
        self.manual_state = TrackState(
            status="Playing",
            title=title.strip(),
            artist=artist.strip(),
            album=album.strip(),
            duration=duration,
            source="manual",
            source_display="Кастомный трек"
        )
        logger.info("Установлен ручной трек: %s — %s", artist, title)

    def get_all_states(self) -> Dict[str, Optional[TrackState]]:
        """Возвращает текущие состояния всех доступных плееров."""
        states: Dict[str, Optional[TrackState]] = {}
        for name in ("spotify", "telegram", "soundcloud"):
            try:
                states[name] = self.watchers[name].get_state()
            except Exception as e:
                logger.debug("Ошибка получения состояния %s: %s", name, e)
                states[name] = None
        if self.manual_state:
            states["manual"] = self.manual_state
        return states

    def get_active_state(self) -> Optional[TrackState]:
        """Возвращает текущий трек в зависимости от выбранного режима."""
        if self.mode == "manual":
            return self.manual_state

        if self.mode in self.watchers:
            watcher = self.watchers[self.mode]
            return watcher.get_state()

        # Режим "auto" (умный автовыбор):
        states = self.get_all_states()

        # 1. Проверяем, кто сейчас активно играет (Playing)
        # Приоритет: сначала музыкальные сервисы (Spotify, SoundCloud), затем мессенджер (Telegram)
        for name in ("spotify", "soundcloud", "telegram"):
            st = states.get(name)
            if st and st.status == "Playing":
                return st

        # 2. Если никто не играет, берем плеер на паузе (Paused)
        for name in ("spotify", "soundcloud", "telegram"):
            st = states.get(name)
            if st and st.status == "Paused":
                return st

        return None

    def control_media(self, action: str) -> bool:
        """Отправляет команду управления (PlayPause, Next, Previous) активному плееру."""
        target_name = self.mode if self.mode in self.watchers else None
        if not target_name:
            states = self.get_all_states()
            for name in ("spotify", "soundcloud", "telegram"):
                st = states.get(name)
                if st and st.is_active:
                    target_name = name
                    break

        if not target_name:
            return False

        watcher = self.watchers.get(target_name)
        if watcher and hasattr(watcher, "control_media"):
            return watcher.control_media(action)
        return False
