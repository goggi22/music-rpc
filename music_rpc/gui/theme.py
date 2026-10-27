"""
Тёмная современная тема оформления для Music RPC в стиле Discord и Spotify.
"""

DARK_THEME_QSS = """
QMainWindow, QWidget#CentralWidget {
    background-color: #111214;
    color: #dbdee1;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

QFrame#TrackCard {
    background-color: #1e1f22;
    border: 1px solid #2b2d31;
    border-radius: 12px;
    padding: 16px;
}

QFrame#SettingsCard {
    background-color: #18191c;
    border: 1px solid #232428;
    border-radius: 12px;
    padding: 14px;
}

QLabel {
    color: #dbdee1;
}

QLabel#AppTitle {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}

QLabel#TrackTitle {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#TrackArtist {
    font-size: 13px;
    font-weight: 500;
    color: #949ba4;
}

QLabel#TrackAlbum {
    font-size: 11px;
    color: #80848e;
}

QLabel#TimeLabel {
    font-size: 11px;
    color: #949ba4;
    font-family: monospace;
}

QLabel#StatusBadge {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#StatusBadgeConnected {
    background-color: rgba(35, 165, 90, 0.2);
    color: #23a55a;
    border: 1px solid rgba(35, 165, 90, 0.4);
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#StatusBadgeDisconnected {
    background-color: rgba(240, 178, 50, 0.15);
    color: #f0b232;
    border: 1px solid rgba(240, 178, 50, 0.3);
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#SourceBadge {
    background-color: #2b2d31;
    color: #f2f3f5;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

/* Кнопки выбора источника */
QPushButton#SourceButton {
    background-color: #232428;
    color: #b5bac1;
    border: 1px solid #2b2d31;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#SourceButton:hover {
    background-color: #2b2d31;
    color: #ffffff;
}

QPushButton#SourceButton:checked {
    background-color: #5865f2;
    color: #ffffff;
    border-color: #5865f2;
}

/* Прогресс-бар */
QProgressBar {
    border: none;
    background-color: #2b2d31;
    height: 6px;
    border-radius: 3px;
    text-align: right;
}

QProgressBar::chunk {
    background-color: #1db954;
    border-radius: 3px;
}

/* Чекбоксы */
QCheckBox {
    color: #dbdee1;
    font-size: 13px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #35363c;
    background-color: #232428;
}

QCheckBox::indicator:hover {
    border-color: #5865f2;
}

QCheckBox::indicator:checked {
    background-color: #5865f2;
    border-color: #5865f2;
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
}

/* Вспомогательные кнопки */
QPushButton#ActionBtn {
    background-color: #2b2d31;
    color: #f2f3f5;
    border: 1px solid #35363c;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton#ActionBtn:hover {
    background-color: #35363c;
}

/* Меню трея */
QMenu {
    background-color: #1e1f22;
    border: 1px solid #2b2d31;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    color: #dbdee1;
    padding: 6px 20px 6px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #2b2d31;
    margin: 4px 0px;
}
"""
