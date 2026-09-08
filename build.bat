@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Jobhuntsaver Build ===

if not exist ".venv\Scripts\python.exe" (
  echo [1/8] Creating virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Failed to create venv.
    exit /b 1
  )
) else (
  echo [1/8] Virtual environment found.
)

call ".venv\Scripts\activate.bat"

echo [2/8] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency install failed.
  exit /b 1
)

echo [3/8] Running tests...
python -m pytest -q
if errorlevel 1 (
  echo Tests failed — build aborted.
  exit /b 1
)

echo [4/8] Preparing bundled Playwright Chromium...
python packaging\prepare_browsers.py
if errorlevel 1 (
  echo Browser prepare failed.
  exit /b 1
)

echo [5/8] Building EXE with PyInstaller...
if not exist "dist" mkdir dist
if not exist "build" mkdir build
python -m PyInstaller --noconfirm --clean packaging\Jobhuntsaver.spec
if errorlevel 1 (
  echo PyInstaller failed.
  exit /b 1
)

echo [6/8] Copying config templates, assets, and Chromium...
if not exist "dist\Jobhuntsaver\config" mkdir "dist\Jobhuntsaver\config"
copy /Y "config\*.example" "dist\Jobhuntsaver\config\" >nul
if not exist "dist\Jobhuntsaver\templates" mkdir "dist\Jobhuntsaver\templates"
copy /Y "templates\cover_letter.txt" "dist\Jobhuntsaver\templates\" >nul
if exist "dist\Jobhuntsaver\ms-playwright" rmdir /S /Q "dist\Jobhuntsaver\ms-playwright"
xcopy /E /I /Y "packaging\ms-playwright" "dist\Jobhuntsaver\ms-playwright\" >nul
if errorlevel 1 (
  echo Failed to copy bundled Chromium into dist.
  exit /b 1
)

echo [7/8] Verifying output...
if not exist "dist\Jobhuntsaver\Jobhuntsaver.exe" (
  echo EXE missing: dist\Jobhuntsaver\Jobhuntsaver.exe
  exit /b 1
)
dir /s /b "dist\Jobhuntsaver\ms-playwright\chrome.exe" >nul 2>&1
if errorlevel 1 (
  echo Bundled chrome.exe missing under dist\Jobhuntsaver\ms-playwright
  exit /b 1
)

echo [8/8] Done.
echo.
echo Final EXE:
echo   %CD%\dist\Jobhuntsaver\Jobhuntsaver.exe
echo Bundled browser:
echo   %CD%\dist\Jobhuntsaver\ms-playwright
echo.
echo Note: Settings -^> Browser -^> "Browser-Komponente prüfen" verifies the bundle.
exit /b 0
