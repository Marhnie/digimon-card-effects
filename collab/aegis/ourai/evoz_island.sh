#!/bin/bash
i=$1; D=C:/Users/Daewonmedia/ourai_data; G=100
PEERS="$D/evoz_1.jsonl;$D/evoz_2.jsonl;$D/evoz_3.jsonl;$D/evoz_4.jsonl;$D/evoz_5.jsonl"
lastgen() { [ -f $D/evoz_$i.jsonl ] && tail -1 $D/evoz_$i.jsonl | python -c "import json,sys;print(json.loads(sys.stdin.read())['gen'])" || echo 0; }
cd /c/Users/Daewonmedia/aegis_engine/apps/api
while [ $(lastgen) -lt $G ]; do
  AEGIS_CARDS_BUNDLE=0 OURAI_GENS=$G OURAI_SEED=$((200+i)) OURAI_RANDOM_START=24 OURAI_PEERS="$PEERS" OURAI_OUT=$D/evoz_$i.jsonl npx vitest run src/ourai/evo.test.ts >> $D/evoz_$i.log 2>&1
  echo "restart $(date +%T)" >> $D/evoz_$i.log; sleep 5
done
echo "ISLAND DONE $(date +%T)" >> $D/evoz_$i.log
