#!/usr/bin/env sh
# Judge-helper server keeper for Linux/macOS (E34): restarts the server 10 s after it stops.
#   sh server/run_server.sh                 # listens on 127.0.0.1:8787
#   HOST=0.0.0.0 sh server/run_server.sh    # all interfaces
# Optional public quick tunnel (needs cloudflared):  cloudflared tunnel --url http://127.0.0.1:8787
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
while true; do
  echo "[$(date)] start" >> server/server.log
  python3 server/app.py >> server/server.log 2>&1
  echo "[$(date)] stopped ($?), restarting in 10 s" >> server/server.log
  sleep 10
done
