"""
Мониторинг воспроизведения Spotify (Linux MPRIS и Windows SMTC).
Работает локально с плеером — никакой VPN не требуется!
"""

import sys
import logging
from typing import Optional, List
from .base import BasePlayerWatcher, TrackState

logger = logging.getLogger("MusicRPC.Spotify")

if sys.platform != "win32":
    try:
        import dbus
    except ImportError:
        dbus = None
else:
    dbus = None


class SpotifyWatcher(BasePlayerWatcher):
    """Мониторинг плеера Spotify без VPN."""

    def __init__(self, hints: Optional[List[str]] = None):
        self.hints = [h.lower() for h in (hints or ["spotify"])]
        self.bus = dbus.SessionBus() if dbus else None

    def get_state(self) -> Optional[TrackState]:
        if sys.platform == "win32":
            return self._get_state_windows()
        else:
            return self._get_state_linux()

    def _get_state_linux(self) -> Optional[TrackState]:
        if not self.bus:
            return None

        spotify_bus_name = None
        try:
            for name in self.bus.list_names():
                if name == "org.mpris.MediaPlayer2.spotify" or (name.startswith("org.mpris.MediaPlayer2.") and "spotify" in name.lower()):
                    spotify_bus_name = name
                    break
        except Exception:
            return None

        if not spotify_bus_name:
            return None

        try:
            obj = self.bus.get_object(spotify_bus_name, "/org/mpris/MediaPlayer2")
            props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")

            raw_status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
            if raw_status not in ("Playing", "Paused"):
                return TrackState(
                    status="Stopped",
                    title="",
                    artist="",
                    source="spotify",
                    source_display="Spotify"
                )

            metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")

            title = str(metadata.get("xesam:title", "")).strip()

            artists = metadata.get("xesam:artist", "")
            if isinstance(artists, (list, tuple, dbus.Array)):
                artist = ", ".join(str(a) for a in artists if str(a).strip()).strip()
            else:
                artist = str(artists).strip()

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

            return TrackState(
                status=raw_status,
                title=title or "Трек Spotify",
                artist=artist or "Spotify",
                album=album,
                position=position_sec,
                duration=duration_sec,
                art_url=art_url,
                track_url=track_url,
                source="spotify",
                source_display="Spotify"
            )
        except Exception as e:
            logger.debug("Ошибка получения состояния Spotify на Linux: %s", e)
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
            title = (media_props.title or "").strip() if media_props else ""
            artist = (media_props.artist or "").strip() if media_props else ""
            album = (media_props.album_title or "").strip() if media_props else ""

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
                title=title or "Spotify",
                artist=artist or "Spotify",
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
            for name in self.bus.list_names():
                if name == "org.mpris.MediaPlayer2.spotify" or (name.startswith("org.mpris.MediaPlayer2.") and "spotify" in name.lower()):
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
            logger.debug("Ошибка управления Spotify Linux: %s", e)
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
