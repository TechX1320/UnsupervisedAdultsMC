@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
echo.
echo ======================================
echo   UNSUPERVISED SMP - SERVER MODPACK
 echo ======================================
echo.
where py >nul 2>nul
if not errorlevel 1 (
  set "PYCMD=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11+ is needed on YOUR OWNER PC to generate the server pack.
    echo Your friends do NOT need Python. https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set "PYCMD=python"
)
echo Step 1 of 2: Pin 1.21.1 Fabric mod versions and dependencies...
%PYCMD% tools\update_pack.py
if errorlevel 1 goto :error
echo.
echo Step 2 of 2: Download verified server JARs...
%PYCMD% tools\export_server.py
if errorlevel 1 goto :error
echo.
echo SUCCESS. Mods are in "Server Setup\mods".
echo Also see "Server Setup\installed-mods.md" and "Server Setup\unavailable-mods.txt".
echo IMPORTANT: Commit pack\catalog.json and pack\pack-lock.json to GitHub main.
echo WARNING: Stop Crafty and back up your world before uploading files.
pause
exit /b 0
:error
echo.
echo FAILED: Read the message above. Existing server mods are preserved on a download error.
pause
exit /b 1
