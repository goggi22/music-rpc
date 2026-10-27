"""
Мониторинг воспроизведения Telegram (AyuGram, официальный клиент, Kotatogram, 64Gram).
Включает интеллектуальную фильтрацию не-музыкального контента (голосовые сообщения, кружочки, видеоролики).
"""

import sys
import re
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

# Шаблоны дат и времени в заголовках голосовых сообщений (например: "сегодня в 20:55", "today at 14:30")
VOICE_DATE_PATTERNS = [
    r'^(?:сегодня|вчера|today|yesterday)\s+(?:в|at|um|à)\s+\d{1,2}:\d{2}',
    r'^\d{1,2}\s+(?:янв|фев|мар|апр|ма[йя]|июн|июл|авг|сен|окт|ноя|дек)[а-я]*\s+(?:в|at|um|à|,)?\s*\d{1,2}:\d{2}',
    r'^\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(?:в|at|um|à|,)?\s*\d{1,2}:\d{2}',
    r'^\d{1,2}[./\-]\d{1,2}(?:[./\-]\d{2,4})?(?:,?\s*(?:в|at|um|à|\s)\s*|\s+)\d{1,2}:\d{2}(?:\s*[ap]m)?',
    r'^\d{1,2}:\d{2}(?:\s*[ap]m)?$'
]

# Ключевые слова голосовых и видеосообщений
VOICE_WORDS = (
    'голосовое сообщение', 'аудиосообщение', 'голосовое',
    'voice message', 'voice note', 'audio message',
    'видеосообщение', 'video message', 'кружочек', 'round video',
    'голосове повідомлення', 'аудіоповідомлення', 'відеоповідомлення', 'кружечок',
    'sprachnachricht', 'videonachricht', 'message vocal', 'mensaje de voz'
)

# Расширения видеофайлов
VIDEO_EXTENSIONS = (
    '.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv',
    '.3gp', '.m4v', '.ts', '.gif', '.asf', '.vob', '.ogv'
)

# Расширения аудиофайлов
AUDIO_EXTENSIONS = (
    '.mp3', '.flac', '.wav', '.m4a', '.aac', '.alac', '.ogg',
    '.opus', '.wma', '.mid', '.midi'
)

# Дефолтные заполнители исполнителя
GENERIC_ARTISTS = {
    '', 'telegram', 'unknown', 'неизвестный', 'неизвестный исполнитель',
    'вы', 'you', 'аудиозапись', 'аудио', 'audio', 'избранное',
    'saved messages', 'saved_messages'
}


