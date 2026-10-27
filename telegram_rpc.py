#!/usr/bin/env python3
"""
Telegram Discord Rich Presence (RPC)
Отображает текущую музыку из Telegram (AyuGram, официальный Telegram Desktop и др.)
в статусе Discord в стиле Spotify:
- Автор без предлога "от"
- Без третьей строчки (без альбома)
- Маленькая иконка с подсказкой "in Telegram"
- 100% поиск обложек через SoundCloud, Deezer, iTunes и YouTube
- Автоматический поиск и определение автора трека, если автор не указан в тегах.
"""

import os
import sys
import time
import json
import socket
import struct
import signal
import urllib.request
import urllib.parse
import re
import logging
from typing import Optional, Dict, Any, Tuple

try:
    import dbus
except ImportError:
    print("Ошибка: не найден модуль dbus-python. Установите python-dbus / dbus-python.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("TelegramRPC")

DEFAULT_CONFIG: Dict[str, Any] = {
    # Discord Client ID
    "client_id": "1262937085635985409",
    # Тип активности: 2 = Listening ("Слушает <Автор>"), 5 = Competing ("Competing in Telegram")
    "activity_type": 2,
    # Отображать имя автора в заголовке активности ("Слушает <Автор>")
    "show_author_as_activity_name": True,
    # Формат второй строки (state) — без предлога "от"
    "state_format": "{artist}",
    # Автоматически определять автора через сеть, если автор не указан
    "auto_detect_missing_artist": True,
    # Автопоиск обложек
    "search_covers": True,
    # Поведение при паузе
    "show_paused": True,
    # Кнопка поиска
    "show_button": True,
    "button_label": "🔍 Найти трек",
    # Текст маленькой иконки
    "small_text_label": "in Telegram",
    # Интервал проверки (сек)
    "poll_interval_seconds": 1.0,
    # Обложка по умолчанию
    "fallback_cover": "https://cdn.discordapp.com/app-assets/1262937085635985409/1262949949071691818.png",
    # Поддерживаемые клиенты Telegram
    "player_name_hints": [
        "telegram",
        "ayugram",
        "tdesktop",
        "64gram",
        "kotatogram",
        "exteragram"
    ]
}


class ArtistFinder:
    """Сервис автоматического определения исполнителя, если он отсутствует в тегах Telegram."""

    SOUNDCLOUD_CLIENT_ID = "bQmaW4vAHmJIUxisgjRG4MAWAiDgsk9D"

    def __init__(self):
        self.cache: Dict[str, Tuple[str, str]] = {}

    def resolve(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        cache_key = title.lower().strip()
        if cache_key in self.cache:
            return self.cache[cache_key]

        search_query = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title)
        search_query = re.sub(r'[\s_]+eq\s*[\d\-_]*', '', search_query, flags=re.IGNORECASE).strip() or title

        # 1. Поиск в SoundCloud (отлично подходит для музыки из Telegram и андерграунда)
        try:
            url = (
                f"https://api-v2.soundcloud.com/search/tracks"
                f"?q={urllib.parse.quote(search_query)}"
                f"&client_id={self.SOUNDCLOUD_CLIENT_ID}&limit=5"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("collection", []):
                    t_title = item.get("title", "").strip()
                    t_user = item.get("user", {}).get("username", "").strip()

                    # Проверяем, есть ли "Исполнитель - Трек" в названии на SoundCloud
                    for sep in (" - ", " – ", " — "):
                        if sep in t_title:
                            parts = t_title.split(sep, 1)
                            if parts[0].strip() and parts[1].strip():
                                res = (parts[0].strip(), parts[1].strip())
                                self.cache[cache_key] = res
                                logger.info("🔎 Автор не был указан. Автоматически найден исполнитель: '%s' для трека '%s' (SoundCloud)", res[0], res[1])
                                return res

                    # Если название совпадает, берем автора аккаунта SoundCloud
                    if search_query.lower() in t_title.lower() or t_title.lower() in search_query.lower():
                        if t_user:
                            res = (t_user.strip(), search_query)
                            self.cache[cache_key] = res
                            logger.info("🔎 Автор не был указан. Автоматически найден исполнитель: '%s' для трека '%s' (SoundCloud)", res[0], res[1])
                            return res
        except Exception:
            pass

        # 2. Поиск в Deezer
        try:
            url = f"https://api.deezer.com/search?q={urllib.parse.quote(search_query)}&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("data"):
                    item = data["data"][0]
                    d_title = item.get("title", "").lower()
                    if search_query.lower() in d_title or d_title in search_query.lower():
                        res = (item["artist"]["name"].strip(), item["title"].strip())
                        self.cache[cache_key] = res
                        logger.info("🔎 Автор не был указан. Автоматически найден исполнитель: '%s' для трека '%s' (Deezer)", res[0], res[1])
                        return res
        except Exception:
            pass

        # 3. Поиск в iTunes
        try:
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(search_query)}&entity=song&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("resultCount", 0) > 0:
                    item = data["results"][0]
                    it_title = item.get("trackName", "").lower()
                    if search_query.lower() in it_title or it_title in search_query.lower():
                        res = (item.get("artistName", "").strip(), item.get("trackName", "").strip())
                        self.cache[cache_key] = res
                        logger.info("🔎 Автор не был указан. Автоматически найден исполнитель: '%s' для трека '%s' (iTunes)", res[0], res[1])
                        return res
        except Exception:
            pass

        self.cache[cache_key] = (None, None)
        return None, None


class CoverFinder:
    """
    Многоуровневый поисковик обложек с кэшированием:
    1. Deezer API (официальные HD квадратные обложки 500x500/1000x1000)
    2. SoundCloud API (андерграунд, ремиксы, треки из тг-каналов, 500x500)
    3. iTunes Search API (официальные обложки 512x512)
    4. YouTube Search (находит 100% треков, если в каталогах нет)
    """

    SOUNDCLOUD_CLIENT_ID = "bQmaW4vAHmJIUxisgjRG4MAWAiDgsk9D"

    def __init__(self, fallback_url: str):
        self.fallback_url = fallback_url
        self.cache: Dict[str, str] = {}
        self.max_cache_size = 500

    @staticmethod
    def _clean_for_search(text: str) -> str:
        text = re.sub(r'[\(\[\{].*?[\)\]\}]', '', text)
        return text.strip()

    def _search_deezer(self, query: str) -> Optional[str]:
        try:
            url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("data"):
                    track = data["data"][0]
                    return track.get("album", {}).get("cover_big") or track.get("album", {}).get("cover_medium")
        except Exception:
            pass
        return None

    def _search_soundcloud(self, query: str) -> Optional[str]:
        try:
            url = (
                f"https://api-v2.soundcloud.com/search/tracks"
                f"?q={urllib.parse.quote(query)}"
                f"&client_id={self.SOUNDCLOUD_CLIENT_ID}&limit=3"
            )
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for t in data.get("collection", []):
                    art = t.get("artwork_url") or t.get("user", {}).get("avatar_url")
                    if art:
                        art = art.replace("-large.", "-t500x500.")
                        return art
        except Exception:
            pass
        return None

    def _search_itunes(self, query: str) -> Optional[str]:
        try:
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("resultCount", 0) > 0:
                    artwork = data["results"][0].get("artworkUrl100", "")
                    if artwork:
                        return artwork.replace("100x100bb", "512x512bb")
        except Exception:
            pass
        return None

    def _search_youtube(self, query: str) -> Optional[str]:
        try:
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                match = re.search(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
                if match:
                    vid = match.group(1)
                    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        except Exception:
            pass
        return None

    def get_cover(self, artist: str, title: str) -> str:
        cache_key = f"{artist.lower().strip()}|{title.lower().strip()}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        first_artist = re.split(r'[,/&]|feat\.|ft\.', artist, flags=re.IGNORECASE)[0].strip()
        clean_title = self._clean_for_search(title) or title

        queries = [
            f"{artist} {clean_title}",
            f"{first_artist} {clean_title}",
            f"{artist} {title}",
            f"{clean_title}"
        ]

        cover_url = None
        seen = set()

        for q in queries:
            q = q.strip()
            if not q or q in seen:
                continue
            seen.add(q)

            # 1. Deezer
            cover_url = self._search_deezer(q)
            if cover_url:
                break

            # 2. SoundCloud
            cover_url = self._search_soundcloud(q)
            if cover_url:
                break

            # 3. iTunes
            cover_url = self._search_itunes(q)
            if cover_url:
                break

        # 4. YouTube
        if not cover_url:
            for q in queries:
                q = q.strip()
                if not q:
                    continue
                cover_url = self._search_youtube(q)
                if cover_url:
                    break

        final_cover = cover_url or self.fallback_url
        if len(self.cache) >= self.max_cache_size:
            self.cache.pop(next(iter(self.cache)))
        self.cache[cache_key] = final_cover
        return final_cover


class DiscordIPC:
    """Низкоуровневый клиент Discord Rich Presence через Unix Domain Socket."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.last_connect_attempt = 0.0

    def _find_ipc_path(self) -> Optional[str]:
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        candidates = [
            f"{runtime_dir}/discord-ipc-{i}" for i in range(10)
        ] + [
            f"/tmp/discord-ipc-{i}" for i in range(10)
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def connect(self) -> bool:
        if self.connected:
            return True

        now = time.time()
        if now - self.last_connect_attempt < 3.0:
            return False
        self.last_connect_attempt = now

        ipc_path = self._find_ipc_path()
        if not ipc_path:
            return False

        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(3.0)
            self.sock.connect(ipc_path)

            handshake = json.dumps({"v": 1, "client_id": self.client_id}).encode("utf-8")
            self.sock.sendall(struct.pack("<II", 0, len(handshake)) + handshake)

            hdr = self.sock.recv(8)
            if not hdr:
                self.disconnect()
                return False

            op, length = struct.unpack("<II", hdr)
            data = b""
            while len(data) < length:
                chunk = self.sock.recv(min(length - len(data), 4096))
                if not chunk:
                    break
                data += chunk

            resp = json.loads(data.decode("utf-8"))
            if resp.get("evt") == "READY":
                self.connected = True
                user = resp.get("data", {}).get("user", {})
                username = user.get("global_name") or user.get("username")
                logger.info("Подключено к Discord (пользователь: %s)", username)
                return True
            else:
                self.disconnect()
                return False
        except Exception as e:
            self.disconnect()
            return False

    def disconnect(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def send_frame(self, op: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.connected:
            if not self.connect():
                return None

        try:
            raw = json.dumps(data).encode("utf-8")
            self.sock.sendall(struct.pack("<II", op, len(raw)) + raw)

            hdr = self.sock.recv(8)
            if not hdr:
                self.disconnect()
                return None
            op_resp, length = struct.unpack("<II", hdr)
            buf = b""
            while len(buf) < length:
                chunk = self.sock.recv(min(length - len(buf), 4096))
                if not chunk:
                    break
                buf += chunk
            return json.loads(buf.decode("utf-8"))
        except Exception as e:
            logger.warning("Ошибка связи с Discord IPC: %s", e)
            self.disconnect()
            return None

    def set_activity(self, activity: Optional[Dict[str, Any]]) -> bool:
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {
                "pid": os.getpid(),
                "activity": activity
            },
            "nonce": str(time.time())
        }
        resp = self.send_frame(1, payload)
        return resp is not None and resp.get("evt") != "ERROR"

    def clear_activity(self) -> bool:
        return self.set_activity(None)


def sanitize_str(s: str, min_len: int = 2, max_len: int = 128) -> str:
    s = s.strip()
    if len(s) < min_len:
        s = s.ljust(min_len)
    if len(s) > max_len:
        s = s[:max_len - 1] + "…"
    return s


def parse_clean_track(
    raw_artist: str,
    raw_title: str,
    artist_finder: Optional[ArtistFinder] = None,
    auto_detect: bool = True
) -> Tuple[str, str]:
    """Очищает и нормализует имя исполнителя и название трека, при необходимости находит автора через сеть."""
    artist = raw_artist.strip() if raw_artist else ""
    title = raw_title.strip() if raw_title else ""

    # Убираем расширения файлов
    title = re.sub(r'\.(mp3|flac|wav|m4a|ogg|opus)$', '', title, flags=re.IGNORECASE)

    # Убираем теги телеграм-каналов (@channel, t.me/...)
    title = re.sub(r'@[\w_]+|t\.me/[\w_]+', '', title)
    artist = re.sub(r'@[\w_]+|t\.me/[\w_]+', '', artist)

    # Убираем номера треков в начале (01. , 02 - )
    title = re.sub(r'^\d+[\.\-\s]+', '', title)

    # Если вместо пробелов стоят подчеркивания
    if '_' in title and ' ' not in title:
        title = title.replace('_', ' ')
    if '_' in artist and ' ' not in artist:
        artist = artist.replace('_', ' ')

    # Убираем лишние скобки с битрейтом вроде [320kbps]
    title = re.sub(r'\[(320|256|192|128|flac|lossless).*?\]', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[\s_]+eq\s*[\d\-_]*$', '', title, flags=re.IGNORECASE).strip()

    # Если автор не указан или generic
    generic_artists = ('', 'telegram', 'unknown', 'неизвестный исполнитель', 'аудиозапись')
    if artist.lower() in generic_artists:
        # 1. Пробуем распарсить "Исполнитель - Трек" из названия
        found_by_split = False
        for sep in (' - ', ' – ', ' — '):
            if sep in title:
                parts = title.split(sep, 1)
                if parts[0].strip() and parts[1].strip():
                    artist = parts[0].strip()
                    title = parts[1].strip()
                    found_by_split = True
                    break

        # 2. Если разделителя нет в названии, ищем автора через SoundCloud/Deezer/iTunes
        if not found_by_split and auto_detect and artist_finder:
            found_art, found_tit = artist_finder.resolve(title)
            if found_art:
                artist = found_art
                if found_tit:
                    title = found_tit

    artist = artist.strip() or "Telegram"
    title = title.strip() or "Аудиозапись"
    return artist, title


class TelegramPlayerWatcher:
    """Мониторинг плеера Telegram через D-Bus (MPRIS)."""

    def __init__(self, name_hints: list, artist_finder: Optional[ArtistFinder] = None, auto_detect: bool = True):
        self.name_hints = [h.lower() for h in name_hints]
        self.bus = dbus.SessionBus()
        self.artist_finder = artist_finder
        self.auto_detect = auto_detect

    def find_active_player(self) -> Optional[str]:
        try:
            names = self.bus.list_names()
        except Exception as e:
            logger.warning("Ошибка опроса D-Bus имен: %s", e)
            return None

        matched = []
        for name in names:
            if name.startswith("org.mpris.MediaPlayer2."):
                lower = name.lower()
                if any(hint in lower for hint in self.name_hints):
                    matched.append(name)

        if not matched:
            return None

        for player_name in matched:
            try:
                obj = self.bus.get_object(player_name, "/org/mpris/MediaPlayer2")
                props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
                if status == "Playing":
                    return player_name
            except Exception:
                continue

        return matched[0]

    def get_player_state(self, player_bus_name: str) -> Optional[Dict[str, Any]]:
        try:
            obj = self.bus.get_object(player_bus_name, "/org/mpris/MediaPlayer2")
            props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")

            status = str(props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus"))
            metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")

            try:
                pos_micro = int(props.Get("org.mpris.MediaPlayer2.Player", "Position"))
                position_sec = max(0.0, pos_micro / 1_000_000.0)
            except Exception:
                position_sec = 0.0

            raw_title = str(metadata.get("xesam:title", "")).strip()

            artist_raw = metadata.get("xesam:artist", "")
            if isinstance(artist_raw, (list, tuple, dbus.Array)):
                raw_artist = ", ".join(str(a) for a in artist_raw if str(a).strip()).strip()
            else:
                raw_artist = str(artist_raw).strip()

            album = str(metadata.get("xesam:album", "")).strip()
            length_micro = int(metadata.get("mpris:length", 0))
            duration_sec = max(0.0, length_micro / 1_000_000.0)
            art_url = str(metadata.get("mpris:artUrl", "")).strip()

            artist, title = parse_clean_track(
                raw_artist,
                raw_title,
                artist_finder=self.artist_finder,
                auto_detect=self.auto_detect
            )

            return {
                "status": status,
                "title": title,
                "artist": artist,
                "album": album,
                "position": position_sec,
                "duration": duration_sec,
                "art_url": art_url
            }
        except Exception as e:
            return None


def load_config(config_path: str) -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                cfg.update(user_cfg)
        except Exception as e:
            logger.warning("Не удалось прочитать %s: %s", config_path, e)
    else:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
    return cfg


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    config = load_config(config_path)

    client_id = config.get("client_id", DEFAULT_CONFIG["client_id"])
    activity_type = int(config.get("activity_type", DEFAULT_CONFIG["activity_type"]))
    fallback_cover = config.get("fallback_cover", DEFAULT_CONFIG["fallback_cover"])
    poll_interval = float(config.get("poll_interval_seconds", 1.0))
    show_paused = bool(config.get("show_paused", True))
    search_covers = bool(config.get("search_covers", True))
    show_button = bool(config.get("show_button", True))
    button_label = sanitize_str(config.get("button_label", "🔍 Найти трек"), min_len=1, max_len=32)
    small_text_label = config.get("small_text_label", "in Telegram")
    player_hints = config.get("player_name_hints", DEFAULT_CONFIG["player_name_hints"])
    show_author_name = bool(config.get("show_author_as_activity_name", True))
    state_format = config.get("state_format", "{artist}")
    auto_detect_artist = bool(config.get("auto_detect_missing_artist", True))

    ipc = DiscordIPC(client_id)
    artist_finder = ArtistFinder()
    watcher = TelegramPlayerWatcher(player_hints, artist_finder=artist_finder, auto_detect=auto_detect_artist)
    covers = CoverFinder(fallback_cover)

    running = True

    def sig_handler(sig, frame):
        nonlocal running
        logger.info("Завершение работы по сигналу...")
        running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    type_name = "Listening" if activity_type == 2 else ("Competing" if activity_type == 5 else f"Type {activity_type}")
    logger.info("Запущен сервис Telegram Discord RPC (режим %s).", type_name)

    last_signature: Optional[str] = None
    last_expected_pos = 0.0
    last_pos_time = 0.0
    last_update_time = 0.0
    had_active_presence = False

    while running:
        try:
            player_name = watcher.find_active_player()

            if not player_name:
                if had_active_presence:
                    logger.info("Telegram не воспроизводит аудио. Очистка статуса.")
                    ipc.clear_activity()
                    had_active_presence = False
                    last_signature = None
                time.sleep(poll_interval)
                continue

            state = watcher.get_player_state(player_name)
            if not state or state["status"] == "Stopped":
                if had_active_presence:
                    logger.info("Воспроизведение остановлено.")
                    ipc.clear_activity()
                    had_active_presence = False
                    last_signature = None
                time.sleep(poll_interval)
                continue

            status = state["status"]  # Playing или Paused
            if status == "Paused" and not show_paused:
                if had_active_presence:
                    ipc.clear_activity()
                    had_active_presence = False
                    last_signature = None
                time.sleep(poll_interval)
                continue

            title = state["title"]
            artist = state["artist"]
            pos = state["position"]
            dur = state["duration"]
            now = time.time()

            seeked = False
            if last_pos_time > 0 and status == "Playing":
                expected_pos = last_expected_pos + (now - last_pos_time)
                if abs(pos - expected_pos) > 3.5:
                    seeked = True

            base_sig = f"{status}|{artist}|{title}|{int(dur)}"
            time_since_update = now - last_update_time

            need_update = (
                base_sig != last_signature
                or seeked
                or time_since_update > 25.0
                or not had_active_presence
            )

            if need_update:
                # 1. Поиск обложки (Deezer -> SoundCloud -> iTunes -> YouTube)
                if state["art_url"].startswith("http"):
                    cover_url = state["art_url"]
                elif search_covers:
                    cover_url = covers.get_cover(artist, title)
                else:
                    cover_url = fallback_cover

                # 2. Формирование второй строки (state) — без предлога "от"
                formatted_state = state_format.replace("{artist}", artist).replace("{title}", title)
                if status == "Paused":
                    state_text = f"⏸ {formatted_state}"
                else:
                    state_text = formatted_state

                # 3. Формирование активности:
                activity: Dict[str, Any] = {
                    "type": activity_type,
                    "details": sanitize_str(title),
                    "state": sanitize_str(state_text),
                    "assets": {
                        "large_image": cover_url,
                        "small_image": "1",  # Telegram icon
                        "small_text": f"{small_text_label} (Пауза)" if status == "Paused" else small_text_label
                    }
                }

                # Название активности
                if activity_type == 5:
                    activity["name"] = "Telegram"
                elif show_author_name and artist:
                    activity["name"] = sanitize_str(artist)

                # Таймлайн (прогресс-бар)
                if status == "Playing" and dur > 0:
                    activity["timestamps"] = {
                        "start": int(now - pos),
                        "end": int(now + (dur - pos))
                    }
                elif status == "Playing":
                    activity["timestamps"] = {
                        "start": int(now - pos)
                    }

                # Кнопка поиска
                if show_button:
                    search_query = urllib.parse.quote_plus(f"{artist} {title}")
                    yt_url = f"https://www.youtube.com/results?search_query={search_query}"
                    activity["buttons"] = [
                        {
                            "label": button_label,
                            "url": yt_url
                        }
                    ]

                success = ipc.set_activity(activity)
                if success:
                    if base_sig != last_signature:
                        icon = "⏸" if status == "Paused" else "▶"
                        logger.info("%s Сейчас играет: %s — %s (%d сек)", icon, artist, title, int(dur))
                    last_signature = base_sig
                    last_expected_pos = pos
                    last_pos_time = now
                    last_update_time = now
                    had_active_presence = True

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("Непредвиденная ошибка в цикле: %s", e)
            time.sleep(2.0)

    logger.info("Очистка активности в Discord перед завершением...")
    ipc.clear_activity()
    ipc.disconnect()
    logger.info("Завершено.")


if __name__ == "__main__":
    main()
