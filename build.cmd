@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo.
echo =====================================================
echo   UNSUPERVISED ADULTS MC - LOCAL WINDOWS EXE BUILD
 echo =====================================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Python 3.11+ required ON YOUR BUILD PC ONLY.
    echo Download: https://www.python.org/downloads/windows/
    echo Select Add Python to PATH during installation.
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
echo Installing pinned build dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 goto :error
echo Running source tests...
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto :error
echo Building single-file Windows launcher...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name UnsupervisedAdultsMC --add-data "pack\catalog.json;pack" --paths . launcher.py
if errorlevel 1 goto :error
echo.
echo SUCCESS: dist\UnsupervisedAdultsMC.exe
echo Share this EXE; friends do not need Python or a separate Prism install.
echo It will install verified Prism Portable into UnsupervisedAdultsMC_Data beside the EXE.
echo NOTE: Microsoft login happens in the Prism window on first run only.
pause
exit /b 0
:error
echo.
echo BUILD FAILED. Read the error above.
pause
exit /b 1
