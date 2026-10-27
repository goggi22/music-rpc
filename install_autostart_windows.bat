@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "VBS_FILE=%SCRIPT_DIR%run_background.vbs"

echo ========================================================
echo   Установка Telegram Discord RPC в автозагрузку Windows
echo ========================================================
echo.

python -c "import winsdk" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Установка библиотеки Windows Media SDK (winsdk)...
    pip install -r requirements-windows.txt
)

:: Создаем VBS-скрипт для абсолютно тихого запуска без консольного окна
(
echo Set WshShell = CreateObject("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%SCRIPT_DIR:~0,-1%"
echo WshShell.Run "pythonw telegram_rpc.py", 0, False
) > "%VBS_FILE%"

:: Добавляем в ветку автозагрузки текущего пользователя (права администратора НЕ требуются)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "TelegramDiscordRPC" /t REG_SZ /d "wscript.exe \"%VBS_FILE%\"" /f >nul

echo [OK] Успешно добавлено в автозагрузку Windows!
echo Сервис будет запускаться незаметно в фоне при каждом входе в систему.
echo.
echo Запускаем службу прямо сейчас в фоновом режиме...
wscript.exe "%VBS_FILE%"
echo [OK] Служба запущена в фоне.
echo.
pause
