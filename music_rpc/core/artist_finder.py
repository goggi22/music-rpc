"""
Сервис автоматического определения исполнителя, если он отсутствует в тегах.
"""

import urllib.request
import urllib.parse
import json
import re
import logging
from typing import Optional, Tuple, Dict

logger = logging.getLogger("MusicRPC.ArtistFinder")


class ArtistFinder:
    SOUNDCLOUD_CLIENT_ID = "bQmaW4vAHmJIUxisgjRG4MAWAiDgsk9D"

    def __init__(self):
        self.cache: Dict[str, Tuple[str, str]] = {}

    def resolve(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        cache_key = title.lower().strip()
        if cache_key in self.cache:
            return self.cache[cache_key]

        search_query = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title)
        search_query = re.sub(r'[\s_]+eq\s*[\d\-_]*', '', search_query, flags=re.IGNORECASE).strip() or title

        # 1. Поиск в SoundCloud
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

                    for sep in (" - ", " – ", " — "):
                        if sep in t_title:
                            parts = t_title.split(sep, 1)
                            if parts[0].strip() and parts[1].strip():
                                res = (parts[0].strip(), parts[1].strip())
                                self.cache[cache_key] = res
                                logger.info("🔎 Найден исполнитель: '%s' для '%s' (SoundCloud)", res[0], res[1])
                                return res

                    if search_query.lower() in t_title.lower() or t_title.lower() in search_query.lower():
                        if t_user:
                            res = (t_user.strip(), search_query)
                            self.cache[cache_key] = res
                            logger.info("🔎 Найден исполнитель: '%s' для '%s' (SoundCloud)", res[0], res[1])
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
                        logger.info("🔎 Найден исполнитель: '%s' для '%s' (Deezer)", res[0], res[1])
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
                        logger.info("🔎 Найден исполнитель: '%s' для '%s' (iTunes)", res[0], res[1])
                        return res
        except Exception:
            pass

        self.cache[cache_key] = (None, None)
        return None, None
