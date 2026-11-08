#!/bin/bash
D=C:/Users/Daewonmedia/ourai_data
until grep -q "GEN 100 CHECK DONE" $D/evom_checkpoint.done 2>/dev/null; do sleep 300; done
G=100
while [ ! -f $D/evom_STOP ]; do
  G=$((G+25))
  until python - $G <<'PY'
import json,sys,os
G=int(sys.argv[1]);D='C:/Users/Daewonmedia/ourai_data'
for i in range(1,6):
  rows=[json.loads(l) for l in open(f'{D}/evom_{i}.jsonl') if l.strip()]
  r=[x for x in rows if x['gen']==G]
  if not r: sys.exit(1)
  json.dump(r[-1]['best'],open(f'{D}/evom_g{G}_{i}.json','w'))
PY
  do sleep 300; done
  decks=""; for i in 1 2 3 4 5; do decks="$decks$D/evom_g${G}_$i.json;"; done
  [ $G -eq 125 ] && decks="$decks$D/evo_cp2_1.json;"
  cd /c/Users/Daewonmedia/aegis_engine/apps/api
  AEGIS_CARDS_BUNDLE=0 OURAI_GAUNTLET=current OURAI_PILOT_DIR=$D/pilots_use OURAI_DECKS="${decks}meta:Jupitermon" OURAI_GAMES=64 OURAI_EVAL_SEED=$((1600000000 + G*1000000)) OURAI_OUT=$D/evom_checkpoint.jsonl npx vitest run src/ourai/vdeck.test.ts > $D/evom_g$G.log 2>&1
  echo "GEN $G CHECK DONE $(date +%T)" >> $D/evom_checkpoint.done
  BEST=$(python - $G <<'PY'
import json,sys
G=int(sys.argv[1])
rows=[json.loads(l) for l in open('C:/Users/Daewonmedia/ourai_data/evom_checkpoint.jsonl') if f'evom_g{G}_' in l]
b=max(rows,key=lambda r:r['score'])
print(b['deck'] if b['score']>=0.90 else '')
PY
)
  if [ -n "$BEST" ]; then
    AEGIS_CARDS_BUNDLE=0 OURAI_GAUNTLET=current OURAI_PILOT_DIR=$D/pilots_use OURAI_DECKS="$BEST" OURAI_GAMES=128 OURAI_EVAL_SEED=$((1900000000 + G*1000000)) OURAI_OUT=$D/evom_confirm.jsonl npx vitest run src/ourai/vdeck.test.ts > $D/evom_confirm_g$G.log 2>&1
    S=$(tail -1 $D/evom_confirm.jsonl | python -c "import json,sys;print(json.loads(sys.stdin.read())['score'])")
    echo "CONFIRM G$G $BEST $S $(date +%T)" >> $D/evom_checkpoint.done
    python -c "import sys;sys.exit(0 if float('$S')>=0.90 else 1)" && { echo "TARGET REACHED G$G $(date)" >> $D/evom_checkpoint.done; touch $D/evom_STOP; }
  fi
done
