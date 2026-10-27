#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="music-rpc.service"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "=========================================================="
echo "  Установка Music RPC в автозапуск systemd (Linux)"
echo "=========================================================="

mkdir -p "$SYSTEMD_USER_DIR"
cp "$SCRIPT_DIR/music-rpc.service" "$SYSTEMD_USER_DIR/$SERVICE_NAME"

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"

echo ""
echo "✅ Сервис $SERVICE_NAME успешно установлен и запущен!"
echo "Статус сервиса:"
systemctl --user status "$SERVICE_NAME" --no-pager
echo ""
echo "Для просмотра логов в реальном времени:"
echo "  journalctl --user -u $SERVICE_NAME -f"
