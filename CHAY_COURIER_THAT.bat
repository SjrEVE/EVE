@echo off
chcp 65001 >nul
echo ======================================================
echo   FILA-BOT: CHAY THAT COURIER (CONFIRM-INPUT BAM PHIM/CHUOT)
echo ======================================================
echo CANH BAO: Bot se thuc thi click chuot va bam phim that vao EVE!
echo Nhan Ctrl+C bat ky luc nao de dung bot an toan.
echo.
pause
cd /d "%~dp0"
set PYTHONPATH=src
python -u -m fila_bot.cli distribution --live --confirm-input --max-missions 5
echo.
pause
