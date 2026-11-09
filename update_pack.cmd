@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 tools\update_pack.py
) else (
  python tools\update_pack.py
)
if errorlevel 1 (
  echo Pack resolution reported an error.
  pause
  exit /b 1
)
echo.
echo IMPORTANT: Commit pack\pack-lock.json to GitHub main.
echo This is what pins exactly the same mod files for every friend.
pause
