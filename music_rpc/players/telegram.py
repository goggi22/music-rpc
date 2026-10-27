"""
Мониторинг воспроизведения Telegram (AyuGram, официальный клиент, Kotatogram, 64Gram).
"""

import sys
import logging
from typing import Optional, List
from .base import BasePlayerWatcher, TrackState
from ..core.cleaner import clean_text, split_artist_title
from ..core.artist_finder import ArtistFinder

logger = logging.getLogger("MusicRPC.Telegram")

if sys.platform != "win32":
    try:
        import dbus
    except ImportError:
        dbus = None
else:
    dbus = None


class TelegramWatcher(BasePlayerWatcher):
    """Мониторинг плеера Telegram на Linux и Windows."""

    def __init__(self, hints: Optional[List[str]] = None, artist_finder: Optional[ArtistFinder] = None, auto_detect: bool = True):
        self.hints = [h.lower() for h in (hints or ["telegram", "ayugram", "tdesktop", "64gram", "kotatogram"])]
        self.artist_finder = artist_finder or ArtistFinder()
        self.auto_detect = auto_detect
        self.bus = dbus.SessionBus() if dbus else None

    def _clean_track(self, raw_artist: str, raw_title: str) -> tuple:
        artist, title = clean_text(raw_title, raw_artist)

        generic_artists = ('', 'telegram', 'unknown', 'неизвестный исполнитель', 'аудиозапись')
        if artist.lower() in generic_artists:
            # 1. Сплит "Исполнитель - Трек"
            split_art, split_tit = split_artist_title(title)
            if split_art and split_tit:
                artist = split_art
                title = split_tit
            elif self.auto_detect and self.artist_finder:
                # 2. Сетевой поиск автора через SoundCloud/Deezer
                found_art, found_tit = self.artist_finder.resolve(title)
                if found_art:
                    artist = found_art
                    if found_tit:
                        title = found_tit

        artist = artist.strip() or "Telegram"
        title = title.strip() or "Аудиозапись"
        return artist, title

    def get_state(self) -> Optional[TrackState]:
        if sys.platform == "win32":
            return self._get_state_windows()
        else:
            return self._get_state_linux()

    def _get_state_linux(self) -> Optional[TrackState]:
        if not self.bus:
            return None

        matched_names = []
        try:
            for name in self.bus.list_names():
                if name.startswith("org.mpris.MediaPlayer2."):
                    lower = name.lower()
                    if any(h in lower for h in self.hints):
                        matched_names.append(name)
        except Exception:
            return None

        if not matched_names:
            return None

        # Ищем играющий плеер
        target_bus = None
        for name in matched_names:
            try:
                obj = self.bus.get_object(name, "/org/mpris/MediaPlayer2")
                props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                st = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
                if st == "Playing":
                    target_bus = name
                    break
            except Exception:
                continue

        if not target_bus:
            target_bus = matched_names[0]

        try:
            obj = self.bus.get_object(target_bus, "/org/mpris/MediaPlayer2")
            props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")

            raw_status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
            if raw_status not in ("Playing", "Paused"):
                return TrackState(status="Stopped", title="", artist="", source="telegram", source_display="Telegram")

            metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
            raw_title = str(metadata.get("xesam:title", "")).strip()

            artists = metadata.get("xesam:artist", "")
            if isinstance(artists, (list, tuple, dbus.Array)):
                raw_artist = ", ".join(str(a) for a in artists if str(a).strip()).strip()
            else:
                raw_artist = str(artists).strip()

            album = str(metadata.get("xesam:album", "")).strip()
            art_url = str(metadata.get("mpris:artUrl", "")).strip()

            try:
                pos_micro = int(props.Get("org.mpris.MediaPlayer2.Player", "Position"))
                position_sec = max(0.0, pos_micro / 1_000_000.0)
            except Exception:
                position_sec = 0.0

            length_micro = int(metadata.get("mpris:length", 0))
            duration_sec = max(0.0, length_micro / 1_000_000.0)

            artist, title = self._clean_track(raw_artist, raw_title)

            return TrackState(
                status=raw_status,
                title=title,
                artist=artist,
                album=album,
                position=position_sec,
                duration=duration_sec,
                art_url=art_url,
                source="telegram",
                source_display="Telegram"
            )
        except Exception:
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

            artist, title = self._clean_track(raw_artist, raw_title)

            return TrackState(
                status=status,
                title=title,
                artist=artist,
                album=album,
                position=pos,
                duration=dur,
                art_url="",
                source="telegram",
                source_display="Telegram"
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
            for name in self.bus.list_names():
                if name.startswith("org.mpris.MediaPlayer2.") and any(h in name.lower() for h in self.hints):
                    obj = self.bus.get_object(name, "/org/mpris/MediaPlayer2")
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
            logger.debug("Ошибка управления Telegram Linux: %s", e)
        return False

    def _control_windows(self, action: str) -> bool:
        import asyncio
        async def _act():
            from .win_smtc import WinSMTCHelper
            if not WinSMTCHelper.is_available():
                return False
            sessions = await WinSMTCHelper.get_sessions()
            for s in sessions:
                try:
                    app_id = (s.source_app_user_model_id or "").lower()
                    if any(h in app_id for h in self.hints):
                        act = action.lower()
                        if act in ("playpause", "toggle", "play_pause", "pause", "play"):
                            await s.try_toggle_play_pause_async()
                        elif act in ("next", "skip"):
                            await s.try_skip_next_async()
                        elif act in ("previous", "prev"):
                            await s.try_skip_previous_async()
                        return True
                except Exception:
                    continue
            return False
        try:
            return asyncio.run(asyncio.wait_for(_act(), timeout=2.0))
        except Exception:
            return False
