# 🎵 Music RPC — Spotify, Telegram & SoundCloud Discord Rich Presence

Универсальный, быстрый и легковесный сервис Discord Rich Presence для одновременной поддержки **Spotify**, **SoundCloud** и **Telegram** с интерактивным CLI-терминалом, умным автовыбором источника, фильтрацией голосовых сообщений и готовым `.exe` для Windows.

---

## 🌟 Возможности и особенности

### 🟢 Spotify (1:1 как оригинальный статус, БЕЗ VPN)
- **Работает без VPN:** официальная интеграция Spotify в Discord часто перестает обновляться или требует постоянного VPN. **Music RPC** считывает медиа-данные локально через системные протоколы (Windows SMTC / Linux MPRIS) — **VPN не требуется!**
- **Поддержка любых источников:** отслеживает как официальное десктопное приложение Spotify, так и веб-плеер (`open.spotify.com`) в любом браузере (Chrome, Edge, Firefox, Brave, Opera, Яндекс).
- **Оригинальный вид в Discord:**
  - Заголовок: **«Слушает Spotify»** (*Listening to Spotify*).
  - Полноразмерная HD-обложка альбома без лишних мелких иконок поверх.
  - Кнопка **«Слушать в Spotify»** с прямой ссылкой на трек или поиск.

### ☁️ SoundCloud
- **Веб и десктоп:** распознает треки из браузеров и неофициальных клиентов SoundCloud.
- **Официальный вид:**
  - Заголовок: **«Слушает SoundCloud»** (*Listening to SoundCloud*).
  - Фирменный значок оранжевого облака SoundCloud в статусе.
  - Кнопка **«В SoundCloud»** с прямым переходом к треку.

### ✈️ Telegram (AyuGram, Kotatogram, 64Gram, Telegram Desktop)
- **Заголовок:** **«Слушает Telegram»** (*Listening to Telegram*) с иконкой самолетика.
- **🛡 Интеллектуальный фильтр не-музыкальных медиа:**
  - **Голосовые сообщения:** автоматически отсекаются по форматам даты и времени (`сегодня в 20:55`, `yesterday at 14:10`, `27.10.2026 в ...`) и системным ключевым словам (`голосовое сообщение`, `voice message`, `audio_...`).
  - **Кружочки (видеосообщения):** полностью игнорируются (`видеосообщение`, `кружочек`, `round video`).
  - **Видеофайлы и клипы:** отсекаются по расширениям (`.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`, `.flv`, `.gif`) и префиксам камеры (`VID_...`, `MOV_...`).
  - **Только настоящая музыка:** статус отображается исключительно для музыкальных файлов (`.mp3`, `.flac`, `.m4a`, `.wav`, `.opus`, теги ID3 или формат `Исполнитель — Название`).
- **Авто-поиск авторов:** если в аудиозаписи Telegram не указан исполнитель, сервис автоматически найдет автора через SoundCloud, Deezer или iTunes.

### ⚡ Умный автовыбор (Auto Mode) и приоритеты
- Сервис сам определяет, какой плеер играет в данный момент.
- Музыкальные плееры (**Spotify** и **SoundCloud**) имеют **строгий приоритет** над Telegram — если вы слушаете музыку и одновременно включили аудио в Telegram, статус музыки не перебьется.

### 🎛 Ручной режим (Custom Track)
- Возможность вручную задать любого исполнителя, трек и альбом прямо через консоль или параметры запуска.

---

## 🚀 Быстрый старт

### 🪟 Windows (Без установки Python)

