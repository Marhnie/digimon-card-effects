#!/bin/bash
# usage: run_job.sh jobs/x.json  -> jobs/x.out.json (log: jobs/x.log)
J=$(cygpath -w "$(realpath "$1")"); O="${J%.json}.out.json"; rm -f "$O"
export DCGO_JOB="$J" DCGO_OUT="$O"
"C:/Users/Daewonmedia/Unity/2021.3.45f2/Editor/Unity.exe" -batchmode -projectPath "C:\Users\Daewonmedia\ext\DCGO" -executeMethod HarnessCli.Run -logFile "${J%.json}.log"
echo done exit=$?; cat "$O" 2>/dev/null | head -c 3000
