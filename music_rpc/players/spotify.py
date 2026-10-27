"""
Мониторинг воспроизведения Spotify (Linux MPRIS и Windows SMTC).
Работает локально с плеером — никакой VPN не требуется!
"""

import sys
import re
import logging
from typing import Optional, List
from .base import BasePlayerWatcher, TrackState
from ..core.cleaner import clean_text, split_artist_title

logger = logging.getLogger("MusicRPC.Spotify")

if sys.platform != "win32":
    try:
        import dbus
    except ImportError:
        dbus = None
else:
    dbus = None


class SpotifyWatcher(BasePlayerWatcher):
    """Мониторинг плеера Spotify без VPN (официальное приложение + веб-версия open.spotify.com)."""

    def __init__(self, hints: Optional[List[str]] = None, browser_hints: Optional[List[str]] = None):
        self.hints = [h.lower() for h in (hints or ["spotify"])]
        self.browser_hints = [b.lower() for b in (browser_hints or [
            "chrome", "msedge", "firefox", "zen", "brave", "opera", "vivaldi", "chromium", "yandex"
        ])]
        self.bus = dbus.SessionBus() if dbus else None
        self._active_linux_bus: Optional[str] = None

    @staticmethod
    def _clean_spotify_title(raw_title: str, raw_artist: str) -> tuple:
        title = raw_title.strip()
        artist = raw_artist.strip()

        # Очистка браузерных хвостов Spotify: "Track • Artist - Spotify" или "Track - Spotify"
        title = re.sub(r'[\s\-|–—·]+Spotify.*$', '', title, flags=re.IGNORECASE).strip()

        # Формат вкладки Spotify: "Track Name • Artist"
        if "•" in title:
            parts = [p.strip() for p in title.split("•") if p.strip()]
            if len(parts) >= 2:
                title = parts[0]
                if not artist or artist.lower() in ("spotify", "unknown"):
                    artist = parts[1]

        # Если автор не указан или "Spotify", пробуем разделить "Исполнитель - Трек"
        if not artist or artist.lower() in ("spotify", "unknown", ""):
            split_art, split_tit = split_artist_title(title)
            if split_art and split_tit:
                artist = split_art
                title = split_tit

        artist, title = clean_text(title, artist)
        return artist or "Spotify", title or "Трек Spotify"

    def get_state(self) -> Optional[TrackState]:
        if sys.platform == "win32":
            return self._get_state_windows()
        else:
            return self._get_state_linux()

    def _get_state_linux(self) -> Optional[TrackState]:
        if not self.bus:
            return None

        # 1. Сначала ищем официальный десктопный клиент Spotify в MPRIS
        try:
            for name in self.bus.list_names():
                if name == "org.mpris.MediaPlayer2.spotify" or (name.startswith("org.mpris.MediaPlayer2.") and "spotify" in name.lower()):
                    obj = self.bus.get_object(name, "/org/mpris/MediaPlayer2")
                    props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                    raw_status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))

                    if raw_status in ("Playing", "Paused"):
                        metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
                        raw_title = str(metadata.get("xesam:title", "")).strip()

                        artists = metadata.get("xesam:artist", "")
                        if isinstance(artists, (list, tuple, dbus.Array)):
                            raw_artist = ", ".join(str(a) for a in artists if str(a).strip()).strip()
                        else:
                            raw_artist = str(artists).strip()

                        artist, title = self._clean_spotify_title(raw_title, raw_artist)
                        album = str(metadata.get("xesam:album", "")).strip()
                        art_url = str(metadata.get("mpris:artUrl", "")).strip()
                        track_url = str(metadata.get("xesam:url", "")).strip()

                        try:
                            pos_micro = int(props.Get("org.mpris.MediaPlayer2.Player", "Position"))
                            position_sec = max(0.0, pos_micro / 1_000_000.0)
                        except Exception:
                            position_sec = 0.0

                        length_micro = int(metadata.get("mpris:length", 0))
                        duration_sec = max(0.0, length_micro / 1_000_000.0)

                        self._active_linux_bus = name
                        return TrackState(
                            status=raw_status,
                            title=title,
                            artist=artist,
                            album=album,
                            position=position_sec,
                            duration=duration_sec,
                            art_url=art_url,
                            track_url=track_url,
                            source="spotify",
                            source_display="Spotify"
                        )
        except Exception as e:
            logger.debug("Ошибка опроса нативного Spotify Linux: %s", e)

        # 2. Если нативный клиент не играет, ищем веб-плеер Spotify (open.spotify.com) во вкладках браузеров
        try:
            browser_buses = []
            for name in self.bus.list_names():
                if name.startswith("org.mpris.MediaPlayer2."):
                    lower = name.lower()
                    if any(b in lower for b in self.browser_hints):
                        browser_buses.append(name)

            paused_cand = None
            for b_name in browser_buses:
                try:
                    obj = self.bus.get_object(b_name, "/org/mpris/MediaPlayer2")
                    props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                    raw_status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
                    if raw_status not in ("Playing", "Paused"):
                        continue

                    metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
                    track_url = str(metadata.get("xesam:url", "")).strip()
                    track_id = str(metadata.get("mpris:trackid", "")).strip()
                    raw_title = str(metadata.get("xesam:title", "")).strip()
                    album = str(metadata.get("xesam:album", "")).strip()

                    is_spotify = (
                        "spotify.com" in track_url.lower()
                        or "spotify" in track_id.lower()
                        or track_url.startswith("spotify:")
                        or "spotify" in album.lower()
                        or raw_title.lower().endswith("spotify")
                        or " • " in raw_title and "spotify" in b_name.lower()
                    )

                    if not is_spotify:
                        continue

                    artists = metadata.get("xesam:artist", "")
                    if isinstance(artists, (list, tuple, dbus.Array)):
                        raw_artist = ", ".join(str(a) for a in artists if str(a).strip()).strip()
                    else:
                        raw_artist = str(artists).strip()

                    artist, title = self._clean_spotify_title(raw_title, raw_artist)
                    art_url = str(metadata.get("mpris:artUrl", "")).strip()

                    try:
                        pos_micro = int(props.Get("org.mpris.MediaPlayer2.Player", "Position"))
                        position_sec = max(0.0, pos_micro / 1_000_000.0)
                    except Exception:
                        position_sec = 0.0

                    length_micro = int(metadata.get("mpris:length", 0))
                    duration_sec = max(0.0, length_micro / 1_000_000.0)

                    state = TrackState(
                        status=raw_status,
                        title=title,
                        artist=artist,
                        album=album,
                        position=position_sec,
                        duration=duration_sec,
                        art_url=art_url,
                        track_url=track_url,
                        source="spotify",
                        source_display="Spotify"
                    )

                    if raw_status == "Playing":
                        self._active_linux_bus = b_name
                        return state
                    elif not paused_cand:
                        paused_cand = (b_name, state)
                except Exception:
                    continue

            if paused_cand:
                self._active_linux_bus = paused_cand[0]
                return paused_cand[1]

        except Exception as e:
            logger.debug("Ошибка опроса веб-версии Spotify Linux: %s", e)

        return None

    def _get_state_windows(self) -> Optional[TrackState]:
        import asyncio
        try:
            return asyncio.run(asyncio.wait_for(self._async_windows_state(), timeout=2.0))
        except BaseException:
            return None

    async def _async_windows_state(self) -> Optional[TrackState]:
        from .win_smtc import WinSMTCHelper, PlaybackStatus
        if not WinSMTCHelper.is_available():
            return None

        sessions = await WinSMTCHelper.get_sessions()
        matched = None

        # 1. Поиск нативного клиента Spotify
        for s in sessions:
            try:
                app_id = (s.source_app_user_model_id or "").lower()
                if any(h in app_id for h in self.hints):
                    info = s.get_playback_info()
                    if info and info.playback_status == PlaybackStatus.PLAYING:
                        matched = s
                        break
            except Exception:
                continue

        if not matched:
            for s in sessions:
                try:
                    app_id = (s.source_app_user_model_id or "").lower()
                    if any(h in app_id for h in self.hints):
                        matched = s
                        break
                except Exception:
                    continue

        # 2. Если нативный клиент не найден, проверяем браузерные сессии (Spotify Web)
        if not matched:
            for s in sessions:
                try:
                    app_id = (s.source_app_user_model_id or "").lower()
                    if any(b in app_id for b in self.browser_hints):
                        props = await s.try_get_media_properties_async()
                        if not props:
                            continue
                        t = (props.title or "").lower()
                        a = (props.artist or "").lower()
                        al = (props.album_title or "").lower()
                        if "spotify" in t or "spotify" in a or "spotify" in al:
                            matched = s
                            info = s.get_playback_info()
                            if info and info.playback_status == PlaybackStatus.PLAYING:
                                break
                except Exception:
                    continue

        if not matched:
            return None

        try:
            playback = matched.get_playback_info()
            if not playback:
                return None

            p_status = playback.playback_status
            if p_status == PlaybackStatus.PLAYING:
                status = "Playing"
            elif p_status == PlaybackStatus.PAUSED:
                status = "Paused"
            else:
                status = "Stopped"

            media_props = await matched.try_get_media_properties_async()
            raw_title = (media_props.title or "").strip() if media_props else ""
            raw_artist = (media_props.artist or "").strip() if media_props else ""
            album = (media_props.album_title or "").strip() if media_props else ""

            artist, title = self._clean_spotify_title(raw_title, raw_artist)

            timeline = matched.get_timeline_properties()
            pos = 0.0
            dur = 0.0
            if timeline:
                if timeline.position:
                    pos = max(0.0, timeline.position.total_seconds())
                if timeline.end_time:
                    dur = max(0.0, timeline.end_time.total_seconds())

            return TrackState(
                status=status,
                title=title,
                artist=artist,
                album=album,
                position=pos,
                duration=dur,
                art_url="",
                track_url="",
                source="spotify",
                source_display="Spotify"
            )
        except Exception:
            return None

    def control_media(self, action: str) -> bool:
        if sys.platform == "win32":
            return self._control_windows(action)
        return self._control_linux(action)

    def _control_linux(self, action: str) -> bool:
        if not self.bus:
            return False
        try:
            bus_name = self._active_linux_bus
            if not bus_name:
                for name in self.bus.list_names():
                    if name == "org.mpris.MediaPlayer2.spotify" or (name.startswith("org.mpris.MediaPlayer2.") and "spotify" in name.lower()):
                        bus_name = name
                        break

            if bus_name:
                obj = self.bus.get_object(bus_name, "/org/mpris/MediaPlayer2")
                player = dbus.Interface(obj, "org.mpris.MediaPlayer2.Player")
                act = action.lower()
                if act in ("playpause", "toggle", "play_pause", "pause", "play"):
                    player.PlayPause()
                elif act in ("next", "skip"):
                    player.Next()
                elif act in ("previous", "prev"):
                    player.Previous()
                return True
        except Exception as e:
            logger.debug("Ошибка управления Spotify Linux: %s", e)
        return False

    def _control_windows(self, action: str) -> bool:
        import asyncio
        async def _act():
            from .win_smtc import WinSMTCHelper
            if not WinSMTCHelper.is_available():
                return False
            sessions = await WinSMTCHelper.get_sessions()
            target = None
            for s in sessions:
                try:
                    app_id = (s.source_app_user_model_id or "").lower()
                    if any(h in app_id for h in self.hints) or any(b in app_id for b in self.browser_hints):
                        target = s
                        break
                except Exception:
                    continue

            if target:
                act = action.lower()
                if act in ("playpause", "toggle", "play_pause", "pause", "play"):
                    await target.try_toggle_play_pause_async()
                elif act in ("next", "skip"):
                    await target.try_skip_next_async()
                elif act in ("previous", "prev"):
                    await target.try_skip_previous_async()
                return True
            return False
        try:
            return asyncio.run(asyncio.wait_for(_act(), timeout=2.0))
        except Exception:
            return False
