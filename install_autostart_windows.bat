@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "VBS_FILE=%SCRIPT_DIR%run_background.vbs"

echo ========================================================
echo   Установка Music RPC в автозагрузку Windows
echo ========================================================
echo.

:: Проверка наличия автономного EXE файла
if exist "%SCRIPT_DIR%music-rpc.exe" (
    echo [OK] Обнаружен автономный music-rpc.exe.
    (
    echo Set WshShell = CreateObject("WScript.Shell"^)
    echo WshShell.CurrentDirectory = "%SCRIPT_DIR:~0,-1%"
    echo WshShell.Run """%SCRIPT_DIR%music-rpc.exe""", 0, False
    ) > "%VBS_FILE%"
    goto :register_run
)

if exist "%SCRIPT_DIR%dist\music-rpc.exe" (
    echo [OK] Обнаружен автономный dist\music-rpc.exe.
    (
    echo Set WshShell = CreateObject("WScript.Shell"^)
    echo WshShell.CurrentDirectory = "%SCRIPT_DIR%dist"
    echo WshShell.Run """%SCRIPT_DIR%dist\music-rpc.exe""", 0, False
    ) > "%VBS_FILE%"
    goto :register_run
)

:: Поиск Python (если EXE не найден)
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
    echo [ОШИБКА] Python или music-rpc.exe не обнаружены в системе!
    pause
    exit /b 1
)

:: Проверка библиотек
%PY_CMD% -c "import PySide6" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Установка библиотек...
    %PY_CMD% -m pip install -r requirements-windows.txt
)

:: Создаем VBS-скрипт для запуска в трее
(
echo Set WshShell = CreateObject("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%SCRIPT_DIR:~0,-1%"
echo On Error Resume Next
echo WshShell.Run "pythonw main.py", 0, False
echo If Err.Number ^<^> 0 Then
echo     WshShell.Run "python main.py", 0, False
echo End If
) > "%VBS_FILE%"

:register_run

:: Реестр автозагрузки
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "MusicRPC" /t REG_SZ /d "wscript.exe \"%VBS_FILE%\"" /f >nul

echo [OK] Успешно добавлено в автозагрузку Windows!
echo Приложение будет автоматически запускаться в трее при входе в систему.
echo.
echo Запускаем службу прямо сейчас в фоне...
wscript.exe "%VBS_FILE%"
echo [OK] Служба запущена.
echo.
pause
