#!/bin/bash
D=C:/Users/Daewonmedia/ourai_data
for G in 25 50 75 100; do
  until python - $G <<'PY'
import json,sys,os
G=int(sys.argv[1]);D='C:/Users/Daewonmedia/ourai_data'
for i in range(1,6):
  f=f'{D}/evom_{i}.jsonl'
  if not os.path.exists(f): sys.exit(1)
  rows=[json.loads(l) for l in open(f) if l.strip()]
  r=[x for x in rows if x['gen']==G]
  if not r: sys.exit(1)
  json.dump(r[-1]['best'],open(f'{D}/evom_g{G}_{i}.json','w'))
PY
  do sleep 300; done
  decks=""; for i in 1 2 3 4 5; do decks="$decks$D/evom_g${G}_$i.json;"; done
  cd /c/Users/Daewonmedia/aegis_engine/apps/api
  AEGIS_CARDS_BUNDLE=0 OURAI_GAUNTLET=current OURAI_PILOT_DIR=$D/pilots_use OURAI_DECKS="${decks}meta:Jupitermon" OURAI_GAMES=64 OURAI_EVAL_SEED=$((1600000000 + G*1000000)) OURAI_OUT=$D/evom_checkpoint.jsonl npx vitest run src/ourai/vdeck.test.ts > $D/evom_g$G.log 2>&1
  echo "GEN $G CHECK DONE $(date +%T)" >> $D/evom_checkpoint.done
done
