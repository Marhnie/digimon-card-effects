#!/bin/bash
# 유저 레시피 기반 50루트 (사전 등록 2026-11-10). 워커 w(1..5)는 r%5==w%5 루트를 차례로 20세대씩.
w=$1; D=C:/Users/Daewonmedia/ourai_data; R=$D/routes
lastgen() { [ -f $R/r$1.jsonl ] && tail -1 $R/r$1.jsonl | python -c "import json,sys;print(json.loads(sys.stdin.read())['gen'])" || echo 0; }
cd /c/Users/Daewonmedia/aegis_engine/apps/api
for r in $(seq 1 50); do
  [ $(( r % 5 )) -ne $(( w % 5 )) ] && continue
  SEEDS=$(ls $R/r$r/u*.json | tr '\n' ';')
  n=0
  while [ $(lastgen $r) -lt 20 ] && [ $n -lt 5 ] && [ ! -f $D/routes_STOP ]; do
    AEGIS_CARDS_BUNDLE=0 OURAI_GENS=20 OURAI_SEED=$((500+r)) OURAI_GAMES=4 OURAI_NO_META_SEED=1 OURAI_SEED_DECKS="$SEEDS" OURAI_GAUNTLET=current OURAI_PILOT_DIR=$D/pilots_use OURAI_BLOCK=0.5 OURAI_OUT=$R/r$r.jsonl npx vitest run src/ourai/evo.test.ts >> $R/r$r.log 2>&1
    n=$((n+1)); sleep 5
  done
  echo "ROUTE $r DONE gen $(lastgen $r) $(date +%T)" >> $R/done.txt
done
echo "WORKER $w FINISHED $(date)" >> $R/done.txt
