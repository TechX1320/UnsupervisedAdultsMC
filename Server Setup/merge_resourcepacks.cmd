@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
where py >nul 2>nul
if not errorlevel 1 (
  set "PYCMD=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11+ required on your OWNER PC only.
    pause
    exit /b 1
  )
  set "PYCMD=python"
)
%PYCMD% tools\merge_resourcepacks.py
if errorlevel 1 (
  echo Merge FAILED. Check the messages above.
  pause
  exit /b 1
)
echo.
echo Merged resource pack is in "Server Setup\resourcepacks\output".
echo Host the ZIP over HTTPS and set the URL in Crafty server.properties.
pause
