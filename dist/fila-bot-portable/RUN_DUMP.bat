@echo off
rem RUN_DUMP.bat — dump UI tree EVE (read-only, không bấm phím gì)
rem Yêu cầu: EVE client đang chạy trên MÁY NÀY trước khi double-click
cd /d "%~dp0"
echo ============================================
echo  fila-bot UI DUMP (chi doc, khong bam phim)
echo  Yeu cau: EVE client DANG CHAY tren may nay
echo ============================================
python\python.exe dump_ui.py --out ui_dump.json
echo.
echo Xong. Gui lai file ui_dump.json cho Hermes.
pause
