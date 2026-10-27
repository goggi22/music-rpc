"""
Фоновый сервис координации источников, поиска обложек и отправки в Discord Rich Presence.
"""

import time
import logging
import urllib.parse
from typing import Optional, Callable, Dict, Any

from .core.config import ConfigManager
from .core.discord_ipc import DiscordIPC
from .core.cover_finder import CoverFinder
from .core.cleaner import sanitize_str
from .players.manager import PlayerManager
from .players.base import TrackState

logger = logging.getLogger("MusicRPC.Service")


class MusicRPCService:
    """Основной сервис управления Rich Presence."""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.running = False

        self.ipc = DiscordIPC(self.config.get("client_id", "1262937085635985409"))
        self.cover_finder = CoverFinder(self.config.get("fallback_cover"))
        self.player_manager = PlayerManager(mode=self.config.get("source", "auto"))

        # Колбэки для GUI
        self.on_state_change: Optional[Callable[[Optional[TrackState], str], None]] = None
        self.on_discord_status: Optional[Callable[[bool], None]] = None

        self.last_signature: Optional[str] = None
        self.last_expected_pos = 0.0
        self.last_pos_time = 0.0
        self.last_update_time = 0.0
        self.had_active_presence = False

    def set_source(self, source: str):
        self.config.set("source", source)
        self.player_manager.set_mode(source)

    def tick(self):
        """Один шаг опроса плееров и обновления Discord Presence."""
        is_connected = self.ipc.connected or self.ipc.connect()
        if self.on_discord_status:
            self.on_discord_status(is_connected)

        state = self.player_manager.get_active_state()
        show_paused = bool(self.config.get("show_paused", True))

        if not state or state.status == "Stopped":
            if self.had_active_presence:
                logger.info("Воспроизведение остановлено. Очистка Discord статуса.")
                self.ipc.clear_activity()
                self.had_active_presence = False
                self.last_signature = None
            if self.on_state_change:
                self.on_state_change(None, "")
            return

        if state.status == "Paused" and not show_paused:
            if self.had_active_presence:
                self.ipc.clear_activity()
                self.had_active_presence = False
                self.last_signature = None
            if self.on_state_change:
                self.on_state_change(state, "")
            return

        title = state.title
        artist = state.artist
        pos = state.position
        dur = state.duration
        status = state.status
        now = time.time()

        seeked = False
        if self.last_pos_time > 0 and status == "Playing":
            expected_pos = self.last_expected_pos + (now - self.last_pos_time)
            if abs(pos - expected_pos) > 3.5:
                seeked = True

        base_sig = f"{state.source}|{status}|{artist}|{title}|{int(dur)}"
        time_since_update = now - self.last_update_time

        need_update = (
            base_sig != self.last_signature
            or seeked
            or time_since_update > 25.0
            or not self.had_active_presence
        )

        # Разрешение обложки
        cover_url = ""
        if state.art_url and state.art_url.startswith("http"):
            cover_url = state.art_url
        elif self.config.get("search_covers", True):
            cover_url = self.cover_finder.get_cover(artist, title)
        else:
            cover_url = self.config.get("fallback_cover")

        if self.on_state_change:
            self.on_state_change(state, cover_url)

        if need_update and is_connected:
            # 1. Формирование второй строки (state)
            state_fmt = self.config.get("state_format", "{artist}")
            formatted_state = state_fmt.replace("{artist}", artist).replace("{title}", title)
            if status == "Paused":
                state_text = f"⏸ {formatted_state}"
            else:
                state_text = formatted_state

            # Маленькая иконка источника
            source_labels = {
                "spotify": "in Spotify",
                "telegram": "in Telegram",
                "soundcloud": "in SoundCloud"
            }
            small_label = source_labels.get(state.source, "Playing Music")

            activity_type = int(self.config.get("activity_type", 2))
            activity: Dict[str, Any] = {
                "type": activity_type,
                "details": sanitize_str(title),
                "state": sanitize_str(state_text),
                "assets": {
                    "large_image": cover_url,
                    "small_image": "1",
                    "small_text": f"{small_label} (Пауза)" if status == "Paused" else small_label
                }
            }

            # Название активности
            show_author = bool(self.config.get("show_author_as_activity_name", True))
            if show_author and artist:
                activity["name"] = sanitize_str(artist)
            else:
                activity["name"] = state.source_display or "Music"

            # Прогресс-бар
            if status == "Playing" and dur > 0:
                activity["timestamps"] = {
                    "start": int(now - pos),
                    "end": int(now + (dur - pos))
                }
            elif status == "Playing":
                activity["timestamps"] = {
                    "start": int(now - pos)
                }

            # Кнопка поиска / прослушивания
            if self.config.get("show_button", True):
                if state.track_url and state.track_url.startswith("http"):
                    button_url = state.track_url
                    btn_text = f"В {state.source_display}"
                else:
                    query = urllib.parse.quote_plus(f"{artist} {title}")
                    button_url = f"https://www.youtube.com/results?search_query={query}"
                    btn_text = self.config.get("button_label", "🔍 Найти трек")

                activity["buttons"] = [
                    {
                        "label": sanitize_str(btn_text, min_len=1, max_len=32),
                        "url": button_url
                    }
                ]

            success = self.ipc.set_activity(activity)
            if success:
                if base_sig != self.last_signature:
                    icon = "⏸" if status == "Paused" else "▶"
                    logger.info("[%s] %s Сейчас играет: %s — %s (%d сек)", state.source_display, icon, artist, title, int(dur))
                self.last_signature = base_sig
                self.last_expected_pos = pos
                self.last_pos_time = now
                self.last_update_time = now
                self.had_active_presence = True

    def stop(self):
        self.running = False
        try:
            self.ipc.clear_activity()
            self.ipc.disconnect()
        except Exception:
            pass
