#!/usr/bin/env python3
"""
Music RPC - Универсальный Discord Rich Presence для Spotify, Telegram и SoundCloud.
Точка входа: по умолчанию быстрый интерактивный CLI терминал.
"""

import sys
import os
import signal
import time
import argparse
import logging

from music_rpc.core.config import ConfigManager
from music_rpc.service import MusicRPCService
from music_rpc.cli import MusicRPCCLI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("MusicRPC")


def run_headless(config_manager: ConfigManager):
    """Консольный фоновый режим без интерактива (для systemd/демонов)."""
    logger.info("Запуск Music RPC в фоновом режиме...")
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
    """Опциональный графический интерфейс на PySide6."""
    try:
        from PySide6.QtWidgets import QApplication
        from music_rpc.gui.main_window import MainWindow
    except ImportError:
        logger.warning("PySide6 не установлен. Запуск в интерактивном CLI...")
        service = MusicRPCService(config_manager)
        cli = MusicRPCCLI(service, config_manager)
        cli.run()
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
    parser.add_argument("--gui", action="store_true", help="Запустить в графическом интерфейсе (PySide6)")
    parser.add_argument("--headless", "--daemon", action="store_true", help="Фоновый режим без интерактивного меню")
    parser.add_argument("--source", choices=["auto", "spotify", "telegram", "soundcloud", "manual"], help="Выбор источника")
    parser.add_argument("--config", default="config.json", help="Путь к файлу конфигурации")
    parser.add_argument("--artist", help="Имя исполнителя для ручного ввода")
    parser.add_argument("--title", help="Название трека для ручного ввода")
    parser.add_argument("--album", help="Альбом для ручного ввода")

    args = parser.parse_args()

    # Рабочая директория скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    config_path = os.path.join(script_dir, args.config)
    config = ConfigManager(config_path)

    if args.source:
        config.set("source", args.source)

    if args.gui:
        run_gui(config)
    elif args.headless or not sys.stdin.isatty():
        run_headless(config)
    else:
        service = MusicRPCService(config)
        if args.artist and args.title:
            service.set_manual_track(args.artist, args.title, args.album or "")
        cli = MusicRPCCLI(service, config)
        cli.run()


if __name__ == "__main__":
    main()
