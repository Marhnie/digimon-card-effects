#!/bin/bash
D=C:/Users/Daewonmedia/ourai_data; cd $D
until grep -q "GEN 75 CHECK DONE" evom_checkpoint.done 2>/dev/null; do sleep 300; done
R=$(python - <<'PY'
import json
rows=[json.loads(l) for l in open('C:/Users/Daewonmedia/ourai_data/evom_checkpoint.jsonl') if 'evom_g75_' in l]
b=max(rows,key=lambda r:r['score'])
d=json.load(open(b['deck']))
n=len(set(d['mainDeck']))
print(f"{'EXTEND' if n<=25 else 'SWITCH'} best={b['deck'].split('/')[-1]} score={b['score']:.3f} distinct={n}")
PY
)
echo "DECISION $R $(date)" >> evom_checkpoint.done
case "$R" in EXTEND*) ;; *) exit 0;; esac
for i in 1 2 3 4 5; do (until grep -q "ISLAND DONE" evom_$i.log; do sleep 120; done; EVOM_G=200 bash evom_island.sh $i) & done
EVOM_CHECKS="125 150 175 200" bash evom_checkpoint.sh
wait
