#!/bin/bash
i=$1; D=C:/Users/Daewonmedia/ourai_data; DL=$(cat $D/evoz_deadline_ms)
PEERS="$D/evoz_1.jsonl;$D/evoz_2.jsonl;$D/evoz_3.jsonl;$D/evoz_4.jsonl;$D/evoz_5.jsonl"
cd /c/Users/Daewonmedia/aegis_engine/apps/api
while [ $(( $(date +%s) * 1000 )) -lt $DL ]; do
  AEGIS_CARDS_BUNDLE=0 OURAI_GENS=100000 OURAI_SEED=$((200+i)) OURAI_RANDOM_START=24 OURAI_PEERS="$PEERS" OURAI_DEADLINE_MS=$DL OURAI_OUT=$D/evoz_$i.jsonl npx vitest run src/ourai/evo.test.ts >> $D/evoz_$i.log 2>&1
  echo "restart $(date +%T)" >> $D/evoz_$i.log; sleep 5
done
echo "ISLAND DONE $(date +%T)" >> $D/evoz_$i.log
