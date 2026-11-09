@echo off
chcp 65001 >nul
echo ======================================================
echo   FILA-BOT: CHAY THU COURIER (DRY-RUN AN TOAN, CHI LOG)
echo ======================================================
cd /d "%~dp0"
set PYTHONPATH=src
python -u -m fila_bot.cli distribution --live --max-missions 5
echo.
pause
