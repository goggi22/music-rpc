#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

sed "s|ExecStart=.*|ExecStart=/usr/bin/python3 $SCRIPT_DIR/telegram_rpc.py|g" "$SCRIPT_DIR/telegram-discord-rpc.service" > "$SERVICE_DIR/telegram-discord-rpc.service"
systemctl --user daemon-reload
systemctl --user enable --now telegram-discord-rpc.service

echo ""
echo "=========================================================="
echo "  Telegram Discord RPC успешно установлен в автозапуск!"
echo "=========================================================="
echo "Проверить статус:   systemctl --user status telegram-discord-rpc"
echo "Смотреть логи:      journalctl --user -u telegram-discord-rpc -f"
echo "Остановить сервис:  systemctl --user stop telegram-discord-rpc"
echo ""
