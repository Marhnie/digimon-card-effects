#!/bin/bash
# usage: run_job.sh jobs/x.json  -> jobs/x.out.json (log: jobs/x.log). Hard watchdog 300s (writes fatal=watchdog if the editor hangs).
J=$(cygpath -w "$(realpath "$1")"); O="${J%.json}.out.json"; rm -f "$O"
export DCGO_JOB="$J" DCGO_OUT="$O"
"C:/Users/Daewonmedia/Unity/2021.3.45f2/Editor/Unity.exe" -batchmode -projectPath "C:\Users\Daewonmedia\ext\DCGO" -executeMethod HarnessCli.Run -logFile "${J%.json}.log" &
PID=$!
for i in $(seq 1 ${WATCHDOG_SECS:-300}); do kill -0 $PID 2>/dev/null || break; sleep 1; done
if kill -0 $PID 2>/dev/null; then
  powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'HarnessCli.Run' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" >/dev/null 2>&1; sleep 3
  [ -f "$O" ] || echo '{"fatal":"watchdog: editor hung and was killed","log":[],"errors":[]}' > "$O"
fi
wait $PID 2>/dev/null
echo done; head -c ${HEAD_BYTES:-3000} "$O" 2>/dev/null