1. Скачайте архив **`music-rpc-windows-exe.zip`** из [Releases](https://github.com/goggi22/music-rpc/releases) (или папки `dist/`).
2. Распакуйте архив в удобную папку.
3. Запустите **`music-rpc.exe`** (или `start_windows.bat`).
4. Откроется интерактивное терминальное меню, и статус сразу подключится к Discord!

#### Автозапуск в Windows:
- Запустите **`install_autostart_windows.bat`** — сервис пропишется в автозагрузку пользователя и будет запускаться при старте Windows.
- Для отключения автозапуска запустите **`uninstall_autostart_windows.bat`**.

---

### 🐧 Linux

#### 1. Установка зависимостей:
```bash
git clone https://github.com/goggi22/music-rpc.git
cd music-rpc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. Запуск в терминале (Интерактивный CLI):
```bash
./start.sh
# или напрямую:
python3 main.py
```

#### 3. Установка как системный фоновый сервис (systemd):
```bash
./install_service.sh
```
- **Проверить статус:** `systemctl --user status music-rpc`
- **Просмотр логов в реальном времени:** `journalctl --user -u music-rpc -f`
- **Перезапуск сервиса:** `systemctl --user restart music-rpc`
- **Удаление автозапуска:** `./uninstall_service.sh`

---

## 💻 Режимы запуска и параметры CLI

```
usage: main.py [-h] [--gui] [--headless] [--source {auto,spotify,telegram,soundcloud,manual}]
               [--config CONFIG] [--artist ARTIST] [--title TITLE] [--album ALBUM]
```

| Параметр | Описание |
| :--- | :--- |
| *(без аргументов)* | **Интерактивный CLI**: удобное меню со стрелочками, горячими клавишами и живым статусом |
| `--headless`, `--daemon` | **Фоновый режим**: тихий консольный вывод (идеально для systemd, задачников и скриптов) |
| `--gui` | **Графический интерфейс** на PySide6 (если установлена библиотека) |
| `--source <источник>` | Принудительно зафиксировать источник: `auto`, `spotify`, `telegram`, `soundcloud`, `manual` |
| `--artist <имя>` | Указать исполнителя для ручного режима |
| `--title <название>` | Указать название трека для ручного режима |
| `--album <альбом>` | Указать название альбома для ручного режима |
| `--config <путь>` | Путь к кастомному файлу конфигурации (по умолчанию `config.json`) |

---

## ⚙️ Настройки (`config.json`)

Файл конфигурации создается автоматически при первом запуске, его можно настраивать под себя:

```json
{
    "client_id": "1262937085635985409",
    "client_ids": {
        "spotify": "1316777610419634180",
        "telegram": "1262937085635985409",
        "soundcloud": "802958833214423081"
    },
    "source": "auto",
    "activity_type": 2,
    "show_author_as_activity_name": false,
    "state_format": "{artist}",
    "auto_detect_missing_artist": true,
    "telegram_filter_non_music": true,
    "telegram_min_duration_seconds": 12.0,
    "search_covers": true,
    "show_paused": true,
    "show_button": true,
    "button_label": "🔍 Найти трек",
    "poll_interval_seconds": 1.0,
    "fallback_cover_spotify": "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/spotify.png",
    "fallback_cover_soundcloud": "https://cdn.discordapp.com/app-icons/802958833214423081/c07fbcacdd970a86e334d59b27a1fa70.png",
    "fallback_cover_telegram": "https://cdn.discordapp.com/app-assets/1262937085635985409/1262949949071691818.png",
    "player_name_hints": [
        "telegram",
        "ayugram",
        "tdesktop",
        "64gram",
        "kotatogram",
        "exteragram"
    ]
}
```

### Подробное описание опций:

| Опция | Тип | По умолчанию | Описание |
| :--- | :--- | :--- | :--- |
| `source` | `str` | `"auto"` | Активный режим: `"auto"` (умный выбор), `"spotify"`, `"telegram"`, `"soundcloud"`, `"manual"` |
| `client_ids` | `dict` | *см. выше* | Discord Application ID для каждого сервиса, чтобы отображалось соответствующее имя в профиле |
| `telegram_filter_non_music` | `bool` | `true` | Игнорировать голосовые сообщения, кружочки и видеоролики в Telegram |
| `telegram_min_duration_seconds` | `float` | `12.0` | Минимальная длина аудиозаписи в Telegram, чтобы считать её музыкой |
| `auto_detect_missing_artist` | `bool` | `true` | Авто-поиск автора песни через Deezer/SoundCloud, если у файла нет ID3-тегов |
| `search_covers` | `bool` | `true` | Искать официальные HD-обложки альбомов в музыкальных базах |
| `show_paused` | `bool` | `true` | Показывать статус со значком ⏸ при паузе трека (если `false`, статус скрывается) |
| `show_button` | `bool` | `true` | Показывать кнопку со ссылкой на трек в Discord |
| `poll_interval_seconds` | `float` | `1.0` | Частота опроса медиа-сессий в секундах |
| `player_name_hints` | `list` | *список* | Ключевые слова для поиска процессов Telegram / кастомных форков |

---

## 🛠 Системные требования

- **ОС:**
  - **Windows:** Windows 10 или 11 (при использовании автономного `.exe` Python не требуется).
  - **Linux:** любой современный дистрибутив с D-Bus (Ubuntu, Debian, Fedora, Arch Linux, Void и др.).
- **Discord:** официальный клиент Discord или клиенты Vesktop / WebCord / ArmCord / Discord Canary.

---

## 📄 Лицензия

Проект распространяется под лицензией [MIT](LICENSE).
