#!/bin/bash
D=C:/Users/Daewonmedia/ourai_data; A=$D/allround
EXTRA="$D/evom_1.jsonl;$D/evom_2.jsonl;$D/evom_3.jsonl;$D/evom_4.jsonl;$D/evom_5.jsonl"
cd /c/Users/Daewonmedia/aegis_engine/apps/api
c=$(cat $A/cycle 2>/dev/null || echo 0)
while true; do
  c=$((c+1)); echo $c > $A/cycle
  DL=$(( $(date +%s) * 1000 + 12*3600*1000 ))
  AEGIS_CARDS_BUNDLE=0 OURAI_EXTRA="$EXTRA" OURAI_DEADLINE_MS=$DL OURAI_OUT=$A/tune.jsonl OURAI_CHAMP_OUT=$A/champ.json npx vitest run src/ourai/allround.test.ts >> $A/tune.log 2>&1
  if [ -f $A/champ.json ] && ! cmp -s $A/champ.json $D/pilots_use/self.json; then
    BASE=""; [ -f $D/pilots_use/self.json ] && BASE=$D/pilots_use/self.json
    AEGIS_CARDS_BUNDLE=0 OURAI_CHECK=1 OURAI_EXTRA="$EXTRA" OURAI_CAND=$A/champ.json OURAI_BASE="$BASE" OURAI_GAMES=4 OURAI_EVAL_SEED=$((2000000000 + c*1000000)) OURAI_OUT=$A/check.jsonl npx vitest run src/ourai/allround.test.ts >> $A/check.log 2>&1
    R=$(tail -1 $A/check.jsonl | python -c "import json,sys;r=json.loads(sys.stdin.read());print('PASS' if r['cand']>=r['base']+0.02 else 'FAIL', round(r['cand'],4), round(r['base'],4), r['games'])")
    echo "CYCLE $c CHECK $R $(date)" >> $A/status
    case "$R" in PASS*) cp $A/champ.json $A/deployed_c$c.json; cp $A/champ.json $D/pilots_use/self.json; echo "CYCLE $c DEPLOY $(date)" >> $A/status;; esac
  else
    echo "CYCLE $c NO NEW CHAMP $(date)" >> $A/status
  fi
done
