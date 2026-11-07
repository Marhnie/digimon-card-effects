#!/bin/bash
D=C:/Users/Daewonmedia/ourai_data
BAN="BT24-034;BT25-033;BT25-025;P-213;BT26-029;BT26-033;BT24-041;BT26-081"
SD="$D/climbed_scratch_climb_2b.json;$D/climbed_gen_climb_2.json;$D/gen_top_1.json;$D/gen_top_3.json;$D/scratch_final_1.json"
PEERS="$D/evob_1.jsonl;$D/evob_2.jsonl;$D/evob_3.jsonl;$D/evob_4.jsonl;$D/evob_5.jsonl"
until grep -q "CHECKPOINT 5 DONE" $D/evo_checkpoint.done 2>/dev/null; do sleep 300; done
DL=$(( ($(date +%s) + 24*3600) * 1000 )); echo $DL > $D/evob_deadline_ms
echo "BAN START $(date)" >> $D/evob.status
run_island() {
  i=$1; cd /c/Users/Daewonmedia/aegis_engine/apps/api
  while [ $(( $(date +%s) * 1000 )) -lt $DL ]; do
    AEGIS_CARDS_BUNDLE=0 OURAI_BAN="$BAN" OURAI_GENS=100000 OURAI_SEED=$((100+i)) OURAI_SEED_DECKS="$SD" OURAI_PEERS="$PEERS" OURAI_DEADLINE_MS=$DL OURAI_OUT=$D/evob_$i.jsonl npx vitest run src/ourai/evo.test.ts >> $D/evob_$i.log 2>&1
    echo "restart $(date +%T)" >> $D/evob_$i.log; sleep 5
  done
  echo "ISLAND DONE $(date +%T)" >> $D/evob_$i.log
}
for i in 1 2 3 4 5; do run_island $i & done
wait
decks=""
for i in 1 2 3 4 5; do
  python -c "import json;l=open('$D/evob_$i.jsonl').read().strip().split('\n')[-1];json.dump(json.loads(l)['best'],open('$D/evob_final_$i.json','w'))" && decks="$decks$D/evob_final_$i.json;"
done
CH=$(ls $D/evo_cp5_*.json | head -1)
python - <<PY
import json
rows=[json.loads(l) for l in open('$D/evo_checkpoint.jsonl') if l.strip()]
c=[r for r in rows if r['seed']==290000000 and 'evo_cp5' in r['deck']]
best=max(c,key=lambda r:r['score'])['deck'] if c else '$CH'
open('$D/evob_champ_path','w').write(best)
PY
cd /c/Users/Daewonmedia/aegis_engine/apps/api
AEGIS_CARDS_BUNDLE=0 OURAI_DECKS="${decks}$(cat $D/evob_champ_path);meta:Jupitermon" OURAI_GAMES=64 OURAI_EVAL_SEED=600000000 OURAI_OUT=$D/evob_checkpoint.jsonl npx vitest run src/ourai/vdeck.test.ts > $D/evob_cp.log 2>&1
echo "BAN DONE $(date)" >> $D/evob.status
