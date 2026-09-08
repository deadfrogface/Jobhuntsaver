@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Bitte zuerst setup.bat ausfuehren.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set PYTHONPATH=%cd%
streamlit run ui/app.py --server.headless true --server.port 3847
