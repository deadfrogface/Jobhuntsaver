@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" exit /b 1
call .venv\Scripts\activate.bat
set PYTHONPATH=%cd%
python -m app.main
exit /b %ERRORLEVEL%
