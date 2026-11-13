@echo off
chcp 65001 >nul
title FILA-BOT AUTO - ABYSS SIM
cd /d "%~dp0"

REM Abyss-only entrypoint. Always one SIM run; no EVE connection or input.

set "PY="
if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\hermes\tools\python-3.14.9+202****1021-win32-x64\python.exe" set "PY=%LOCALAPPDATA%\hermes\tools\python-3.14.9+202****1021-win32-x64\python.exe"
if "%PY%"=="" set "PY=python"

set PYTHONPATH=%~dp0src
set PYTHONIOENCODING=utf-8
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOGFILE=%LOGDIR%\abyss_sim_latest.log"
type nul > "%LOGFILE%"

echo ======================================================================
echo   FILA-BOT — ABYSS SIM / 1 RUN
echo ======================================================================
echo SIM only: no EVE connection and no mouse or keyboard input.
echo Log: logs\abyss_sim_latest.log
echo Use XEM_LOG.bat in another window to follow the log.
echo.

"%PY%" -u -m fila_bot.cli abyss --filament "Tranquil Exotic Filament" --max-runs 1 > "%LOGFILE%" 2>&1
set "RC=%errorlevel%"
type "%LOGFILE%"
echo.
echo [END] exit code = %RC%
pause
exit /b %RC%
