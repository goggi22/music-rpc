# Telegram Discord Rich Presence (RPC) в стиле Spotify 🎵

Отображает в твоём Discord-профиле текущую музыку из **Telegram** (AyuGram, официальный Telegram Desktop, Kotatogram, 64Gram и др.) точно так же, как это делает **Spotify**.

Чистый Python без тяжелых зависимостей: прямое общение с Discord через IPC-сокет и опрос плеера через D-Bus (MPRIS).

---

## 🌟 Возможности:
- 🟢 **Стиль Spotify**: вместо «Слушает Telegram» в профиле и списке участников пишется имя автора — **«Слушает <Исполнитель>»**.
- 🔎 **Автоматический поиск автора**: если у трека в Telegram нет тегов (только название вроде `masquerade` или `с тобой`), сервис автоматически находит настоящего исполнителя через SoundCloud, Deezer и Apple Music.
- 🖼 **100% покрытие обложек**: многоуровневый интеллектуальный поиск через **Deezer HD**, **SoundCloud API (500x500)**, **iTunes** и **YouTube**. Обложка находится для абсолютно любого трека, включая андерграунд, ремиксы, сливы и эдиты.
- 🧹 **Умная очистка названий**: срезает расширения (`.mp3`, `.flac`), рекламу каналов (`@channel`, `t.me/...`), таймкоды, битрейты (`[320kbps]`) и технические суффиксы (`_eq`, `_audio`).
- ⏱ **Живой прогресс-бар**: синхронизированный таймлайн трека (прошло / осталось).
- ⏸ **Режим паузы**: при паузе отображает `⏸` и останавливает таймер.
- 🔗 **Кнопка «Найти трек»**: ссылка на мгновенный поиск трека на YouTube в один клик.
- 🐧 **Systemd User Service**: работает как фоновый сервис в Linux (автозапуск при логине).

---

## 🚀 Быстрый старт

### 1. Клонирование
```bash
git clone https://github.com/goggi22/tg-discord-rpc.git
cd tg-discord-rpc
```

### 2. Запуск сервиса в фоне (systemd)
```bash
./install_service.sh
```

### 3. Управление
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

## 🛠 Требования
- Linux (любой дистрибутив с D-Bus: Arch, Ubuntu, Fedora, Debian и т.д.)
- Python 3.8+ (используются только стандартные библиотеки и системный `dbus-python`)
- Запущенный Discord (клиент или Vesktop/WebCord) и Telegram Desktop / AyuGram
