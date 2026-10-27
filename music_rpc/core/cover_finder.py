"""
Многоуровневый интеллектуальный поиск обложек музыкальных треков.
Источники:
1. Deezer API (HD квадратные обложки)
2. SoundCloud API (500x500)
3. iTunes Search API (512x512)
4. YouTube Search (100% покрытие)
"""

import urllib.request
import urllib.parse
import json
import re
import logging
from typing import Optional, Dict

logger = logging.getLogger("MusicRPC.CoverFinder")


class CoverFinder:
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
                        return art.replace("-large.", "-t500x500.")
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

            cover_url = self._search_deezer(q)
            if cover_url:
                break

            cover_url = self._search_soundcloud(q)
            if cover_url:
                break

            cover_url = self._search_itunes(q)
            if cover_url:
                break

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
