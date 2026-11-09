@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo.
echo =====================================================
echo   UNSUPERVISED ADULTS MC - ALL-IN-ONE WINDOWS BUILD
echo =====================================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Python 3.11+ is needed ON THIS BUILD PC ONLY.
    echo Download: https://www.python.org/downloads/windows/
    echo Enable Add Python to PATH during installation.
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
echo Installing pinned build libraries...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 goto :error
echo.
echo Running launcher tests...
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto :error
echo Building standalone Windows EXE...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name UnsupervisedAdultsMC --add-data "pack\catalog.json;pack" --collect-submodules minecraft_launcher_lib --paths . launcher.py
if errorlevel 1 goto :error
echo.
echo SUCCESS: dist\UnsupervisedAdultsMC.exe
echo This is the only program your friends need to download.
echo Keep the EXE in a writable folder (not Program Files).
echo A UnsupervisedAdultsMC_Data folder is created beside the EXE.
echo Minecraft, Java, Fabric and mods are fetched on first run.
pause
exit /b 0
:error
echo.
echo BUILD FAILED. Read the error above.
pause
exit /b 1
