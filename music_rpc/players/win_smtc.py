"""
Интеграция с Windows System Media Transport Controls (SMTC).
Поддерживает как PyWinRT (winrt-Windows.Media.Control), так и winsdk.
"""

import sys
import logging
from typing import Optional, List, Any

logger = logging.getLogger("MusicRPC.WinSMTC")

SessionManager = None
PlaybackStatus = None

if sys.platform == "win32":
    import asyncio
    try:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as _SM,
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as _PS
        )
        SessionManager = _SM
        PlaybackStatus = _PS
    except ImportError:
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as _SM,
                GlobalSystemMediaTransportControlsSessionPlaybackStatus as _PS
            )
            SessionManager = _SM
            PlaybackStatus = _PS
        except ImportError:
            logger.warning("Windows Media SDK не найден! Установите winrt-Windows.Media.Control или winsdk.")


class WinSMTCHelper:
    """Обертка для доступа к сессиям SMTC в Windows."""

    _manager = None

    @classmethod
    async def get_manager(cls):
        if not SessionManager:
            return None
        if cls._manager is None:
            try:
                cls._manager = await SessionManager.request_async()
            except Exception as e:
                logger.warning("Не удалось инициализировать SMTC SessionManager: %s", e)
        return cls._manager

    @classmethod
    async def get_sessions(cls) -> List[Any]:
        mgr = await cls.get_manager()
        if not mgr:
            return []
        try:
            return list(mgr.get_sessions())
        except Exception:
            return []

    @classmethod
    def is_available(cls) -> bool:
        return SessionManager is not None
