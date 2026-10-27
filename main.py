#!/usr/bin/env python3
"""
Music RPC - Универсальный Discord Rich Presence для Spotify, Telegram и SoundCloud.
Точка входа: GUI (PySide6) или CLI/Headless режим.
"""

import sys
import os
import signal
import time
import argparse
import logging

from music_rpc.core.config import ConfigManager
from music_rpc.service import MusicRPCService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("MusicRPC")


def run_cli(config_manager: ConfigManager):
    """Консольный (фоновый) режим работы без GUI."""
    logger.info("Запуск Music RPC в консольном режиме...")
    service = MusicRPCService(config_manager)

    running = True

    def sig_handler(sig, frame):
        nonlocal running
        logger.info("Получен сигнал завершения...")
        running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    poll_int = float(config_manager.get("poll_interval_seconds", 1.0))

    while running:
        try:
            service.tick()
            time.sleep(poll_int)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error("Ошибка в цикле: %s", e)
            time.sleep(2.0)

    service.stop()
    logger.info("Сервис остановлен.")


def run_gui(config_manager: ConfigManager):
    """Графический интерфейс на PySide6."""
    try:
        from PySide6.QtWidgets import QApplication
        from music_rpc.gui.main_window import MainWindow
    except ImportError:
        logger.warning("PySide6 не установлен! Переключение в консольный режим (CLI)...")
        run_cli(config_manager)
        return

    app = QApplication(sys.argv)
    app.setApplicationName("Music RPC")
    app.setApplicationDisplayName("Music RPC")

    service = MusicRPCService(config_manager)
    window = MainWindow(config_manager, service)

    if not config_manager.get("start_minimized", False):
        window.show()
    else:
        window.hide()

    sys.exit(app.exec())


def main():
    parser = argparse.ArgumentParser(description="Music RPC - Spotify, Telegram, SoundCloud Discord Presence")
    parser.add_argument("--cli", "--headless", action="store_true", help="Запустить в консольном режиме без графического интерфейса")
    parser.add_argument("--source", choices=["auto", "spotify", "telegram", "soundcloud"], help="Принудительный выбор источника")
    parser.add_argument("--config", default="config.json", help="Путь к файлу конфигурации")

    args = parser.parse_args()

    # Рабочая директория скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    config_path = os.path.join(script_dir, args.config)
    config = ConfigManager(config_path)

    if args.source:
        config.set("source", args.source)

    if args.cli:
        run_cli(config)
    else:
        run_gui(config)


if __name__ == "__main__":
    main()
