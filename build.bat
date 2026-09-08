@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Jobhuntsaver Build ===

if not exist ".venv\Scripts\python.exe" (
  echo [1/7] Creating virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Failed to create venv.
    exit /b 1
  )
) else (
  echo [1/7] Virtual environment found.
)

call ".venv\Scripts\activate.bat"

echo [2/7] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency install failed.
  exit /b 1
)

echo [3/7] Running tests...
python -m pytest -q
if errorlevel 1 (
  echo Tests failed — build aborted.
  exit /b 1
)

echo [4/7] Building EXE with PyInstaller...
if not exist "dist" mkdir dist
if not exist "build" mkdir build
python -m PyInstaller --noconfirm --clean packaging\Jobhuntsaver.spec
if errorlevel 1 (
  echo PyInstaller failed.
  exit /b 1
)

echo [5/7] Copying config templates and assets...
if not exist "dist\Jobhuntsaver\config" mkdir "dist\Jobhuntsaver\config"
copy /Y "config\*.example" "dist\Jobhuntsaver\config\" >nul
if not exist "dist\Jobhuntsaver\templates" mkdir "dist\Jobhuntsaver\templates"
copy /Y "templates\cover_letter.txt" "dist\Jobhuntsaver\templates\" >nul

echo [6/7] Verifying output...
if not exist "dist\Jobhuntsaver\Jobhuntsaver.exe" (
  echo EXE missing: dist\Jobhuntsaver\Jobhuntsaver.exe
  exit /b 1
)

echo [7/7] Done.
echo.
echo Final EXE:
echo   %CD%\dist\Jobhuntsaver\Jobhuntsaver.exe
echo.
echo Note: On first run, use Settings -^> "Browser-Komponente installieren" if Playwright Chromium is missing.
exit /b 0
