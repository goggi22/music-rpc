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

:: Поиск Python
set "PY_CMD="
py -c "import sys" >nul 2>&1 && set "PY_CMD=py"
if "%PY_CMD%"=="" python -c "import sys" >nul 2>&1 && set "PY_CMD=python"
if "%PY_CMD%"=="" python3 -c "import sys" >nul 2>&1 && set "PY_CMD=python3"

for %%V in (316 315 314 313 312 311 310 39 38) do (
    if "%PY_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set PY_CMD="%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
    if "%PY_CMD%"=="" if exist "%ProgramFiles%\Python%%V\python.exe" set PY_CMD="%ProgramFiles%\Python%%V\python.exe"
    if "%PY_CMD%"=="" if exist "C:\Python%%V\python.exe" set PY_CMD="C:\Python%%V\python.exe"
)

if "%PY_CMD%"=="" (
    echo [ОШИБКА] Python не обнаружен в системе!
    echo Установите любую версию Python от 3.8 до 3.16+ с галочкой "Add to PATH".
    pause
    exit /b 1
)

:: Проверка библиотек
%PY_CMD% -c "import winrt.windows.media.control" >nul 2>&1
if %errorlevel% neq 0 (
    %PY_CMD% -c "import winsdk.windows.media.control" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INFO] Установка библиотек Windows Media...
        %PY_CMD% -m pip install -r requirements-windows.txt
        if %errorlevel% neq 0 (
            %PY_CMD% -m pip install winrt-Windows.Media.Control
        )
    )
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
