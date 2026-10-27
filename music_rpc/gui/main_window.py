"""
Главное окно графического интерфейса Music RPC на PySide6.
"""

import sys
import os
import urllib.request
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, Slot, QSize, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QProgressBar, QCheckBox, QFrame,
    QSystemTrayIcon, QMenu, QApplication
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QFont, QAction

from .theme import DARK_THEME_QSS
from ..service import MusicRPCService
from ..players.base import TrackState
from ..core.config import ConfigManager


class RPCWorkerThread(QThread):
    """Фоновый поток выполнения MusicRPCService, не блокирующий GUI."""

    track_changed = Signal(object, str)  # (TrackState, cover_url)
    discord_status_changed = Signal(bool)

    def __init__(self, service: MusicRPCService, interval_sec: float = 1.0):
        super().__init__()
        self.service = service
        self.interval_sec = interval_sec
        self.running = True

        self.service.on_state_change = self._on_service_state_change
        self.service.on_discord_status = self._on_service_discord_status

    def _on_service_state_change(self, state: Optional[TrackState], cover_url: str):
        self.track_changed.emit(state, cover_url)

    def _on_service_discord_status(self, connected: bool):
        self.discord_status_changed.emit(connected)

    def run(self):
        while self.running:
            try:
                self.service.tick()
            except Exception:
                pass
            self.msleep(int(self.interval_sec * 1000))

    def stop(self):
        self.running = False
        self.wait()


