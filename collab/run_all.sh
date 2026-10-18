#!/bin/bash
cd "$(dirname "$0")"
for f in jobs/q*.json; do case $f in *.out.json) continue;; esac; ./run_job.sh $f > /dev/null 2>&1; echo "finished $f"; done
echo ALLDONE
