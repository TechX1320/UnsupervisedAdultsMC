@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo.
echo ===============================================
echo   UNSUPERVISED ADULTS MC - LOCAL WINDOWS BUILD
echo ===============================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Python 3.11 or newer is required.
    echo Download: https://www.python.org/downloads/windows/
    echo Remember to enable Add Python to PATH.
    pause
    exit /b 1
  )
  set "PYCMD=python"
) else (
  set "PYCMD=py -3"
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating local build environment...
  %PYCMD% -m venv .venv
  if errorlevel 1 goto :error
)
echo Running launcher source tests...
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto :error
echo Installing PyInstaller into local venv...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check "pyinstaller>=6.15,<7"
if errorlevel 1 goto :error
echo Building Windows launcher...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name UnsupervisedAdultsMC --add-data "pack\catalog.json;pack" --paths . launcher.py
if errorlevel 1 goto :error
echo.
echo SUCCESS: dist\UnsupervisedAdultsMC.exe
echo You can distribute this EXE. It downloads official Prism on first run.
pause
exit /b 0
:error
echo.
echo BUILD FAILED. Read the error above.
pause
exit /b 1
