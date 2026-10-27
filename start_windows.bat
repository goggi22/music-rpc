@echo off
chcp 65001 >nul
title Telegram Discord RPC

echo ========================================================
echo   Telegram Discord Rich Presence (RPC) для Windows
echo ========================================================
echo.

cd /d "%~dp0"

python -c "import winsdk" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Установка библиотеки Windows Media SDK (winsdk)...
    pip install -r requirements-windows.txt
    if %errorlevel% neq 0 (
        echo [ОШИБКА] Не удалось установить winsdk. Убедитесь, что Python и pip установлены в PATH.
        pause
        exit /b 1
    )
)

echo [INFO] Запуск Discord RPC для Telegram...
python telegram_rpc.py
if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Скрипт завершил работу с кодом %errorlevel%.
    pause
)
