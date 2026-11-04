#!/bin/bash
# usage: run_seq_screen.sh SEEDBASE "TAG:ENV=V,ENV=V" ...   runs each config with 5 workers x 20 games, one config at a time
SB=$1; shift
D=/c/Users/Daewonmedia/ourai_data
for spec in "$@"; do
  tag=${spec%%:*}; envs=${spec#*:}
  (
    IFS=',' read -ra kv <<< "$envs"; for e in "${kv[@]}"; do [ -n "$e" ] && export "$e"; done
    export OURAI_HALF=1 SEEDBASE=$SB
    bash /c/Users/Daewonmedia/card_effects/collab/aegis/ourai/run_duel.sh C:/Users/Daewonmedia/ourai_data/value_v2_mix.json $tag 5 20
  )
  sleep 20
  until [ $(grep -l "Tests" $D/duel_${tag}_*.log 2>/dev/null | wc -l) -ge 5 ]; do sleep 30; done
  echo "== $tag ($envs)"; python -X utf8 /c/Users/Daewonmedia/card_effects/collab/aegis/ourai/score_duel.py "C:/Users/Daewonmedia/ourai_data/duel_${tag}_*.jsonl" 2>&1 | head -5
done
