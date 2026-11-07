#!/bin/bash
D=C:/Users/Daewonmedia/ourai_data
until grep -q "CHECK DONE" $D/pilots/status 2>/dev/null; do sleep 300; done
mkdir -p $D/pilots_use
python - <<'PY'
import json,shutil,re
D='C:/Users/Daewonmedia/ourai_data'
for l in open(f'{D}/pilots/pilotcheck.jsonl'):
    r=json.loads(l)
    if r.get('tuned') is False: continue
    slug=re.sub(r'[^A-Za-z0-9]+','_',r['deck'])
    use = r['tuned'] >= r['generic'] + 0.02
    print(r['deck'], r['tuned'], r['generic'], 'USE' if use else 'generic')
    if use: shutil.copy(f'{D}/pilots/pilot_{slug}.json', f'{D}/pilots_use/pilot_{slug}.json')
PY
echo "EVOM START $(date)" >> $D/pilots/status
for i in 1 2 3 4 5; do $D/evom_island.sh $i & done
$D/evom_checkpoint.sh &
wait
