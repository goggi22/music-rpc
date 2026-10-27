#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DIST_DIR="$SCRIPT_DIR/dist"
mkdir -p "$DIST_DIR"

echo "=========================================================="
echo "  Сборка релизных архивов Music RPC (Spotify, Telegram, SoundCloud)"
echo "=========================================================="

# Убеждаемся, что файлы для Windows имеют переносы строк CRLF (\r\n)
python3 -c "
for fname in [
    'start_windows.bat',
    'build_exe_windows.bat',
    'install_autostart_windows.bat',
    'uninstall_autostart_windows.bat',
    'requirements-windows.txt'
]:
    try:
        with open(fname, 'rb') as f:
            data = f.read()
        crlf = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n').replace(b'\n', b'\r\n')
        with open(fname, 'wb') as f:
            f.write(crlf)
    except Exception as e:
        print(f'Предупреждение: {fname}: {e}')
"

echo "📦 Сборка Linux архива: dist/music-rpc-linux.zip..."
zip -r "$DIST_DIR/music-rpc-linux.zip" \
    main.py \
    music_rpc \
    config.json \
    music-rpc.service \
    install_service.sh \
    uninstall_service.sh \
    start.sh \
    requirements.txt \
    README.md \
    .gitignore \
    .gitattributes \
    -x "*/__pycache__/*" "*__pycache__*"

echo "📦 Сборка Windows архива: dist/music-rpc-windows.zip..."
zip -r "$DIST_DIR/music-rpc-windows.zip" \
    main.py \
    music_rpc \
    config.json \
    start_windows.bat \
    build_exe_windows.bat \
    install_autostart_windows.bat \
    uninstall_autostart_windows.bat \
    requirements-windows.txt \
    README.md \
    .gitignore \
    .gitattributes \
    -x "*/__pycache__/*" "*__pycache__*"

echo ""
echo "✅ Архивы успешно собраны в папке dist/:"
ls -lh "$DIST_DIR"
echo ""
