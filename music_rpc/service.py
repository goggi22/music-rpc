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

    def set_manual_track(self, artist: str, title: str, album: str = "", duration: float = 0.0):
        self.player_manager.set_manual_track(artist, title, album, duration)

    def get_available_tracks(self) -> Dict[str, Optional[TrackState]]:
        return self.player_manager.get_all_states()

    def get_current_track(self) -> Optional[TrackState]:
        return self.player_manager.get_active_state()

    def control_media(self, action: str) -> bool:
        return self.player_manager.control_media(action)

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
            activity_type = int(self.config.get("activity_type", 2))

            # Точная настройка под конкретный плеер
            if state.source == "spotify":
                # 100% вид официального Spotify в Discord:
                # 1. Заголовок: "Listening to Spotify" (Слушает Spotify)
                activity_name = "Spotify"
                # 2. Исполнитель: "by <Artist>"
                if not artist.lower().startswith("by "):
                    state_text = f"by {artist}"
                else:
                    state_text = artist
                if status == "Paused":
                    state_text = f"⏸ {state_text}"

                # 3. Обложка и hover-текст альбома (БЕЗ маленькой иконки в углу, как в оригинале!)
                assets: Dict[str, Any] = {
                    "large_image": cover_url
                }
                if state.album:
                    assets["large_text"] = sanitize_str(state.album)

            elif state.source == "soundcloud":
                show_author = bool(self.config.get("show_author_as_activity_name", True))
                activity_name = sanitize_str(artist) if show_author and artist else "SoundCloud"
                if not artist.lower().startswith("by "):
                    state_text = f"by {artist}"
                else:
                    state_text = artist
                if status == "Paused":
                    state_text = f"⏸ {state_text}"

                assets = {
                    "large_image": cover_url,
                    "small_image": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/soundcloud.png",
                    "small_text": "in SoundCloud (Пауза)" if status == "Paused" else "in SoundCloud"
                }
                if state.album:
                    assets["large_text"] = sanitize_str(state.album)

            elif state.source == "telegram":
                show_author = bool(self.config.get("show_author_as_activity_name", True))
                activity_name = sanitize_str(artist) if show_author and artist else (state.source_display or "Telegram")

                state_fmt = self.config.get("state_format", "{artist}")
                formatted_state = state_fmt.replace("{artist}", artist).replace("{title}", title)
                state_text = f"⏸ {formatted_state}" if status == "Paused" else formatted_state

                assets = {
                    "large_image": cover_url,
                    "small_image": "1",  # Telegram иконка в ID приложения
                    "small_text": "in Telegram (Пауза)" if status == "Paused" else "in Telegram"
                }
                if state.album:
                    assets["large_text"] = sanitize_str(state.album)

            else:  # manual / кастомный трек / другое
                show_author = bool(self.config.get("show_author_as_activity_name", True))
                activity_name = sanitize_str(artist) if show_author and artist else (state.source_display or "Music")
                state_text = f"⏸ {artist}" if status == "Paused" else artist
                assets = {
                    "large_image": cover_url,
                    "small_text": "Music RPC"
                }
                if state.album:
                    assets["large_text"] = sanitize_str(state.album)

            activity: Dict[str, Any] = {
                "type": activity_type,
                "name": activity_name,
                "details": sanitize_str(title),
                "state": sanitize_str(state_text),
                "assets": assets
            }

            # Прогресс-бар / таймлайн
            if status == "Playing" and dur > 0:
                activity["timestamps"] = {
                    "start": int(now - pos),
                    "end": int(now + (dur - pos))
                }
            elif status == "Playing":
                activity["timestamps"] = {
                    "start": int(now - pos)
                }

            # Кнопка перехода к треку
            if self.config.get("show_button", True):
                if state.source == "spotify":
                    if state.track_url and state.track_url.startswith("http"):
                        button_url = state.track_url
                    elif state.track_url and state.track_url.startswith("spotify:track:"):
                        track_id = state.track_url.split(":")[-1]
                        button_url = f"https://open.spotify.com/track/{track_id}"
                    else:
                        query = urllib.parse.quote_plus(f"{artist} {title}")
                        button_url = f"https://open.spotify.com/search/{query}"
                    btn_text = "Слушать в Spotify"
                elif state.source == "soundcloud":
                    if state.track_url and state.track_url.startswith("http"):
                        button_url = state.track_url
                    else:
                        query = urllib.parse.quote_plus(f"{artist} {title}")
                        button_url = f"https://soundcloud.com/search?q={query}"
                    btn_text = "В SoundCloud"
                else:
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
