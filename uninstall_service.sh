#!/usr/bin/env bash
set -e

systemctl --user stop telegram-discord-rpc.service 2>/dev/null || true
systemctl --user disable telegram-discord-rpc.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/telegram-discord-rpc.service"
systemctl --user daemon-reload

echo "Сервис Telegram Discord RPC отключен и удален из автозапуска."
