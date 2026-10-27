@echo off
chcp 65001 >nul
title Music RPC

echo ========================================================
echo   Music RPC - Spotify, Telegram, SoundCloud для Windows
echo ========================================================
echo.

cd /d "%~dp0"

:: 0. Быстрый запуск автономного EXE (если файл уже скомпилирован)
if exist "%~dp0music-rpc.exe" (\
    echo [OK] Обнаружен автономный файл music-rpc.exe!
    echo Запуск приложения...
    start "" "%~dp0music-rpc.exe" %*
    exit /b 0
)
if exist "%~dp0dist\music-rpc.exe" (
    echo [OK] Обнаружен автономный файл dist\music-rpc.exe!
    echo Запуск приложения...
    start "" "%~dp0dist\music-rpc.exe" %*
    exit /b 0
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
echo [OK] Найден интерпретатор Python:
%PY_CMD% --version
echo.

:: 2. Проверка pip
%PY_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Модуль pip не найден, пробуем инициализировать через ensurepip...
    %PY_CMD% -m ensurepip --default-pip >nul 2>&1
)

:: 3. Проверка библиотек (PySide6 и Windows Media)
echo [1/2] Проверка установленных библиотек...
%PY_CMD% -c "import PySide6" >nul 2>&1
if %errorlevel% neq 0 goto :install_deps

%PY_CMD% -c "import winrt.windows.media.control" >nul 2>&1
if %errorlevel% equ 0 goto :deps_ok

%PY_CMD% -c "import winsdk.windows.media.control" >nul 2>&1
if %errorlevel% equ 0 goto :deps_ok

:install_deps
echo [INFO] Установка необходимых библиотек (PySide6, Windows Media SDK)...
echo.
%PY_CMD% -m pip install -r requirements-windows.txt
if %errorlevel% equ 0 goto :deps_installed

echo [INFO] Попытка установки напрямую...
%PY_CMD% -m pip install PySide6 winrt-Windows.Media.Control
if %errorlevel% equ 0 goto :deps_installed

echo.
echo [ОШИБКА] Не удалось автоматически установить библиотеки!
echo Проверьте подключение к интернету или запустите вручную:
echo   %PY_CMD% -m pip install -r requirements-windows.txt
goto :error_exit

:deps_installed
echo.
echo [OK] Библиотеки успешно установлены!
echo.
goto :deps_done

:deps_ok
echo [OK] Все библиотеки уже установлены.
echo.

:deps_done
:: 4. Запуск Music RPC
echo [2/2] Запуск графического интерфейса Music RPC...
echo ========================================================
echo.

%PY_CMD% main.py
set "EXIT_CODE=%errorlevel%"

echo.
if %EXIT_CODE% neq 0 (
    echo ========================================================
    echo [ОШИБКА] Приложение завершилось с кодом: %EXIT_CODE%
    echo ========================================================
) else (
    echo ========================================================
    echo Приложение завершило работу.
    echo ========================================================
)

:error_exit
echo.
echo Нажмите любую клавишу для закрытия этого окна...
pause >nul
exit /b %EXIT_CODE%
