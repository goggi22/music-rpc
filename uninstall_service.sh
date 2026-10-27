#!/usr/bin/env bash
SERVICE_NAME="music-rpc.service"
OLD_SERVICE="telegram-discord-rpc.service"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "Остановка и отключение сервиса $SERVICE_NAME..."
systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
rm -f "$SYSTEMD_USER_DIR/$SERVICE_NAME"

systemctl --user stop "$OLD_SERVICE" 2>/dev/null || true
systemctl --user disable "$OLD_SERVICE" 2>/dev/null || true
rm -f "$SYSTEMD_USER_DIR/$OLD_SERVICE"

systemctl --user daemon-reload
echo "Сервис успешно удален."
