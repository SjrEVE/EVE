@echo off
chcp 65001 >nul
title FILA-BOT UNIFIED CONTROL CENTER
cd /d "%~dp0"
set PYTHONPATH=src

:MENU
cls
echo ======================================================================
echo              FILA-BOT — TRUNG TAM DIEU KHIEN EVE ONLINE
echo ======================================================================
echo.
echo   [1] 🚚 Chay Distribution (Courier) — LIVE (Thuc thi bam phim that vao EVE)
echo   [2] 🧪 Chay Distribution (Courier) — DRY-RUN (An toan, chi log, khong bam)
echo   [3] 🌌 Chay Abyssal Deadspace — LIVE (Client that)
echo   [4] 🎮 Chay Abyssal Deadspace — SIM (Gia lap test logic)
echo.
echo   [5] 📊 Kiem tra trang thai EVE Client (WorldSnapshot)
echo   [6] 🖥️ Mo Cua So Giao Dien Do Hoa (GUI Dashboard)
echo   [7] 🔍 Mo Cong Cu Soi Giao Dien DOM (Visual UI Inspector)
echo   [8] 🩺 Kiem Tra Toan Bo Ma Nguon (Health Check 25 Suites / 369 Tests)
echo.
echo   [0] Thoat
echo ======================================================================
set /p opt="Chon che do hoat dong (0-8): "

if "%opt%"=="1" goto RUN_DIST_LIVE
if "%opt%"=="2" goto RUN_DIST_DRY
if "%opt%"=="3" goto RUN_ABYSS_LIVE
if "%opt%"=="4" goto RUN_ABYSS_SIM
if "%opt%"=="5" goto RUN_STATUS
if "%opt%"=="6" goto RUN_GUI
if "%opt%"=="7" goto RUN_INSPECTOR
if "%opt%"=="8" goto RUN_TESTS
if "%opt%"=="0" exit /b 0
goto MENU

:RUN_DIST_LIVE
cls
echo ======================================================================
echo   CHAY DISTRIBUTION COURIER — LIVE (BAM PHIM THAT)
echo ======================================================================
echo CANH BAO: Bot se thuc thi click chuot va bam phim that vao EVE client!
echo Bam Ctrl+C bat ky luc nao de dung bot an toan.
echo.
set /p missions="Nhap so luong nhiem vu muon chay (mac dinh 5): "
if "%missions%"=="" set missions=5
python -u -m fila_bot.cli distribution --live --confirm-input --max-missions %missions%
echo.
pause
goto MENU

:RUN_DIST_DRY
cls
echo ======================================================================
echo   CHAY DISTRIBUTION COURIER — DRY-RUN (AN TOAN)
echo ======================================================================
echo Che do an toan: Bot doc game that nhung KHONG gui phim/chuot.
echo.
set /p missions="Nhap so luong nhiem vu muon thu (mac dinh 3): "
if "%missions%"=="" set missions=3
python -u -m fila_bot.cli distribution --live --max-missions %missions%
echo.
pause
goto MENU

:RUN_ABYSS_LIVE
cls
echo ======================================================================
echo   CHAY ABYSSAL DEADSPACE — LIVE (CLIENT THAT)
echo ======================================================================
set /p fila="Nhap ten filament (mac dinh: Tranquil Exotic Filament): "
if "%fila%"=="" set fila=Tranquil Exotic Filament
python -u -m fila_bot.cli abyss --live --confirm-input --filament "%fila%"
echo.
pause
goto MENU

:RUN_ABYSS_SIM
cls
echo ======================================================================
echo   CHAY ABYSSAL DEADSPACE — SIM (GIA LAP TEST)
echo ======================================================================
python -u -m fila_bot.cli abyss --filament "Tranquil Exotic Filament"
echo.
pause
goto MENU

:RUN_STATUS
cls
python -m fila_bot.cli status
echo.
pause
goto MENU

:RUN_GUI
cls
echo Dang khoi dong Giao dien Do hoa (Tkinter Dashboard)...
python -m fila_bot.ui
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
python tests/run_all.py
echo.
pause
goto MENU
