#!/bin/bash
i=$1; D=C:/Users/Daewonmedia/ourai_data; G=100
PEERS="$D/evom_1.jsonl;$D/evom_2.jsonl;$D/evom_3.jsonl;$D/evom_4.jsonl;$D/evom_5.jsonl"
lastgen() { [ -f $D/evom_$i.jsonl ] && tail -1 $D/evom_$i.jsonl | python -c "import json,sys;print(json.loads(sys.stdin.read())['gen'])" || echo 0; }
cd /c/Users/Daewonmedia/aegis_engine/apps/api
while [ $(lastgen) -lt $G ]; do
  AEGIS_CARDS_BUNDLE=0 OURAI_GENS=$G OURAI_SEED=$((250+i)) OURAI_GAUNTLET=current OURAI_PILOT_DIR=$D/pilots_use OURAI_RANDOM_START=24 OURAI_PEERS="$PEERS" OURAI_OUT=$D/evom_$i.jsonl npx vitest run src/ourai/evo.test.ts >> $D/evom_$i.log 2>&1
  echo "restart $(date +%T)" >> $D/evom_$i.log; sleep 5
done
echo "ISLAND DONE $(date +%T)" >> $D/evom_$i.log
