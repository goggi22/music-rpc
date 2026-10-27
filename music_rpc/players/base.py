"""
Базовые классы и структуры данных для мониторинга музыкальных плееров.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TrackState:
    """Состояние воспроизведения текущего трека."""
    status: str            # "Playing", "Paused", "Stopped"
    title: str             # Название трека
    artist: str            # Исполнитель
    album: str = ""        # Название альбома
    position: float = 0.0  # Текущая позиция (сек)
    duration: float = 0.0  # Длительность (сек)
    art_url: str = ""      # Прямая ссылка на обложку (если есть)
    track_url: str = ""    # Ссылка на трек (Spotify, SoundCloud, etc.)
    source: str = ""       # Кодовое имя: "spotify", "telegram", "soundcloud"
    source_display: str = "" # Отображаемое имя: "Spotify", "Telegram", "SoundCloud"

    @property
    def is_playing(self) -> bool:
        return self.status == "Playing"

    @property
    def is_paused(self) -> bool:
        return self.status == "Paused"

    @property
    def is_active(self) -> bool:
        return self.status in ("Playing", "Paused")


class BasePlayerWatcher:
    """Базовый интерфейс наблюдателя за плеером."""

    def get_state(self) -> Optional[TrackState]:
        """Возвращает текущее состояние трека или None, если плеер не запущен."""
        raise NotImplementedError

    def control_media(self, action: str) -> bool:
        """Управление воспроизведением (PlayPause, Next, Previous)."""
        return False
