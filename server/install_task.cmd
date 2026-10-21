@echo off
rem Register / remove the logon task that keeps the judge-helper server running.
rem   install_task.cmd          register and start now
rem   install_task.cmd remove   stop and unregister
set TN=Digimon Judge Server
if /i "%1"=="remove" (
  schtasks /end /tn "%TN%" > nul 2>&1
  schtasks /delete /tn "%TN%" /f
  taskkill /f /fi "WINDOWTITLE eq run_server*" > nul 2>&1
  goto :eof
)
schtasks /create /tn "%TN%" /sc onlogon /rl limited /f /tr "wscript.exe \"%~dp0run_server_hidden.vbs\""
schtasks /run /tn "%TN%"
