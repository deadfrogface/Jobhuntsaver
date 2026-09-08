@echo off
REM Optional: Windows Task Scheduler helper
REM Creates a daily task at 08:00 to run Jobhuntsaver search/apply once and exit.
setlocal
cd /d "%~dp0"
set TASK_NAME=JobhuntsaverMorning
set SCRIPT=%cd%\scripts\scheduled_run.bat

schtasks /Create /F /TN "%TASK_NAME%" /SC DAILY /ST 08:00 /TR "\"%SCRIPT%\"" /RL LIMITED
if errorlevel 1 (
  echo Konnte Aufgabe nicht erstellen. Als Administrator ausfuehren?
  exit /b 1
)
echo Aufgabe "%TASK_NAME%" erstellt (taeglich 08:00).
echo Zum Aendern: Taskplaner oeffnen oder:
echo   schtasks /Change /TN "%TASK_NAME%" /ST 18:00
endlocal
