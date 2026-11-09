@echo off
chcp 65001 >nul
echo ======================================================
echo   FILA-BOT: KIEM TRA TRANG THAI EVE CLIENT (WORLD SNAPSHOT)
echo ======================================================
cd /d "%~dp0"
set PYTHONPATH=src
python -m fila_bot.cli status
echo.
pause
