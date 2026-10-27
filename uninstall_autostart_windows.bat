@echo off
chcp 65001 >nul

echo ========================================================
echo   Удаление Music RPC из автозагрузки Windows
echo ========================================================
echo.

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "MusicRPC" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "TelegramDiscordRPC" /f >nul 2>&1

del /f /q "%~dp0run_background.vbs" >nul 2>&1

echo [OK] Music RPC успешно удален из автозагрузки Windows.
echo.
pause
