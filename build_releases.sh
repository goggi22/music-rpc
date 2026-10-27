#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DIST_DIR="$SCRIPT_DIR/dist"
mkdir -p "$DIST_DIR"

echo "=========================================================="
echo "  Сборка релизных архивов tg-discord-rpc"
echo "=========================================================="

# Убеждаемся, что файлы для Windows имеют переносы строк CRLF (\r\n)
python3 -c "
for fname in ['start_windows.bat', 'install_autostart_windows.bat', 'uninstall_autostart_windows.bat', 'requirements-windows.txt']:
    try:
        with open(fname, 'rb') as f:
            data = f.read()
        crlf = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n').replace(b'\n', b'\r\n')
        with open(fname, 'wb') as f:
            f.write(crlf)
    except Exception as e:
        print(f'Предупреждение: {fname}: {e}')
"

echo "📦 Сборка Linux архива: dist/tg-discord-rpc-linux.zip..."
zip -j "$DIST_DIR/tg-discord-rpc-linux.zip" \
    telegram_rpc.py \
    config.json \
    telegram-discord-rpc.service \
    install_service.sh \
    uninstall_service.sh \
    start.sh \
    README.md \
    .gitignore \
    .gitattributes

echo "📦 Сборка Windows архива: dist/tg-discord-rpc-windows.zip..."
zip -j "$DIST_DIR/tg-discord-rpc-windows.zip" \
    telegram_rpc.py \
    config.json \
    start_windows.bat \
    install_autostart_windows.bat \
    uninstall_autostart_windows.bat \
    requirements-windows.txt \
    README.md \
    .gitignore \
    .gitattributes

echo ""
echo "✅ Архивы успешно собраны в папке dist/:"
ls -lh "$DIST_DIR"
echo ""
echo "Для создания релиза на GitHub выполните:"
echo "  gh release create v1.0.0 dist/*.zip --title \"Telegram Discord RPC v1.0.0\" --notes \"Полноценная поддержка Linux и Windows\""
echo "или загрузите файлы вручную на странице: https://github.com/goggi22/tg-discord-rpc/releases/new"
echo ""
