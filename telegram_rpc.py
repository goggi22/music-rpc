#!/usr/bin/env python3
"""
Обертка обратной совместимости для старых скриптов telegram_rpc.py.
Перенаправляет запуск на ядро Music RPC в режиме Telegram.
"""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from main import main

if __name__ == "__main__":
    # Если запущен напрямую как telegram_rpc.py, включаем режим telegram
    if "--source" not in sys.argv:
        sys.argv.extend(["--source", "telegram"])
    main()
