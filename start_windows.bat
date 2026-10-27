@echo off
chcp 65001 >nul
title Music RPC - Discord Presence

echo ========================================================
echo   Music RPC - Spotify, Telegram, SoundCloud CLI
echo ========================================================
echo.

cd /d "%~dp0"

:: 0. Быстрый запуск автономного EXE (если файл присутствует)
if exist "%~dp0music-rpc.exe" (
    "%~dp0music-rpc.exe" %*
    set "EXIT_CODE=%errorlevel%"
    goto :finished
)
if exist "%~dp0dist\music-rpc.exe" (
    "%~dp0dist\music-rpc.exe" %*
    set "EXIT_CODE=%errorlevel%"
    goto :finished
)

:: 1. Поиск интерпретатора Python (поддерживаются все версии от 3.8 до 3.16+)
set "PY_CMD="

py -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto :python_found
)

python -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :python_found
)

python3 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python3"
    goto :python_found
)

for %%V in (316 315 314 313 312 311 310 39 38) do (
    call :check_py "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
    if not "%PY_CMD%"=="" goto :python_found
    call :check_py "%ProgramFiles%\Python%%V\python.exe"
    if not "%PY_CMD%"=="" goto :python_found
    call :check_py "C:\Python%%V\python.exe"
    if not "%PY_CMD%"=="" goto :python_found
)

call :check_py "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not "%PY_CMD%"=="" goto :python_found

echo ========================================================
echo [ОШИБКА] Python не обнаружен в вашей системе!
echo ========================================================
echo.
echo Для работы подходит ЛЮБАЯ версия Python от 3.8 до 3.16+
echo.
echo Как установить:
echo 1. Скачайте Python с официального сайта:
echo    https://www.python.org/downloads/
echo 2. ВАЖНО: В самом начале установки инсталлятора ОБЯЗАТЕЛЬНО
echo    поставьте галочку внизу окна:
echo    [X] Add python.exe to PATH
echo 3. Нажмите "Install Now" и дождитесь окончания установки.
echo 4. После установки запустите этот файл снова.
echo.
goto :error_exit

:check_py
if "%PY_CMD%"=="" (
    if exist "%~1" (
        "%~1" -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set PY_CMD="%~1"
        )
    )
)
exit /b

:python_found
echo [OK] Найден Python:
%PY_CMD% --version
echo.

:: 2. Проверка pip
%PY_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Модуль pip не найден, инициализируем через ensurepip...
    %PY_CMD% -m ensurepip --default-pip >nul 2>&1
)

:: 3. Проверка библиотек Windows Media SMTC
%PY_CMD% -c "import winrt.windows.media.control" >nul 2>&1
if %errorlevel% equ 0 goto :deps_ok

%PY_CMD% -c "import winsdk.windows.media.control" >nul 2>&1
if %errorlevel% equ 0 goto :deps_ok

echo [INFO] Установка библиотеки Windows Media (winsdk)...
%PY_CMD% -m pip install winsdk >nul 2>&1
if %errorlevel% equ 0 goto :deps_ok

%PY_CMD% -m pip install winrt-Windows.Media.Control >nul 2>&1

:deps_ok
:: 4. Запуск Music RPC CLI
%PY_CMD% main.py %*
set "EXIT_CODE=%errorlevel%"

:finished
echo.
if %EXIT_CODE% neq 0 (
    echo ========================================================
    echo [ОШИБКА] Приложение завершилось с кодом: %EXIT_CODE%
    echo ========================================================
    goto :error_exit
) else (
    echo ========================================================
    echo Music RPC завершил работу.
    echo ========================================================
    exit /b 0
)

:error_exit
echo.
echo Нажмите любую клавишу для закрытия...
pause >nul
exit /b %EXIT_CODE%
