@echo off
chcp 65001 >nul
title FILA-BOT — ABYSS OPERATIONS
cd /d "%~dp0"

set "PY="
if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\hermes\tools\python-3.14.9+20261021-win32-x64\python.exe" set "PY=%LOCALAPPDATA%\hermes\tools\python-3.14.9+20261021-win32-x64\python.exe"

if "%PY%"=="" (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        echo "%%i" | findstr /i "WindowsApps" >nul
        if errorlevel 1 if "%PY%"=="" set "PY=%%i"
    )
)

if "%PY%"=="" (
    echo [LOI] Khong tim thay Python de khoi dong Fila-Bot!
    echo Vui long kiem tra bo cai Python hoac copy Python vao thu muc 'python/'.
    echo.
    pause
    exit /b 1
)

set PYTHONPATH=%~dp0src
set PYTHONIOENCODING=utf-8

:MENU
cls
for /f "delims=" %%v in (%~dp0VERSION) do set "FBVER=%%v"
echo ======================================================================
echo              FILA-BOT v%FBVER% — ABYSS-ONLY OPERATIONS
echo ======================================================================
echo.
echo   [1] Chay Abyssal Deadspace — SIM (1 run, khong ket noi EVE)
echo   [2] Mo giao dien dieu khien Abyss
echo   [3] Kiem tra trang thai EVE Client (WorldSnapshot)
echo   [4] Mo Visual UI Inspector
echo   [5] Chay bo test (local-only evidence may SKIP)
echo.
echo   [0] Thoat
echo ======================================================================
set "opt="
set /p opt="Chon (0-5): "
if not defined opt exit /b 0

if "%opt%"=="1" goto RUN_ABYSS_SIM
if "%opt%"=="2" goto RUN_GUI
if "%opt%"=="3" goto RUN_STATUS
if "%opt%"=="4" goto RUN_INSPECTOR
if "%opt%"=="5" goto RUN_TESTS
if "%opt%"=="0" exit /b 0
goto MENU

:RUN_ABYSS_SIM
cls
echo ======================================================================
echo   ABYSSAL DEADSPACE — SIM (1 run; no EVE connection or input)
echo ======================================================================
"%PY%" -u -m fila_bot.cli abyss --filament "Tranquil Exotic Filament" --max-runs 1
echo.
pause
goto MENU

:RUN_STATUS
cls
"%PY%" -m fila_bot.cli status
echo.
pause
goto MENU

:RUN_GUI
cls
echo Dang khoi dong Giao dien Do hoa (Tkinter Dashboard)...
start "" "%PY%" -m fila_bot.ui
goto MENU

:RUN_INSPECTOR
cls
echo Dang mo Visual UI Inspector tren trinh duyet...
start "" "%~dp0tools\inspector.html"
goto MENU

:RUN_TESTS
cls
echo ======================================================================
echo   DANG CHAY TOAN BO TEST SUITE (IN-PROCESS TEST RUNNER)
echo ======================================================================
"%PY%" tests/run_all.py
echo.
pause
goto MENU
