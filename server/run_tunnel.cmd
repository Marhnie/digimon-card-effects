@echo off
rem Public quick tunnel for the judge-helper server (E34): https://<random>.trycloudflare.com -> http://127.0.0.1:8787
rem Restarts 15 s after it stops. The current public address is written to server\public_url.txt by watch_tunnel.ps1.
cd /d "%~dp0.."
:loop
echo [%date% %time%] tunnel start > server\tunnel.log
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --no-autoupdate --url http://127.0.0.1:8787 >> server\tunnel.log 2>&1
timeout /t 15 /nobreak > nul
goto loop
