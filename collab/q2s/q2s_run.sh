#!/bin/bash
# usage: q2s_run.sh listfile  -> runs jobs/q2s/<name>.json sequentially (skips ones that already have .out.json)
cd "$(dirname "$0")/.."
while read k; do
  k=${k%$''}; [ -z "$k" ] && continue
  [ -f jobs/q2s/$k.out.json ] && continue
  ./run_job.sh jobs/q2s/$k.json > /dev/null 2>&1
  rm -f jobs/q2s/$k.log
  echo "finished $k"
done < "$1"
echo ALLDONE
