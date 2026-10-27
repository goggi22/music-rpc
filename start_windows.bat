@echo off
chcp 65001 >nul
title Telegram Discord RPC

echo ========================================================
echo   Telegram Discord Rich Presence (RPC) для Windows
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. Поиск интерпретатора Python (поддерживаются все версии от 3.8 до 3.16+)
set "PY_CMD="

:: Проверяем официальный лаунчер Python (py.exe)
py -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto :python_found
)

:: Проверяем команду python в системном PATH
python -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :python_found
)

:: Проверяем команду python3 в системном PATH
python3 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python3"
    goto :python_found
)

:: Проверяем стандартные пути установки Python (если не была включена опция Add to PATH)
for %%V in (316 315 314 313 312 311 310 39 38) do (
    call :check_py "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
    if not "%PY_CMD%"=="" goto :python_found
    call :check_py "%ProgramFiles%\Python%%V\python.exe"
    if not "%PY_CMD%"=="" goto :python_found
    call :check_py "C:\Python%%V\python.exe"
    if not "%PY_CMD%"=="" goto :python_found
)

:: Проверяем Microsoft Store / WindowsApps
call :check_py "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if not "%PY_CMD%"=="" goto :python_found

:: Если Python не найден нигде
echo ========================================================
echo [ОШИБКА] Python не обнаружен в вашей системе!
echo ========================================================
echo.
echo Для работы подходит ЛЮБАЯ версия Python от 3.8 до 3.16+
echo (например, Python 3.10, 3.11, 3.12, 3.13, 3.14 или новее).
echo.
echo Как установить:
echo 1. Скачайте Python с официального сайта:
echo    https://www.python.org/downloads/
echo.
echo 2. ВАЖНО: В самом начале установки инсталлятора ОБЯЗАТЕЛЬНО
echo    поставьте галочку внизу окна:
echo    [X] Add python.exe to PATH   (или "Add Python to PATH")
echo.
echo 3. Нажмите "Install Now" и дождитесь окончания установки.
echo 4. После установки запустите этот файл (start_windows.bat) снова.
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
    %PY_CMD% -m pip --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ОШИБКА] Не удалось запустить pip!
        echo Рекомендуется переустановить Python с включенной опцией pip.
        goto :error_exit
    )
)

:: 3. Проверка и установка библиотек Windows Media
echo [1/3] Проверка библиотек Windows Media...
%PY_CMD% -c "import winrt.windows.media.control" >nul 2>&1
if %errorlevel% equ 0 goto :deps_ok

%PY_CMD% -c "import winsdk.windows.media.control" >nul 2>&1
if %errorlevel% equ 0 goto :deps_ok

echo [INFO] Библиотека для связи с плеером Windows еще не установлена.
echo [INFO] Устанавливаем необходимые зависимости для вашей версии Python...
echo.

%PY_CMD% -m pip install -r requirements-windows.txt
if %errorlevel% equ 0 goto :deps_installed

:: Если pip с requirements не сработал, пробуем по отдельности
echo [INFO] Попытка установки winrt-Windows.Media.Control...
%PY_CMD% -m pip install winrt-Windows.Media.Control
if %errorlevel% equ 0 goto :deps_installed

echo [INFO] Попытка установки winsdk...
%PY_CMD% -m pip install winsdk
if %errorlevel% equ 0 goto :deps_installed

echo.
echo [ОШИБКА] Не удалось автоматически установить библиотеки!
echo Проверьте подключение к интернету или выполните вручную в командной строке:
echo   %PY_CMD% -m pip install winrt-Windows.Media.Control
echo или:
echo   %PY_CMD% -m pip install winsdk
goto :error_exit

:deps_installed
echo.
echo [OK] Зависимости успешно установлены!
echo.
goto :deps_done

:deps_ok
echo [OK] Все библиотеки уже установлены.
echo.

:deps_done
:: 4. Проверка запущенных программ
echo [2/3] Подготовка к запуску...
echo Подсказка: убедитесь, что запущен Discord (или Vesktop) и Telegram Desktop (или AyuGram).
echo.

:: 5. Запуск скрипта
echo [3/3] Запуск Telegram Discord RPC...
echo ========================================================
echo   Нажмите Ctrl+C в этом окне, чтобы остановить сервис
echo ========================================================
echo.

%PY_CMD% telegram_rpc.py
set "EXIT_CODE=%errorlevel%"

echo.
if %EXIT_CODE% neq 0 (
    echo ========================================================
    echo [ОШИБКА] Скрипт завершился с кодом ошибки: %EXIT_CODE%
    echo ========================================================
) else (
    echo ========================================================
    echo Сервис завершил работу.
    echo ========================================================
)

:error_exit
echo.
echo Нажмите любую клавишу для закрытия этого окна...
pause >nul
exit /b %EXIT_CODE%
