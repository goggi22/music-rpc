@echo off
chcp 65001 >nul

echo ========================================================
echo   Удаление Telegram Discord RPC из автозагрузки Windows
echo ========================================================
echo.

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "TelegramDiscordRPC" /f >nul 2>&1
del /f /q "%~dp0run_background.vbs" >nul 2>&1

:: Завершаем фоновый процесс pythonw если он запущен
taskkill /f /im pythonw.exe >nul 2>&1

echo [OK] Служба успешно удалена из автозагрузки и остановлена.
echo.
pause
