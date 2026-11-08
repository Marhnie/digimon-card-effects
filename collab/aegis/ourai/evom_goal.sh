#!/bin/bash
i=$1; D=C:/Users/Daewonmedia/ourai_data
PEERS="$D/evom_1.jsonl;$D/evom_2.jsonl;$D/evom_3.jsonl;$D/evom_4.jsonl;$D/evom_5.jsonl"
lastgen() { tail -1 $D/evom_$i.jsonl | python -c "import json,sys;print(json.loads(sys.stdin.read())['gen'])"; }
until grep -q "ISLAND DONE" $D/evom_$i.log; do sleep 120; done
cd /c/Users/Daewonmedia/aegis_engine/apps/api
while [ ! -f $D/evom_STOP ]; do
  G=$(( $(lastgen) / 25 * 25 + 25 ))
  AEGIS_CARDS_BUNDLE=0 OURAI_GENS=$G OURAI_SEED=$((250+i)) OURAI_GAUNTLET=current OURAI_PILOT_DIR=$D/pilots_use OURAI_BLOCK=0.5 OURAI_PEERS="$PEERS" OURAI_OUT=$D/evom_$i.jsonl npx vitest run src/ourai/evo.test.ts >> $D/evom_$i.log 2>&1
  sleep 5
done
echo "GOAL ISLAND STOP $(date +%T)" >> $D/evom_$i.log
