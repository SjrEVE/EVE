@echo off
REM fila-bot UI — mo cua so Start/Pause/Stop/E-STOP
cd /d "%~dp0"

set "PY="
if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\hermes\tools\python-3.14.9+20261021-win32-x64\python.exe" set "PY=%LOCALAPPDATA%\hermes\tools\python-3.14.9+20261021-win32-x64\python.exe"
if "%PY%"=="" set "PY=python"

set PYTHONPATH=%~dp0src
set PYTHONIOENCODING=utf-8

"%PY%" -m fila_bot.ui %*
if errorlevel 1 pause