class ImageLoaderThread(QThread):
    """Асинхронная загрузка обложки по URL."""
    image_loaded = Signal(QPixmap, str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        if not self.url or not self.url.startswith("http"):
            return
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = resp.read()
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    self.image_loaded.emit(pixmap, self.url)
        except Exception:
            pass


class MainWindow(QMainWindow):
    """Главное окно приложения Music RPC."""

    def __init__(self, config_manager: ConfigManager, service: MusicRPCService):
        super().__init__()
        self.config = config_manager
        self.service = service

        self.current_state: Optional[TrackState] = None
        self.current_cover_url: str = ""
        self.image_loader: Optional[ImageLoaderThread] = None

        self.setWindowTitle("Music RPC")
        self.setFixedSize(540, 520)
        self.setStyleSheet(DARK_THEME_QSS)

        self._create_ui()
        self._setup_tray()

        # Запуск фонового сервиса
        poll_int = float(self.config.get("poll_interval_seconds", 1.0))
        self.worker = RPCWorkerThread(self.service, interval_sec=poll_int)
        self.worker.track_changed.connect(self.on_track_changed)
        self.worker.discord_status_changed.connect(self.on_discord_status_changed)
        self.worker.start()

    def _create_ui(self):
        central = QWidget(self)
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Заголовок и статус Discord
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_lbl = QLabel("🎵 Music RPC", self)
        title_lbl.setObjectName("AppTitle")

        self.status_badge = QLabel("○ Подключение к Discord...", self)
        self.status_badge.setObjectName("StatusBadgeDisconnected")

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        main_layout.addLayout(header_layout)

        # 2. Карточка текущего трека
        self.track_card = QFrame(self)
        self.track_card.setObjectName("TrackCard")
        card_layout = QHBoxLayout(self.track_card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(16)

        # Обложка
        self.cover_label = QLabel(self)
        self.cover_label.setFixedSize(110, 110)
        self.cover_label.setStyleSheet("background-color: #2b2d31; border-radius: 8px;")
        self.cover_label.setAlignment(Qt.AlignCenter)
        self._set_default_cover()
        card_layout.addWidget(self.cover_label)

        # Инфо трека
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignVCenter)

        # Бейдж источника
        badge_layout = QHBoxLayout()
        self.source_badge = QLabel("Ожидание музыки", self)
        self.source_badge.setObjectName("SourceBadge")
        badge_layout.addWidget(self.source_badge)
        badge_layout.addStretch()
        info_layout.addLayout(badge_layout)

        # Название и автор
        self.track_title_lbl = QLabel("Нет активного трека", self)
        self.track_title_lbl.setObjectName("TrackTitle")
        self.track_title_lbl.setWordWrap(True)

        self.track_artist_lbl = QLabel("Запустите плеер для трансляции", self)
        self.track_artist_lbl.setObjectName("TrackArtist")

        self.track_album_lbl = QLabel("", self)
        self.track_album_lbl.setObjectName("TrackAlbum")

        info_layout.addWidget(self.track_title_lbl)
        info_layout.addWidget(self.track_artist_lbl)
        info_layout.addWidget(self.track_album_lbl)

        # Прогресс-бар
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        info_layout.addWidget(self.progress_bar)

        # Время
        time_layout = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00", self)
        self.time_label.setObjectName("TimeLabel")
        self.status_icon_lbl = QLabel("⏹", self)
        self.status_icon_lbl.setObjectName("TimeLabel")
        time_layout.addWidget(self.status_icon_lbl)
        time_layout.addStretch()
        time_layout.addWidget(self.time_label)
        info_layout.addLayout(time_layout)

        card_layout.addLayout(info_layout)
        main_layout.addWidget(self.track_card)

        # 3. Выбор источника
        source_group_box = QFrame(self)
        source_group_box.setObjectName("SettingsCard")
        source_layout = QVBoxLayout(source_group_box)
        source_layout.setContentsMargins(12, 12, 12, 12)
        source_layout.setSpacing(10)

        source_title = QLabel("ВЫБОР ИСТОЧНИКА", self)
        source_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #949ba4; letter-spacing: 0.5px;")
        source_layout.addWidget(source_title)

        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(8)

        self.source_btn_group = QButtonGroup(self)
        self.source_btn_group.setExclusive(True)

        sources = [
            ("auto", "⚡ Автовыбор"),
            ("spotify", "🎵 Spotify"),
            ("telegram", "✈️ Telegram"),
            ("soundcloud", "☁️ SoundCloud")
        ]

        current_src = self.config.get("source", "auto")
        for key, text in sources:
            btn = QPushButton(text, self)
            btn.setObjectName("SourceButton")
            btn.setCheckable(True)
            if key == current_src:
                btn.setChecked(True)
            self.source_btn_group.addButton(btn)
            btns_layout.addWidget(btn)
            btn.clicked.connect(lambda checked, k=key: self._on_source_button_clicked(k))

        source_layout.addLayout(btns_layout)
        main_layout.addWidget(source_group_box)

        # 4. Настройки трансляции
        settings_box = QFrame(self)
        settings_box.setObjectName("SettingsCard")
        settings_layout = QVBoxLayout(settings_box)
        settings_layout.setContentsMargins(14, 14, 14, 14)
        settings_layout.setSpacing(10)

        settings_title = QLabel("ПАРАМЕТРЫ DISCORD RICH PRESENCE", self)
        settings_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #949ba4; letter-spacing: 0.5px;")
        settings_layout.addWidget(settings_title)

        self.cb_button = QCheckBox("Кнопка со ссылкой '🔍 Найти трек' в профиле", self)
        self.cb_button.setChecked(bool(self.config.get("show_button", True)))
        self.cb_button.toggled.connect(lambda v: self.config.set("show_button", v))
        settings_layout.addWidget(self.cb_button)

        self.cb_covers = QCheckBox("Автоматический поиск обложек в HD (SoundCloud / Deezer)", self)
        self.cb_covers.setChecked(bool(self.config.get("search_covers", True)))
        self.cb_covers.toggled.connect(lambda v: self.config.set("search_covers", v))
        settings_layout.addWidget(self.cb_covers)

        self.cb_missing_artist = QCheckBox("Автопоиск автора трека, если теги отсутствуют", self)
        self.cb_missing_artist.setChecked(bool(self.config.get("auto_detect_missing_artist", True)))
        self.cb_missing_artist.toggled.connect(lambda v: self.config.set("auto_detect_missing_artist", v))
        settings_layout.addWidget(self.cb_missing_artist)

        self.cb_pause = QCheckBox("Отображать статус ⏸ при паузе", self)
        self.cb_pause.setChecked(bool(self.config.get("show_paused", True)))
        self.cb_pause.toggled.connect(lambda v: self.config.set("show_paused", v))
        settings_layout.addWidget(self.cb_pause)

        self.cb_tray = QCheckBox("Сворачивать в трей около часов при закрытии", self)
        self.cb_tray.setChecked(bool(self.config.get("minimize_to_tray", True)))
        self.cb_tray.toggled.connect(lambda v: self.config.set("minimize_to_tray", v))
        settings_layout.addWidget(self.cb_tray)

        main_layout.addWidget(settings_box)
        main_layout.addStretch()

    def _setup_tray(self):
        """Настройка системного трея."""
        self.tray_icon = QSystemTrayIcon(self)
        icon = self._create_app_icon()
        self.setWindowIcon(icon)
        self.tray_icon.setIcon(icon)

        tray_menu = QMenu(self)

        self.tray_track_action = QAction("Music RPC: Ожидание музыки", self)
        self.tray_track_action.setEnabled(False)
        tray_menu.addAction(self.tray_track_action)

        tray_menu.addSeparator()

        show_action = QAction("Показать окно", self)
        show_action.triggered.connect(self._restore_from_tray)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _create_app_icon(self) -> QIcon:
        """Создает стильную векторную иконку ноты/RPC."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)

        p.setBrush(QColor("#1DB954"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 16, 16)

        p.setPen(QColor("#ffffff"))
        font = p.font()
        font.setPointSize(28)
        font.setBold(True)
        p.setFont(font)
        p.drawText(pixmap.rect(), Qt.AlignCenter, "♪")
        p.end()
        return QIcon(pixmap)

    def _set_default_cover(self):
        pixmap = QPixmap(110, 110)
        pixmap.fill(QColor("#2b2d31"))
        p = QPainter(pixmap)
        p.setPen(QColor("#949ba4"))
        font = p.font()
        font.setPointSize(36)
        p.setFont(font)
        p.drawText(pixmap.rect(), Qt.AlignCenter, "♪")
        p.end()
        self.cover_label.setPixmap(self._make_rounded_pixmap(pixmap))

    def _make_rounded_pixmap(self, src: QPixmap, radius: int = 8) -> QPixmap:
        scaled = src.scaled(110, 110, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        dest = QPixmap(110, 110)
        dest.fill(Qt.transparent)

        p = QPainter(dest)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, 110, 110, radius, radius)
        p.setClipPath(path)
        p.drawPixmap(0, 0, scaled)
        p.end()
        return dest

    def _on_source_button_clicked(self, source_key: str):
        self.service.set_source(source_key)

    @Slot(bool)
    def on_discord_status_changed(self, connected: bool):
        if connected:
            self.status_badge.setText("● Discord подключен")
            self.status_badge.setObjectName("StatusBadgeConnected")
        else:
            self.status_badge.setText("○ Ожидание Discord...")
            self.status_badge.setObjectName("StatusBadgeDisconnected")
        self.status_badge.setStyle(self.status_badge.style())

    @Slot(object, str)
    def on_track_changed(self, state: Optional[TrackState], cover_url: str):
        self.current_state = state

        if not state or state.status == "Stopped":
            self.track_title_lbl.setText("Нет активного трека")
            self.track_artist_lbl.setText("Запустите плеер для трансляции")
            self.track_album_lbl.setText("")
            self.source_badge.setText("Ожидание музыки")
            self.source_badge.setStyleSheet("background-color: #2b2d31; color: #949ba4;")
            self.status_icon_lbl.setText("⏹")
            self.progress_bar.setValue(0)
            self.time_label.setText("00:00 / 00:00")
            self._set_default_cover()
            self.tray_track_action.setText("Music RPC: Ожидание музыки")
            return

        # Источник и цвета
        src_colors = {
            "spotify": "#1DB954",
            "telegram": "#229ED9",
            "soundcloud": "#FF5500"
        }
        accent = src_colors.get(state.source, "#5865F2")

        self.source_badge.setText(f"{state.source_display}")
        self.source_badge.setStyleSheet(f"background-color: {accent}; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 2px 6px;")

        self.track_title_lbl.setText(state.title)
        self.track_artist_lbl.setText(state.artist)
        self.track_album_lbl.setText(state.album or "")

        # Иконка воспроизведения
        icon_str = "▶ Сейчас играет" if state.status == "Playing" else "⏸ На паузе"
        self.status_icon_lbl.setText(icon_str)

        # Прогресс
        pos_m, pos_s = divmod(int(state.position), 60)
        dur_m, dur_s = divmod(int(state.duration), 60)
        self.time_label.setText(f"{pos_m:02d}:{pos_s:02d} / {dur_m:02d}:{dur_s:02d}")

        if state.duration > 0:
            pct = int((state.position / state.duration) * 100)
            self.progress_bar.setValue(min(100, max(0, pct)))\
        else:
            self.progress_bar.setValue(0)

        # Трей
        self.tray_track_action.setText(f"{state.source_display}: {state.artist} — {state.title}")
        self.tray_icon.setToolTip(f"Music RPC\n{state.artist} — {state.title}")

        # Обложка
        if cover_url != self.current_cover_url:
            self.current_cover_url = cover_url
            if cover_url:
                self.image_loader = ImageLoaderThread(cover_url)
                self.image_loader.image_loaded.connect(self._on_image_loaded)
                self.image_loader.start()
            else:
                self._set_default_cover()

    @Slot(QPixmap, str)
    def _on_image_loaded(self, pixmap: QPixmap, url: str):
        if url == self.current_cover_url:
            self.cover_label.setPixmap(self._make_rounded_pixmap(pixmap))

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            if self.isVisible():
                self.hide()
            else:
                self._restore_from_tray()

    def _restore_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self.worker.stop()
        self.service.stop()
        QApplication.quit()

    def closeEvent(self, event):
        if self.config.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Music RPC",
                "Приложение свернуто в трей и продолжает работать в фоне.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self._quit_app()
            event.accept()
