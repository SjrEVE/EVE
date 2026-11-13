@echo off
chcp 65001 >nul
title FILA-BOT — ABYSS SIM LOG
REM Follow the most recent SIM run. This is not the live-client log.
:wait
if not exist "%~dp0logs\abyss_sim_latest.log" (
  echo Waiting for Abyss SIM log... (run AUTO.bat or the Abyss SIM launcher)
  timeout /t 2 /nobreak >nul
  goto wait
)
echo === logs\abyss_sim_latest.log — Ctrl+C or close this window to exit ===
powershell -NoProfile -Command "Get-Content -Path '%~dp0logs\abyss_sim_latest.log' -Wait -Tail 40 -Encoding UTF8"
pause
