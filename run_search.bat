@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Bitte zuerst setup.bat ausfuehren.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set PYTHONPATH=%cd%
python -m app.main --mode search_only
echo.
pause
