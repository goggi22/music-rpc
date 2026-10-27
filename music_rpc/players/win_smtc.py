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
    try:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as _SM,
            GlobalSystemMediaTransportControlsSessionPlaybackStatus as _PS
        )
        SessionManager = _SM
        PlaybackStatus = _PS
    except BaseException:
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as _SM,
                GlobalSystemMediaTransportControlsSessionPlaybackStatus as _PS
            )
            SessionManager = _SM
            PlaybackStatus = _PS
        except BaseException:
            logger.debug("Windows Media SDK не найден (winrt/winsdk).")


class WinSMTCHelper:
    """Обертка для безопасного доступа к сессиям SMTC в Windows."""

    _manager = None
    _failed = False

    @classmethod
    async def get_manager(cls):
        if not SessionManager or cls._failed:
            return None
        if cls._manager is None:
            try:
                cls._manager = await SessionManager.request_async()
            except BaseException as e:
                cls._failed = True
                logger.debug("Не удалось инициализировать SMTC SessionManager: %s", e)
                return None
        return cls._manager

    @classmethod
    async def get_sessions(cls) -> List[Any]:
        if cls._failed:
            return []
        try:
            mgr = await cls.get_manager()
            if not mgr:
                return []
            return list(mgr.get_sessions())
        except BaseException:
            return []

    @classmethod
    def is_available(cls) -> bool:
        return SessionManager is not None and not cls._failed
