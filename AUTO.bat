@echo off
chcp 65001 >nul
title FILA-BOT AUTO - LIVE SECURITY
cd /d "%~dp0"

REM ======================================================================
REM  AUTO.bat - BAM DUP LA CHAY. Khong can go lenh, khong can chon menu.
REM  Bot tu ket noi EVE client dang mo, doc UI tree, tu bam phim/chuot that.
REM  Mac dinh 1 mission co giam sat. Muon nhieu hon: AUTO.bat 3
REM  Dung an toan bat ky luc nao: Ctrl+C (bot nha phim + dung sach).
REM  CANH BAO: botting vi pham EULA CCP - chi chay acc Boss da chap nhan.
REM ======================================================================

set "PY="
if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\hermes\tools\python-3.14.9+202****1021-win32-x64\python.exe" set "PY=%LOCALAPPDATA%\hermes\tools\python-3.14.9+202****1021-win32-x64\python.exe"
if "%PY%"=="" set "PY=python"

set PYTHONPATH=%~dp0src
set PYTHONIOENCODING=utf-8
set "N=%~1"
if "%N%"=="" set "N=1"

echo ======================================================================
echo   FILA-BOT AUTO - LIVE / BAM PHIM THAT / %N% MISSION
echo ======================================================================
echo  Dang khoi dong... (cold-start reader ~10 giay)
echo  Nhan Ctrl+C de dung an toan. Khong can lam gi them.
echo  Log live: logs\live_latest.log — bam XEM_LOG.bat de mo cua so xem.
echo.

set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

"%PY%" -u -m fila_bot.cli security --live --confirm-input --max-missions %N% --tick 0.5 2>&1 | powershell -NoProfile -Command "$input | ForEach-Object { $_; $_ | Out-File -FilePath '%~dp0logs\live_latest.log' -Append -Encoding utf8 }"
echo.
echo [KET THUC] exit code = %errorlevel%
pause
