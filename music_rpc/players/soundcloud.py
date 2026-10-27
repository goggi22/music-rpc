"""
Мониторинг воспроизведения SoundCloud из браузеров (Chrome, Edge, Firefox, Brave, Opera и др.)
через стандартные системные медиа-сессии (MPRIS на Linux, SMTC на Windows).
"""

import sys
import re
import logging
from typing import Optional, List
from .base import BasePlayerWatcher, TrackState
from ..core.cleaner import clean_text, split_artist_title

logger = logging.getLogger("MusicRPC.SoundCloud")

if sys.platform != "win32":
    try:
        import dbus
    except ImportError:
        dbus = None
else:
    dbus = None


class SoundCloudWatcher(BasePlayerWatcher):
    """Мониторинг воспроизведения SoundCloud из веб-браузеров."""

    def __init__(self, browser_hints: Optional[List[str]] = None):
        self.browser_hints = [b.lower() for b in (browser_hints or [
            "chrome", "msedge", "firefox", "brave", "opera", "vivaldi", "yandex", "chromium"
        ])]
        self.bus = dbus.SessionBus() if dbus else None

    @staticmethod
    def _parse_soundcloud_title(raw_title: str, raw_artist: str) -> tuple:
        title = raw_title.strip()
        artist = raw_artist.strip()

        # Если в конце названия браузер приписал " - SoundCloud" или "on SoundCloud"
        title = re.sub(r'[\s\-|–—]+SoundCloud.*$', '', title, flags=re.IGNORECASE).strip()

        # Формат вкладки SoundCloud: "Stream <Title> by <Artist>"
        m = re.match(r'^Stream\s+(.+?)\s+by\s+(.+)$', title, flags=re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            if not artist or artist.lower() == "soundcloud":
                artist = m.group(2).strip()

        # Если автор пуст, пробуем разделить "Исполнитель - Трек"
        if not artist or artist.lower() in ("soundcloud", "unknown", ""):
            split_art, split_tit = split_artist_title(title)
            if split_art and split_tit:
                artist = split_art
                title = split_tit

        artist, title = clean_text(title, artist)
        return artist or "SoundCloud", title or "Аудиозапись"

    def get_state(self) -> Optional[TrackState]:
        if sys.platform == "win32":
            return self._get_state_windows()
        else:
            return self._get_state_linux()

    def _get_state_linux(self) -> Optional[TrackState]:
        if not self.bus:
            return None

        matched_buses = []
        try:
            for name in self.bus.list_names():
                if name.startswith("org.mpris.MediaPlayer2."):
                    lower = name.lower()
                    if any(b in lower for b in self.browser_hints):
                        matched_buses.append(name)
        except Exception:
            return None

        if not matched_buses:
            return None

        # Проверяем активные браузерные сессии
        candidates = []
        for b_name in matched_buses:
            try:
                obj = self.bus.get_object(b_name, "/org/mpris/MediaPlayer2")
                props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                st = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
                metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
                url = str(metadata.get("xesam:url", "")).lower()
                title = str(metadata.get("xesam:title", "")).lower()

                # Проверяем, связано ли это с SoundCloud
                is_sc = "soundcloud" in url or "soundcloud" in title or "stream " in title
                candidates.append((b_name, st, is_sc, props, metadata))
            except Exception:
                continue

        if not candidates:
            return None

        # Приоритет: сессии SoundCloud с Playing, затем любые сессии SoundCloud, затем любые играющие
        target = None
        for b_name, st, is_sc, props, metadata in candidates:
            if is_sc and st == "Playing":
                target = (st, props, metadata)
                break

        if not target:
            for b_name, st, is_sc, props, metadata in candidates:
                if is_sc:
                    target = (st, props, metadata)
                    break

        if not target:
            for b_name, st, is_sc, props, metadata in candidates:
                if st == "Playing":
                    target = (st, props, metadata)
                    break

        if not target and candidates:
            target = (candidates[0][1], candidates[0][3], candidates[0][4])

        if not target:
            return None

        raw_status, props, metadata = target
        if raw_status not in ("Playing", "Paused"):
            return TrackState(status="Stopped", title="", artist="", source="soundcloud", source_display="SoundCloud")

        try:
            raw_title = str(metadata.get("xesam:title", "")).strip()

            artists = metadata.get("xesam:artist", "")
            if isinstance(artists, (list, tuple, dbus.Array)):
                raw_artist = ", ".join(str(a) for a in artists if str(a).strip()).strip()
            else:
                raw_artist = str(artists).strip()

            album = str(metadata.get("xesam:album", "")).strip()
            art_url = str(metadata.get("mpris:artUrl", "")).strip()
            track_url = str(metadata.get("xesam:url", "")).strip()

            try:
                pos_micro = int(props.Get("org.mpris.MediaPlayer2.Player", "Position"))
                pos = max(0.0, pos_micro / 1_000_000.0)
            except Exception:
                pos = 0.0

            length_micro = int(metadata.get("mpris:length", 0))
            dur = max(0.0, length_micro / 1_000_000.0)

            artist, title = self._parse_soundcloud_title(raw_title, raw_artist)

            return TrackState(
                status=raw_status,
                title=title,
                artist=artist,
                album=album,
                position=pos,
                duration=dur,
                art_url=art_url,
                track_url=track_url,
                source="soundcloud",
                source_display="SoundCloud"
            )
        except Exception:
            return None

    def _get_state_windows(self) -> Optional[TrackState]:
        import asyncio
        try:
            return asyncio.run(asyncio.wait_for(self._async_windows_state(), timeout=2.0))
        except Exception:
            return None

    async def _async_windows_state(self) -> Optional[TrackState]:
        from .win_smtc import WinSMTCHelper, PlaybackStatus
        if not WinSMTCHelper.is_available():
            return None

        sessions = await WinSMTCHelper.get_sessions()
        matched = None

        # Ищем браузерные сессии
        for s in sessions:
            try:
                app_id = (s.source_app_user_model_id or "").lower()
                if any(b in app_id for b in self.browser_hints):
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
                    if any(b in app_id for b in self.browser_hints):
                        matched = s
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

            timeline = matched.get_timeline_properties()
            pos = 0.0
            dur = 0.0
            if timeline:
                if timeline.position:
                    pos = max(0.0, timeline.position.total_seconds())
                if timeline.end_time:
                    dur = max(0.0, timeline.end_time.total_seconds())

            artist, title = self._parse_soundcloud_title(raw_title, raw_artist)

            return TrackState(
                status=status,
                title=title,
                artist=artist,
                album=album,
                position=pos,
                duration=dur,
                art_url="",
                track_url="",
                source="soundcloud",
                source_display="SoundCloud"
            )
        except Exception:
            return None
