@echo off
rem START.bat — bật fila-bot (sim mode, KHÔNG bấm phím thật)
rem Live mode + bấm thật chỉ bật khi đã test dump UI ok + hiểu rủi ro
cd /d "%~dp0"
echo ============================================
echo  fila-bot (SIM — trang thai gia, khong dam EVE)
echo ============================================
python\python.exe -c "import sys; sys.path.insert(0,'src'); from fila_bot.main import main; sys.exit(main())" --mode sim
pause
