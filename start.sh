#!/usr/bin/env bash
cd "$(dirname "$0")"
PY_BIN="python3"
if [ -f "./.venv/bin/python" ]; then
    PY_BIN="./.venv/bin/python"
fi

exec "$PY_BIN" main.py "$@"
