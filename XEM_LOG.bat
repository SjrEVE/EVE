@echo off
chcp 65001 >nul
title FILA-BOT — LIVE LOG (cua so nay tu cap nhat)
REM Xem truc tiep log moi nhat. Mo bat ky luc nao, khoi canh bao gi cung duoc.
:wait
if not exist "%~dp0logs\live_latest.log" (
  echo Dang cho log dau tien... (chay AUTO.bat hoac launcher)
  timeout /t 2 /nobreak >nul
  goto wait
)
echo === logs\live_latest.log — cap nhat truc tiep, Ctrl+C hoac dong cua so de thoat ===
powershell -NoProfile -Command "Get-Content -Path '%~dp0logs\live_latest.log' -Wait -Tail 40 -Encoding UTF8"
pause
