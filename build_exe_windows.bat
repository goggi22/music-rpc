@echo off
chcp 65001 >nul
title Сборка Music RPC в автономный EXE

echo ========================================================
echo   Сборка Music RPC в единый исполняемый файл (.exe)
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. Поиск Python
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
    pause
    exit /b 1
)

echo [OK] Используется интерпретатор:
%PY_CMD% --version
echo.

:: 2. Установка зависимостей сборки
echo [1/3] Установка PyInstaller и PySide6...
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install pyinstaller PySide6 -r requirements-windows.txt
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось установить сборочные пакеты!
    pause
    exit /b 1
)

:: 3. Сборка одного EXE файла
echo.
echo [2/3] Компиляция приложения в standalone music-rpc.exe...
%PY_CMD% -m PyInstaller ^
    --noconsole ^
    --onefile ^
    --name "music-rpc" ^
    --collect-all PySide6 ^
    --hidden-import winrt.windows.media.control ^
    --hidden-import winsdk.windows.media.control ^
    main.py

if %errorlevel% neq 0 (
    echo [ОШИБКА] Сборка завершилась с ошибкой!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [OK] Готово! Исполняемый файл собран:
echo      dist\music-rpc.exe
echo.
echo Этот файл абсолютно автономен и не требует установленного
echo Python или библиотек на компьютере пользователя.
echo ========================================================
echo.
pause
