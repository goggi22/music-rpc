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


DEFAULT_CLIENT_IDS = {
    "spotify": "1316777610419634180",    # "Spotify" -> Listening to Spotify
    "telegram": "1262937085635985409",   # "Telegram" -> Listening to Telegram
    "soundcloud": "802958833214423081"   # "SoundCloud" -> Listening to SoundCloud
}

DEFAULT_FALLBACK_COVERS = {
    "spotify": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/spotify.png",
    "soundcloud": "https://cdn.discordapp.com/app-icons/802958833214423081/c07fbcacdd970a86e334d59b27a1fa70.png",
    "telegram": "https://cdn.discordapp.com/app-assets/1262937085635985409/1262949949071691818.png"
}


class MusicRPCService:
    """Основной сервис управления Rich Presence."""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.running = False

        self.client_ids = self.config.get("client_ids", DEFAULT_CLIENT_IDS)
        source = self.config.get("source", "auto")
        if source in self.client_ids:
            initial_id = self.client_ids[source]
        else:
            initial_id = self.client_ids.get("spotify", "1316777610419634180")

        self.ipc = DiscordIPC(initial_id)
        self.cover_finder = CoverFinder(self.config.get("fallback_cover"))
        self.player_manager = PlayerManager(mode=source, config=self.config)

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

        # Разрешение обложки с безопасным фоллбэком под конкретный плеер (никогда не ставить чужую иконку!)
        source_fallback = self.config.get(f"fallback_cover_{state.source}") or DEFAULT_FALLBACK_COVERS.get(state.source, self.config.get("fallback_cover"))
        cover_url = ""
        if state.art_url and state.art_url.startswith("http"):
            cover_url = state.art_url
        elif self.config.get("search_covers", True):
            cover_url = self.cover_finder.get_cover(artist, title, fallback_url=source_fallback)
        else:
            cover_url = source_fallback

        # Автоматическое переключение Client ID под активный источник
        target_client_id = self.client_ids.get(state.source, self.config.get("client_id", "1262937085635985409"))
        if self.ipc.client_id != target_client_id:
            logger.info("[%s] Переключение Discord Application на Client ID: %s", state.source_display, target_client_id)
            self.ipc.reconnect(target_client_id)
            self.last_signature = None
            need_update = True
            is_connected = self.ipc.connected

        if need_update and is_connected:
            activity_type = int(self.config.get("activity_type", 2))

            # Точная настройка под конкретный плеер
            if state.source == "spotify":
                # Заголовок: "Listening to Spotify" (Слушает Spotify)
                activity_name = "Spotify"
                state_text = f"by {artist}" if not artist.lower().startswith("by ") else artist
                if status == "Paused":
                    state_text = f"⏸ {state_text}"

                # Обложка и hover-текст альбома (БЕЗ маленькой иконки, как в оригинале!)
                assets: Dict[str, Any] = {
                    "large_image": cover_url
                }
                if state.album:
                    assets["large_text"] = sanitize_str(state.album)

            elif state.source == "soundcloud":
                # Заголовок: "Listening to SoundCloud" (Слушает SoundCloud)
                activity_name = "SoundCloud"
                state_text = f"by {artist}" if not artist.lower().startswith("by ") else artist
                if status == "Paused":
                    state_text = f"⏸ {state_text}"

                # Маленькая иконка: официальный ассет 'soundcloud' в приложении 802958833214423081
                assets = {
                    "large_image": cover_url,
                    "small_image": "soundcloud",
                    "small_text": "in SoundCloud (Пауза)" if status == "Paused" else "in SoundCloud"
                }
                if state.album:
                    assets["large_text"] = sanitize_str(state.album)

            elif state.source == "telegram":
                # Заголовок: "Listening to Telegram" (Слушает Telegram)
                activity_name = "Telegram"
                state_fmt = self.config.get("state_format", "{artist}")
                formatted_state = state_fmt.replace("{artist}", artist).replace("{title}", title)
                state_text = f"⏸ {formatted_state}" if status == "Paused" else formatted_state

                # Маленькая иконка: ассет '1' в приложении 1262937085635985409
                assets = {
                    "large_image": cover_url,
                    "small_image": "1",
                    "small_text": "in Telegram (Пауза)" if status == "Paused" else "in Telegram"
                }
                if state.album:
                    assets["large_text"] = sanitize_str(state.album)

            else:  # manual / кастомный трек / другое
                activity_name = state.source_display or "Music"
                state_text = f"⏸ {artist}" if status == "Paused" else artist
                assets = {
                    "large_image": cover_url,
                    "small_text": "Music RPC"
                }
                if state.album:
                    assets["large_text"] = sanitize_str(state.album)

            show_author = bool(self.config.get("show_author_as_activity_name", False))
            if show_author and artist:
                activity_name = sanitize_str(artist)

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
