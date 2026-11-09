@echo off
REM fila-bot UI — mo cua so Start/Pause/Stop/E-STOP
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
python -m fila_bot.ui %*
if errorlevel 1 pause
