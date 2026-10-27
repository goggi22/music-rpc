"""
Менеджер настроек Music RPC.
"""

import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("MusicRPC.Config")

DEFAULT_CONFIG: Dict[str, Any] = {
    # Discord Client Application ID
    "client_id": "1262937085635985409",
    # Выбранный источник: "auto", "spotify", "telegram", "soundcloud"
    "source": "auto",
    # Тип активности: 2 = Listening ("Слушает <Автор>")
    "activity_type": 2,
    # Отображать имя автора в заголовке активности ("Слушает <Автор>")
    "show_author_as_activity_name": True,
    # Формат второй строки (state)
    "state_format": "{artist}",
    # Автоматически определять автора через сеть, если автор не указан
    "auto_detect_missing_artist": True,
    # Искать обложки через Deezer/SoundCloud/iTunes
    "search_covers": True,
    # Поведение при паузе (показывать статус паузы или скрывать)
    "show_paused": True,
    # Кнопка со ссылкой в профиле Discord
    "show_button": True,
    "button_label": "🔍 Найти трек",
    # Интервал опроса плееров (сек)
    "poll_interval_seconds": 1.0,
    # Сворачивать в системный трей при закрытии крестиком
    "minimize_to_tray": True,
    # Запускать свернутым в трей
    "start_minimized": False,
    # Обложка по умолчанию
    "fallback_cover": "https://cdn.discordapp.com/app-assets/1262937085635985409/1262949949071691818.png",
    # Поддерживаемые имена процессов Telegram
    "telegram_hints": ["telegram", "ayugram", "tdesktop", "64gram", "kotatogram"],
    # Поддерживаемые имена процессов Spotify
    "spotify_hints": ["spotify"],
    # Поддерживаемые браузеры для SoundCloud
    "browser_hints": ["chrome", "msedge", "firefox", "brave", "opera", "vivaldi", "yandex", "chromium"]
}


class ConfigManager:
    """Управление файлом конфигурации config.json."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = os.path.abspath(config_path)
        self.data: Dict[str, Any] = self.load()

    def load(self) -> Dict[str, Any]:
        cfg = DEFAULT_CONFIG.copy()
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    cfg.update(user_cfg)
            except Exception as e:
                logger.warning("Не удалось прочитать %s: %s", self.config_path, e)
        else:
            self.save(cfg)
        return cfg

    def save(self, data: Dict[str, Any] = None) -> bool:
        if data is not None:
            self.data = data
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Ошибка сохранения %s: %s", self.config_path, e)
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, DEFAULT_CONFIG.get(key, default))

    def set(self, key: str, value: Any, auto_save: bool = True):
        self.data[key] = value
        if auto_save:
            self.save()
