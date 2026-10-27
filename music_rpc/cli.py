"""
Интерактивная консольная утилита (CLI) для Music RPC.
Быстрый, легкий (без тяжелых GUI библиотек), с возможностью выбора трека и источника.
"""

import os
import sys
import time
import signal
import threading
from typing import Optional

from .service import MusicRPCService
from .core.config import ConfigManager
from .players.base import TrackState

# Инициализация ANSI цветов для Windows
if sys.platform == "win32":
    os.system("")

# ANSI цветовые коды
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_seconds(sec: float) -> str:
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m:02d}:{s:02d}"


class MusicRPCCLI:
    """Интерактивный терминальный интерфейс для Music RPC."""

    def __init__(self, service: MusicRPCService, config: ConfigManager):
        self.service = service
        self.config = config
        self.running = True
        self.lock = threading.Lock()
        self.last_status_line = ""

    def _worker_loop(self):
        """Фоновый цикл обновления статуса Discord."""
        while self.running:
            try:
                self.service.tick()
            except Exception:
                pass
            time.sleep(1.0)

    def print_banner(self):
        banner = f"""{CYAN}{BOLD}
========================================================================
  🎵 MUSIC RPC — Discord Presence (Spotify / Telegram / SoundCloud)
========================================================================{RESET}"""
        print(banner)

    def print_dashboard(self):
        with self.lock:
            # Очистка не обязательна каждый раз, но сделаем разделитель
            is_discord = self.service.ipc.connected
            current = self.service.get_current_track()
            mode = self.config.get("source", "auto")
            all_states = self.service.get_available_tracks()

            discord_str = f"{GREEN}🟢 Подключено (Discord найден){RESET}" if is_discord else f"{RED}🔴 Ожидание Discord (запустите клиент Discord){RESET}"
            
            mode_names = {
                "auto": "Автоматический (активный плеер)",
                "spotify": "Только Spotify (100% вид оригинала)",
                "telegram": "Только Telegram",
                "soundcloud": "Только SoundCloud",
                "manual": "Пользовательский (ручной ввод)"
            }
            mode_str = mode_names.get(mode, mode.capitalize())

            print(f"\n{BOLD}[Статус Discord]:{RESET} {discord_str}")
            print(f"{BOLD}[Режим выбора]:{RESET}   {YELLOW}{mode_str}{RESET}")
            print(f"{DIM}{'─' * 70}{RESET}")

            # Текущий транслируемый трек
            if current and current.is_active:
                status_icon = "▶ Играет" if current.status == "Playing" else "⏸ На паузе"
                dur_str = f"{format_seconds(current.position)} / {format_seconds(current.duration)}" if current.duration > 0 else format_seconds(current.position)
                source_badge = f"{GREEN}Spotify (Оригинальный вид){RESET}" if current.source == "spotify" else current.source_display

                print(f"{BOLD}СЕЙЧАС В DISCORD:{RESET}")
                print(f"  🎵 {BOLD}Трек:{RESET}     {CYAN}{current.title}{RESET}")
                print(f"  👤 {BOLD}Автор:{RESET}    {current.artist}")
                if current.album:
                    print(f"  💿 {BOLD}Альбом:{RESET}   {current.album}")
                print(f"  📻 {BOLD}Источник:{RESET} {source_badge}")
                print(f"  ⏱  {BOLD}Статус:{RESET}   {status_icon} ({dur_str})")
            else:
                print(f"{DIM}В данный момент музыка не играет (Discord статус чист){RESET}")

            print(f"{DIM}{'─' * 70}{RESET}")
            print(f"{BOLD}ДОСТУПНЫЕ ИСТОЧНИКИ И ТРЕКИ:{RESET}")

            # Список обнаруженных плееров
            sources = [
                ("1", "spotify", "🟢 Spotify", "Spotify"),
                ("2", "telegram", "✈️ Telegram", "Telegram"),
                ("3", "soundcloud", "☁️ SoundCloud", "SoundCloud"),
            ]

            for num, key, title_label, display in sources:
                st = all_states.get(key)
                selected = f" {GREEN}{BOLD}← ВЫБРАН{RESET}" if mode == key else ""
                if st and st.is_active:
                    st_icon = "▶" if st.status == "Playing" else "⏸"
                    print(f"  [{BOLD}{num}{RESET}] {title_label:<14}: {st_icon} {st.artist} — {st.title}{selected}")
                elif st and st.status == "Stopped":
                    print(f"  [{BOLD}{num}{RESET}] {title_label:<14}: {DIM}Остановлен{RESET}{selected}")
                else:
                    print(f"  [{BOLD}{num}{RESET}] {title_label:<14}: {DIM}Не запущен / нет трека{RESET}{selected}")

            if "manual" in all_states and all_states["manual"]:
                m_st = all_states["manual"]
                m_selected = f" {GREEN}{BOLD}← ВЫБРАН{RESET}" if mode == "manual" else ""
                print(f"  [{BOLD}M{RESET}] ✍️ Ручной трек   : {m_st.artist} — {m_st.title}{m_selected}")

            auto_selected = f" {GREEN}{BOLD}← ВЫБРАН{RESET}" if mode == "auto" else ""
            print(f"  [{BOLD}A{RESET}] 🔄 Авто-режим   : Автоматически транслировать играющий плеер{auto_selected}")

            print(f"{DIM}{'─' * 70}{RESET}")
            print(f"{BOLD}КОМАНДЫ УПРАВЛЕНИЯ:{RESET}")
            print(f"  {CYAN}1, 2, 3{RESET} - Выбрать конкретный плеер (Spotify / Telegram / SoundCloud)")
            print(f"  {CYAN}A{RESET}       - Включить авто-режим (Auto)")
            print(f"  {CYAN}M{RESET}       - Ввести свой трек вручную (Кастомный статус)")
            print(f"  {CYAN}P / Space{RESET}- Пауза / Возобновить трек (Play/Pause)")
            print(f"  {CYAN}N{RESET}       - Следующий трек (Next)")
            print(f"  {CYAN}B{RESET}       - Предыдущий трек (Previous)")
            print(f"  {CYAN}R{RESET}       - Обновить статус")
            print(f"  {CYAN}Q{RESET}       - Выход")
            print(f"{DIM}{'─' * 70}{RESET}")

    def run(self):
        """Запуск интерактивного режима."""
        self.print_banner()

        # Запуск фонового воркера
        worker = threading.Thread(target=self._worker_loop, daemon=True)
        worker.start()

        time.sleep(0.5)  # Дать сервису инициализироваться
        self.print_dashboard()

        while self.running:
            try:
                cmd = input(f"{BOLD}[music-rpc] > {RESET}").strip().lower()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd:
                continue

            if cmd == "q":
                print(f"\n{YELLOW}Завершение работы Music RPC...{RESET}")
                break

            elif cmd == "1":
                self.service.set_source("spotify")
                print(f"{GREEN}✓ Источник переключен на Spotify (100% оригинальный вид в Discord)!{RESET}")
                time.sleep(0.3)
                self.print_dashboard()

            elif cmd == "2":
                self.service.set_source("telegram")
                print(f"{GREEN}✓ Источник переключен на Telegram!{RESET}")
                time.sleep(0.3)
                self.print_dashboard()

            elif cmd == "3":
                self.service.set_source("soundcloud")
                print(f"{GREEN}✓ Источник переключен на SoundCloud!{RESET}")
                time.sleep(0.3)
                self.print_dashboard()

            elif cmd == "a":
                self.service.set_source("auto")
                print(f"{GREEN}✓ Включен автоматический режим выбора активного плеера!{RESET}")
                time.sleep(0.3)
                self.print_dashboard()

            elif cmd == "m":
                print(f"\n{BOLD}--- Ручной ввод трека ---{RESET}")
                try:
                    artist = input("Введите имя исполнителя (Автор): ").strip()
                    title = input("Введите название трека: ").strip()
                    album = input("Введите альбом (необязательно): ").strip()
                except (KeyboardInterrupt, EOFError):
                    continue

                if artist and title:
                    self.service.set_manual_track(artist, title, album)
                    self.config.set("source", "manual")
                    print(f"{GREEN}✓ Установлен трек: {artist} — {title}! Идет поиск обложки и отправка в Discord...{RESET}")
                else:
                    print(f"{RED}Ошибка: Исполнитель и название не могут быть пустыми!{RESET}")
                time.sleep(0.5)
                self.print_dashboard()

            elif cmd in ("p", " ", "pause", "play"):
                ok = self.service.control_media("PlayPause")
                status = f"{GREEN}✓ Отправлена команда Play/Pause{RESET}" if ok else f"{YELLOW}Команда отправлена (нет активного плеера для ответа){RESET}"
                print(status)
                time.sleep(0.5)
                self.print_dashboard()

            elif cmd in ("n", "next"):
                ok = self.service.control_media("Next")
                print(f"{GREEN}✓ Следующий трек (Next){RESET}")
                time.sleep(0.8)
                self.print_dashboard()

            elif cmd in ("b", "prev", "back"):
                ok = self.service.control_media("Previous")
                print(f"{GREEN}✓ Предыдущий трек (Previous){RESET}")
                time.sleep(0.8)
                self.print_dashboard()

            elif cmd == "r":
                self.print_dashboard()

            else:
                print(f"{RED}Неизвестная команда '{cmd}'. Введите 1, 2, 3, A, M, P, N, B, R или Q.{RESET}")

        self.running = False
        self.service.stop()
        print(f"{GREEN}Music RPC успешно остановлен. До встречи!{RESET}")
