#!/bin/bash
D=C:/Users/Daewonmedia/ourai_data; DL=$(cat $D/evoz_deadline_ms)
for k in 1 2 3 4 5; do
  target=$(( DL/1000 - (5-k)*12*3600 ))
  while [ $(date +%s) -lt $target ]; do sleep 300; done
  [ $k -eq 5 ] && while [ $(grep -l "ISLAND DONE" $D/evoz_{1..5}.log 2>/dev/null | wc -l) -lt 5 ]; do sleep 300; done
  decks=""
  for i in 1 2 3 4 5; do
    python -c "import json;l=open('$D/evoz_$i.jsonl').read().strip().split('\n')[-1];json.dump(json.loads(l)['best'],open('$D/evoz_cp${k}_$i.json','w'))" && decks="$decks$D/evoz_cp${k}_$i.json;"
  done
  cd /c/Users/Daewonmedia/aegis_engine/apps/api
  AEGIS_CARDS_BUNDLE=0 OURAI_DECKS="${decks}meta:Jupitermon" OURAI_GAMES=64 OURAI_EVAL_SEED=$((700000000 + k*10000000)) OURAI_OUT=$D/evoz_checkpoint.jsonl npx vitest run src/ourai/vdeck.test.ts > $D/evoz_cp$k.log 2>&1
  echo "CHECKPOINT $k DONE $(date +%T)" >> $D/evoz_checkpoint.done
done