class TelegramWatcher(BasePlayerWatcher):
    """Мониторинг плеера Telegram на Linux и Windows."""

    def __init__(
        self,
        hints: Optional[List[str]] = None,
        artist_finder: Optional[ArtistFinder] = None,
        auto_detect: bool = True,
        filter_non_music: bool = True,
        min_duration: float = 12.0
    ):
        self.hints = [h.lower() for h in (hints or ["telegram", "ayugram", "tdesktop", "64gram", "kotatogram", "exteragram"])]
        self.artist_finder = artist_finder or ArtistFinder()
        self.auto_detect = auto_detect
        self.filter_non_music = filter_non_music
        self.min_duration = min_duration
        self.bus = dbus.SessionBus() if dbus else None

    def is_telegram_music(self, title: str, artist: str = "", duration: float = 0.0) -> bool:
        """
        Проверяет, является ли воспроизводимый медиафайл настоящим музыкальным треком,
        а не голосовым сообщением, видеосообщением (кружочком) или видеороликом.
        """
        if not self.filter_non_music:
            return True

        t = title.strip().lower()
        a = artist.strip().lower()

        if not t:
            return False

        # 1. Проверка на голосовые по дате/времени ('сегодня в 20:55', 'today at 14:30', '27.10.2026 в 20:55')
        for pat in VOICE_DATE_PATTERNS:
            if re.search(pat, t, flags=re.IGNORECASE):
                return False

        # 2. Ключевые слова голосовых и видеосообщений в названии или исполнителе
        for word in VOICE_WORDS:
            if word in t or (a and word in a):
                return False

        # 3. Видеофайлы по расширению
        if any(t.endswith(ext) or a.endswith(ext) for ext in VIDEO_EXTENSIONS):
            return False

        # 4. Видеофайлы по системным префиксам (VID_20261027, MOV_1234, video_...)
        if re.match(r'^(?:vid|video|mov|file|screen|rec|recording|cam|dvr|clip)[\s_\-\d]+(?:\.[a-z0-9]+)?$', t):
            return False

        # 5. Системные имена голосовых сообщений (audio_2026-..., voice-message, ptt-...)
        if re.match(r'^(?:audio|voice|ptt|sound)[\s_\-\d]+(?:\.[a-z0-9]+)?$', t):
            return False

        # 6. Если длительность меньше порога (голосовые/короткие звуки)
        if 0 < duration < self.min_duration:
            has_audio_ext = any(t.endswith(ext) for ext in AUDIO_EXTENSIONS)
            has_real_artist = bool(a and a not in GENERIC_ARTISTS)
            if not (has_audio_ext and has_real_artist):
                return False

        # 7. Если явно указано музыкальное расширение (.mp3, .flac, .m4a и т.д.)
        if any(t.endswith(ext) for ext in AUDIO_EXTENSIONS):
            return True

        # 8. Если указан реальный исполнитель (не дефолтный Telegram/Вы/Unknown)
        if a and a not in GENERIC_ARTISTS:
            return True

        # 9. Если в названии трека есть разделитель автора и названия ('Исполнитель - Трек')
        if ' - ' in title or ' – ' in title or ' — ' in title:
            return True

        # 10. Если трек длится дольше 30 секунд и не похож на видео/голосовое
        if duration >= 30.0:
            return True

        return False

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

        candidate_states: List[TrackState] = []
        for name in matched_names:
            try:
                obj = self.bus.get_object(name, "/org/mpris/MediaPlayer2")
                props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")

                raw_status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
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

                # Фильтрация голосовых, видеосообщений и видеофайлов
                if self.filter_non_music and not self.is_telegram_music(raw_title, raw_artist, duration_sec):
                    logger.debug("Telegram MPRIS медиа '%s' отфильтровано (не музыка)", raw_title)
                    continue

                if raw_status not in ("Playing", "Paused"):
                    continue

                artist, title = self._clean_track(raw_artist, raw_title)

                state = TrackState(
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
                candidate_states.append(state)
            except Exception:
                continue

        if not candidate_states:
            return TrackState(status="Stopped", title="", artist="", source="telegram", source_display="Telegram")

        # Отдаем играющий плеер, либо на паузе
        for st in candidate_states:
            if st.status == "Playing":
                return st
        for st in candidate_states:
            if st.status == "Paused":
                return st
        return candidate_states[0]

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
        candidate_states: List[TrackState] = []

        for s in sessions:
            try:
                app_id = (s.source_app_user_model_id or "").lower()
                if not any(h in app_id for h in self.hints):
                    continue

                playback = s.get_playback_info()
                if not playback:
                    continue

                p_status = playback.playback_status
                if p_status == PlaybackStatus.PLAYING:
                    status = "Playing"
                elif p_status == PlaybackStatus.PAUSED:
                    status = "Paused"
                else:
                    continue

                media_props = await s.try_get_media_properties_async()
                raw_title = (media_props.title or "").strip() if media_props else ""
                raw_artist = (media_props.artist or "").strip() if media_props else ""
                album = (media_props.album_title or "").strip() if media_props else ""

                timeline = s.get_timeline_properties()
                pos = 0.0
                dur = 0.0
                if timeline:
                    if timeline.position:
                        pos = max(0.0, timeline.position.total_seconds())
                    if timeline.end_time:
                        dur = max(0.0, timeline.end_time.total_seconds())

                # Фильтрация голосовых сообщений, видео и кружочков
                if self.filter_non_music and not self.is_telegram_music(raw_title, raw_artist, dur):
                    logger.debug("Telegram SMTC медиа '%s' отфильтровано (не музыка)", raw_title)
                    continue

                artist, title = self._clean_track(raw_artist, raw_title)

                state = TrackState(
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
                candidate_states.append(state)
            except Exception:
                continue

        if not candidate_states:
            return TrackState(status="Stopped", title="", artist="", source="telegram", source_display="Telegram")

        for st in candidate_states:
            if st.status == "Playing":
                return st
        for st in candidate_states:
            if st.status == "Paused":
                return st
        return candidate_states[0]

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
