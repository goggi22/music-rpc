# Telegram Discord Rich Presence (RPC) в стиле Spotify 🎵

Отображает в твоём Discord-профиле текущую музыку из **Telegram** (AyuGram, официальный Telegram Desktop, Kotatogram, 64Gram и др.) точно так же, как это делает **Spotify**.

Поддерживает **Linux** (D-Bus MPRIS) и **Windows** (System Media Transport Controls / SMTC). Чистый Python с прямым подключением к Discord IPC.

---

## 🌟 Возможности:
- 🟢 **Стиль Spotify**: вместо «Слушает Telegram» в профиле и списке участников пишется имя автора — **«Слушает <Исполнитель>»**.
- 🔎 **Автоматический поиск автора**: если у трека в Telegram нет тегов (только название вроде `masquerade` или `с тобой`), сервис автоматически находит настоящего исполнителя через SoundCloud, Deezer и Apple Music.
- 🖼 **100% покрытие обложек**: многоуровневый интеллектуальный поиск через **Deezer HD**, **SoundCloud API (500x500)**, **iTunes** и **YouTube**. Обложка находится для абсолютно любого трека, включая андерграунд, ремиксы, сливы и эдиты.
- 🧹 **Умная очистка названий**: срезает расширения (`.mp3`, `.flac`), рекламу каналов (`@channel`, `t.me/...`), таймкоды, битрейты (`[320kbps]`) и технические суффиксы (`_eq`, `_audio`).
- ⏱ **Живой прогресс-бар**: синхронизированный таймлайн трека (прошло / осталось).
- ⏸ **Режим паузы**: при паузе отображает `⏸` и останавливает таймер.
- 🔗 **Кнопка «Найти трек»**: ссылка на мгновенный поиск трека на YouTube в один клик.
- 🐧 **Linux**: фоновый сервис `systemd` (автозапуск при входе).
- 🪟 **Windows**: тихий фоновый автозапуск без всплывающих черных консольных окон (через VBS/реестр).

---

## 📦 Скачать готовые архивы (Releases)

Готовые zip-архивы для каждой платформы доступны во вкладке [**Releases**](https://github.com/goggi22/tg-discord-rpc/releases):
- `tg-discord-rpc-windows.zip` — версия для Windows (включает bat-скрипты запуска и автозагрузки).
- `tg-discord-rpc-linux.zip` — версия для Linux (включает systemd сервис и скрипты управления).

---

## 🚀 Установка и запуск

### 🪟 На Windows:
1. Скачай `tg-discord-rpc-windows.zip` из [Releases](https://github.com/goggi22/tg-discord-rpc/releases) (или склонируй репозиторий).
2. Распакуй архив в удобную папку.
3. Для добавления в автозапуск дважды кликни:
   - `install_autostart_windows.bat` — автоматически установит нужные зависимости (`winsdk`), добавит тихий автозапуск в систему и сразу запустит RPC в фоне.
4. Для разового запуска в окне консоли:
   - `start_windows.bat`
5. Для удаления из автозапуска:
   - `uninstall_autostart_windows.bat`

---

### 🐧 На Linux:
1. Клонирование или распаковка `tg-discord-rpc-linux.zip`:
```bash
git clone https://github.com/goggi22/tg-discord-rpc.git
cd tg-discord-rpc
```
2. Установка в автозапуск (`systemd`):
```bash
./install_service.sh
```
3. Управление сервисом:
- **Статус:** `systemctl --user status telegram-discord-rpc`
- **Логи в реальном времени:** `journalctl --user -u telegram-discord-rpc -f`
- **Перезапуск:** `systemctl --user restart telegram-discord-rpc`
- **Остановка:** `systemctl --user stop telegram-discord-rpc`
- **Удаление автозапуска:** `./uninstall_service.sh`

---

## ⚙️ Настройки (`config.json`)

Файл `config.json` генерируется автоматически при первом запуске:

```json
{
    "client_id": "1262937085635985409",
    "activity_type": 2,
    "show_author_as_activity_name": true,
    "state_format": "{artist}",
    "auto_detect_missing_artist": true,
    "small_text_label": "in Telegram",
    "search_covers": true,
    "show_paused": true,
    "show_button": true,
    "button_label": "🔍 Найти трек",
    "poll_interval_seconds": 1.0,
    "fallback_cover": "https://cdn.discordapp.com/app-assets/1262937085635985409/1262949949071691818.png",
    "player_name_hints": [
        "telegram",
        "ayugram",
        "tdesktop",
        "64gram",
        "kotatogram"
    ]
}
```

---

## 🛠 Системные требования
- **Linux:** любой дистрибутив с D-Bus (Arch, Ubuntu, Fedora, Debian и т.д.), Python 3.8+ (`python-dbus`).
- **Windows:** Windows 10 или 11, Python 3.8+ (`pip install winsdk`).
- Запущенный клиент Discord (официальный клиент или Vesktop / WebCord) и Telegram Desktop / AyuGram.
