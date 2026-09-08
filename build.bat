@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Jobhuntsaver Onefile Build ===

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Failed to create venv.
    exit /b 1
  )
) else (
  echo [1/5] Virtual environment found.
)

call ".venv\Scripts\activate.bat"

echo [2/5] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements-runtime.txt
python -m pip install -r requirements-dev.txt
if errorlevel 1 (
  echo Dependency install failed.
  exit /b 1
)

echo [3/5] Running tests...
python -m pytest -q
if errorlevel 1 (
  echo Tests failed — build aborted.
  exit /b 1
)

echo [4/5] Building ONEFILE EXE (Chromium NOT bundled)...
if not exist "dist" mkdir dist
if not exist "build" mkdir build
python -m PyInstaller --noconfirm --clean packaging\Jobhuntsaver.spec
if errorlevel 1 (
  echo PyInstaller failed.
  exit /b 1
)

echo [5/5] Verifying output...
if not exist "dist\Jobhuntsaver.exe" (
  echo EXE missing: dist\Jobhuntsaver.exe
  exit /b 1
)
if exist "dist\Jobhuntsaver\ms-playwright" (
  echo ERROR: Chromium must not be bundled.
  exit /b 1
)

echo.
echo Final artifact:
echo   %CD%\dist\Jobhuntsaver.exe
echo Browser installs on demand to:
echo   %%LOCALAPPDATA%%\Jobhuntsaver\browsers
exit /b 0
