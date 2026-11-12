@echo off
chcp 65001 >nul
title FILA-BOT UNIFIED CONTROL CENTER
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
echo              FILA-BOT v%FBVER% — TRUNG TAM DIEU KHIEN EVE ONLINE
echo ======================================================================
echo.
echo   [1] 🚚 Chay Distribution (Courier) — LIVE (Thuc thi bam phim that vao EVE)
echo   [2] 🧪 Chay Distribution (Courier) — DRY-RUN (An toan, chi log, khong bam)
echo   [3] ⚔️ Chay Security (PvE Combat) — LIVE (BAM PHIM THAT — Gila / Cruiser)
echo   [4] 🛡️ Chay Security (PvE Combat) — DRY-RUN (An toan, chi log, khong bam)
echo   [5] 🌌 Chay Abyssal Deadspace — LIVE (CANH BAO: chua ground undock/fila/gate)
echo   [6] 🎮 Chay Abyssal Deadspace — SIM (Gia lap test logic)
echo.
echo   [7] 📊 Kiem tra trang thai EVE Client (WorldSnapshot)
echo   [8] 🖥️ Mo Cua So Giao Dien Do Hoa (GUI Dashboard)
echo   [9] 🔍 Mo Cong Cu Soi Giao Dien DOM (Visual UI Inspector)
echo   [10] 🩺 Kiem Tra Toan Bo Ma Nguon (Health Check — tat ca 31 suites)
echo   [11] 🧠 Abyss SIM voi Behavior Tree (engine=bt, so sanh voi FSM)
echo   [12] ✅ Security E2E SIM (vong lap day du toi IDLE_DONE, 1 mission)
echo.
echo   [0] Thoat
echo ======================================================================
set /p opt="Chon che do hoat dong (0-12): "

if "%opt%"=="1" goto RUN_DIST_LIVE
if "%opt%"=="2" goto RUN_DIST_DRY
if "%opt%"=="3" goto RUN_SEC_LIVE
if "%opt%"=="4" goto RUN_SEC_DRY
if "%opt%"=="5" goto RUN_ABYSS_LIVE
if "%opt%"=="6" goto RUN_ABYSS_SIM
if "%opt%"=="7" goto RUN_STATUS
if "%opt%"=="8" goto RUN_GUI
if "%opt%"=="9" goto RUN_INSPECTOR
if "%opt%"=="10" goto RUN_TESTS
if "%opt%"=="11" goto RUN_ABYSS_BT
if "%opt%"=="12" goto RUN_SEC_E2E_SIM
if "%opt%"=="0" exit /b 0
goto MENU

:RUN_SEC_LIVE
cls
echo ======================================================================
echo   CHAY SECURITY (PVE COMBAT) — LIVE (BAM PHIM THAT — GILA DOCTRINE)
echo ======================================================================
echo CANH BAO: Bot se thuc thi click chuot va bam phim that vao EVE client!
echo - Orbit site 30km, bat Afterburner
echo - Target lock & phong drone, recall drone khi bi target
echo Bam Ctrl+C bat ky luc nao de dung bot an toan.
echo.
set /p missions="Nhap so luong nhiem vu muon chay (mac dinh 3): "
if "%missions%"=="" set missions=3
"%PY%" -u -m fila_bot.cli security --live --confirm-input --max-missions %missions%
echo.
pause
goto MENU

:RUN_SEC_DRY
cls
echo ======================================================================
echo   CHAY SECURITY (PVE COMBAT) — DRY-RUN (AN TOAN)
echo ======================================================================
echo Che do an toan: Bot doc game that nhung KHONG gui phim/chuot.
echo.
set /p missions="Nhap so luong nhiem vu muon thu (mac dinh 3): "
if "%missions%"=="" set missions=3
"%PY%" -u -m fila_bot.cli security --live --max-missions %missions%
echo.
pause
goto MENU

:RUN_SEC_E2E_SIM
cls
echo ======================================================================
echo   SECURITY E2E SIM — vong lap day du, khong can EVE client
echo ======================================================================
echo Nhan offer -> undock -> warp site -> combat -> ve tram -> Complete
echo -> read-back -> IDLE_DONE. Chi log, KHONG gui phim/chuot that.
echo.
"%PY%" -u -m fila_bot.cli security --max-missions 1 --tick 0.15
echo.
pause
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
set /p sec="Bo qua kiem tra sec route? (y/N — mac dinh N = fail-closed): "
set "SECFLAG="
if /i "%sec%"=="y" set "SECFLAG=--allow-unknown-sec"
"%PY%" -u -m fila_bot.cli distribution --live --confirm-input --max-missions %missions% %SECFLAG%
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
"%PY%" -u -m fila_bot.cli distribution --live --max-missions %missions%
echo.
pause
goto MENU

:RUN_ABYSS_LIVE
cls
echo ======================================================================
echo   CHAY ABYSSAL DEADSPACE — LIVE (CLIENT THAT)
echo ======================================================================
echo CANH BAO: undock / dung filament / gate / dock cua Abyss CHUA ground.
echo Bot se chay guards roi DUNG voi ly do ro rang, KHONG bam mu.
echo.
set /p fila="Nhap ten filament (mac dinh: Tranquil Exotic Filament): "
if "%fila%"=="" set fila=Tranquil Exotic Filament
set /p runs="So run toi da (bo trong = vo han): "
set "RUNFLAG="
if not "%runs%"=="" set "RUNFLAG=--max-runs %runs%"
"%PY%" -u -m fila_bot.cli abyss --live --confirm-input --filament "%fila%" %RUNFLAG%
echo.
pause
goto MENU

:RUN_ABYSS_SIM
cls
echo ======================================================================
echo   CHAY ABYSSAL DEADSPACE — SIM (GIA LAP TEST)
echo ======================================================================
"%PY%" -u -m fila_bot.cli abyss --filament "Tranquil Exotic Filament"
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

:RUN_ABYSS_BT
cls
echo ======================================================================
echo   ABYSS SIM — BEHAVIOR TREE ENGINE (so sanh voi FSM)
echo ======================================================================
"%PY%" -u -m fila_bot.cli abyss --filament "Tranquil Exotic Filament" --engine bt --max-runs 1
echo.
pause
goto MENU
