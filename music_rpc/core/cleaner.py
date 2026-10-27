"""
Утилиты очистки и нормализации метаданных треков.
"""

import re
from typing import Tuple


def sanitize_str(s: str, min_len: int = 2, max_len: int = 128) -> str:
    s = s.strip()
    if len(s) < min_len:
        s = s.ljust(min_len)
    if len(s) > max_len:
        s = s[:max_len - 1] + "…"
    return s


def clean_text(title: str, artist: str = "") -> Tuple[str, str]:
    """
    Очищает название трека и исполнителя:
    - убирает расширения (.mp3, .flac)
    - убирает рекламу телеграм-каналов (@channel, t.me/...)
    - убирает номера дорожек (01. , 02 - )
    - убирает битрейты ([320kbps], [flac])
    - убирает технические постфиксы (_eq, _audio)
    """
    title = title.strip() if title else ""
    artist = artist.strip() if artist else ""

    # Расширения
    title = re.sub(r'\.(mp3|flac|wav|m4a|ogg|opus)$', '', title, flags=re.IGNORECASE)

    # Реклама каналов
    title = re.sub(r'@[\w_]+|t\.me/[\w_]+', '', title)
    artist = re.sub(r'@[\w_]+|t\.me/[\w_]+', '', artist)

    # Номера треков в начале
    title = re.sub(r'^\d+[\.\-\s]+', '', title)

    # Подчеркивания вместо пробелов
    if '_' in title and ' ' not in title:
        title = title.replace('_', ' ')
    if '_' in artist and ' ' not in artist:
        artist = artist.replace('_', ' ')

    # Скобки с битрейтом
    title = re.sub(r'\[(320|256|192|128|flac|lossless).*?\]', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[\s_]+eq\s*[\d\-_]*$', '', title, flags=re.IGNORECASE).strip()

    title = title.strip() or "Без названия"
    artist = artist.strip() or "Неизвестный исполнитель"
    return artist, title


def split_artist_title(text: str) -> Tuple[str, str]:
    """Разделяет строку вида 'Исполнитель - Название' на кортеж (автор, трек)."""
    text = text.strip()
    for sep in (' - ', ' – ', ' — '):
        if sep in text:
            parts = text.split(sep, 1)
            if parts[0].strip() and parts[1].strip():
                return parts[0].strip(), parts[1].strip()
    return "", text
