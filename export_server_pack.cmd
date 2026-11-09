@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 tools\export_server.py
) else (
  python tools\export_server.py
)
if errorlevel 1 (
  echo.
  echo ERROR: Server pack not created.
  pause
  exit /b 1
)
echo Upload extracted server mod files through Crafty, never give your friends Crafty access.
pause
