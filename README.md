# 🎵 Music RPC — Spotify, Telegram & SoundCloud Discord Rich Presence

Универсальное приложение с красивым интерфейсом для отображения музыки из **Spotify**, **Telegram** и **SoundCloud** в твоём статусе Discord в стиле Spotify.

---

## 🌟 Главные преимущества:

- 🟢 **Spotify БЕЗ VPN**: официальная интеграция Spotify с Discord часто перестает работать или требует VPN в некоторых регионах. **Music RPC** парсит данные локально с плеера без обращений к серверам Spotify и транслирует напрямую в Discord — **VPN не нужен!**
- ✈️ **Telegram (AyuGram, Kotatogram, официальный клиент)**:
  - Автор без предлога «от» в стиле Spotify.
  - Автоматическое определение исполнителя через SoundCloud/Deezer/iTunes, если у аудиозаписи нет тегов.
- ☁️ **SoundCloud (Браузеры)**:
  - Поддержка воспроизведения из Chrome, Edge, Firefox, Brave, Opera, Yandex и др. через системные медиа-сессии.
- 🖼 **100% покрытие обложек**:
  - Deezer HD (1000x1000), SoundCloud API (500x500), iTunes (512x512) и YouTube.
- 🎨 **Красивый графический интерфейс (GUI)**:
  - Современная темная тема (Discord / Spotify дизайн).
  - Карточка текущего трека с живой обложкой, таймлайном и прогресс-баром.
  - Быстрое переключение источников: `[⚡ Автовыбор]` `[🎵 Spotify]` `[✈️ Telegram]` `[☁️ SoundCloud]`.
  - Сворачивание в системный трей (около часов).
- 📦 **Автономный `.exe`**:
  - Полностью самодостаточный исполняемый файл — не требует установки Python, pip или Anaconda!

---

## 🚀 Быстрый старт

### 🪟 Windows:

#### Вариант 1 (Без Python / Standalone):
1. Скачай `music-rpc-windows.zip` из раздела [Releases](https://github.com/goggi22/music-rpc/releases).
2. Запусти **`music-rpc.exe`** (или `start_windows.bat`).
3. Приложение откроется с графическим интерфейсом и автоматически подключится к Discord.

#### Сборка собственного автономного `.exe`:
Запусти файл **`build_exe_windows.bat`** — он сам соберет готовый `dist\music-rpc.exe`.

#### Автозапуск в Windows:
Запусти **`install_autostart_windows.bat`** — сервис добавится в автозагрузку и будет тихо работать в трее. Для удаления используй `uninstall_autostart_windows.bat`.

---

### 🐧 Linux:

#### Графический интерфейс:
```bash
python3 main.py
```

#### Фоновый сервис в systemd (автозапуск):
```bash
./install_service.sh
```
- **Статус:** `systemctl --user status music-rpc`
- **Логи:** `journalctl --user -u music-rpc -f`
- **Удаление:** `./uninstall_service.sh`

---

## ⚙️ Настройки (`config.json`)

```json
{
    "client_id": "1262937085635985409",
    "source": "auto",
    "activity_type": 2,
    "show_author_as_activity_name": true,
    "state_format": "{artist}",
    "auto_detect_missing_artist": true,
    "search_covers": true,
    "show_paused": true,
    "show_button": true,
    "button_label": "🔍 Найти трек",
    "poll_interval_seconds": 1.0,
    "minimize_to_tray": true
}
```

---

## 🛠 Системные требования

- **Windows:** Windows 10 или 11 (при использовании `.exe` Python не требуется).
- **Linux:** любой современный дистрибутив с D-Bus, Python 3.8+ (`PySide6`).
- Запущенный клиент Discord (официальный клиент или Vesktop / WebCord).
