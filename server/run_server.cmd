@echo off
rem Judge-helper server keeper (E34): runs server/app.py and restarts it 10 s after it stops.
rem Started hidden at logon by Startup\DigimonJudgeServer.vbs -> server\run_server_hidden.vbs.
rem Python: %JUDGE_PYTHON% if set, else "python" on PATH, else the Microsoft Store alias in %LOCALAPPDATA%.
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set PY=%JUDGE_PYTHON%
if "%PY%"=="" where python >nul 2>&1 && set PY=python
if "%PY%"=="" if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" set PY="%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
if "%PY%"=="" set PY=py
:loop
echo [%date% %time%] start (%PY%) >> server\server.log
%PY% server\app.py >> server\server.log 2>&1
echo [%date% %time%] stopped (exit %errorlevel%), restarting in 10 s >> server\server.log
timeout /t 10 /nobreak > nul
goto loop
