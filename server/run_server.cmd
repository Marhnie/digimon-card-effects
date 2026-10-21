@echo off
rem Judge-helper server keeper (E34): runs server/app.py and restarts it 10 s after it stops.
rem Started hidden at logon by the scheduled task "Digimon Judge Server" (server\install_task.cmd).
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
:loop
echo [%date% %time%] start >> server\server.log
python server\app.py >> server\server.log 2>&1
echo [%date% %time%] stopped (exit %errorlevel%), restarting in 10 s >> server\server.log
timeout /t 10 /nobreak > nul
goto loop
