#!/bin/bash
cd "$(dirname "$0")"
for k in "$@"; do ./run_job.sh jobs/$k.json >/dev/null 2>&1; echo "finished $k"; done; echo ALLDONE2
