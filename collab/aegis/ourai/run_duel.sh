#!/bin/bash
# usage: run_duel.sh VALUE_JSON TAG WORKERS GAMES_PER_WORKER [LEVEL]
cd /c/Users/Daewonmedia/aegis_engine/apps/api
for w in $(seq 0 $(($3-1))); do
  (OURAI_VALUE=$1 OURAI_LEVEL=${5:-master} OURAI_GAMES=$4 OURAI_SEED=$((700000+w*1000)) OURAI_OUT=C:/Users/Daewonmedia/ourai_data/duel_$2_$w.jsonl AEGIS_CARDS_BUNDLE=0 \
    npx vitest run src/ourai/duel.test.ts --silent=false --reporter=verbose > /c/Users/Daewonmedia/ourai_data/duel_$2_$w.log 2>&1 &)
done
