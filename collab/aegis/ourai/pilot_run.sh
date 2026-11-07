#!/bin/bash
D=C:/Users/Daewonmedia/ourai_data; P=$D/pilots
DECKS=("Examon" "Jupitermon" "UlforceVeedramon" "Glowing Dawn" "TS Mervamon" "Toho Braves" "Chronomon")
DL=$(( ($(date +%s) + 10*3600) * 1000 )); echo $DL > $P/deadline_ms
run() {
  k=$1; name="${DECKS[$k]}"; slug=$(echo "$name" | sed 's/[^A-Za-z0-9]\+/_/g')
  cd /c/Users/Daewonmedia/aegis_engine/apps/api
  while [ $(( $(date +%s) * 1000 )) -lt $DL ]; do
    AEGIS_CARDS_BUNDLE=0 OURAI_DECK="$name" OURAI_SEED=$((k+1)) OURAI_DEADLINE_MS=$DL OURAI_OUT=$P/tune_$slug.jsonl OURAI_CHAMP_OUT=$P/pilot_$slug.json npx vitest run src/ourai/pilot.test.ts >> $P/tune_$slug.log 2>&1
    echo "restart $(date +%T)" >> $P/tune_$slug.log; sleep 5
  done
}
for k in 0 1 2 3 4 5 6; do run $k & done
wait
echo "TUNE DONE $(date)" >> $P/status
cd /c/Users/Daewonmedia/aegis_engine/apps/api
AEGIS_CARDS_BUNDLE=0 OURAI_PILOT_DIR=$P OURAI_DECKS="Examon;Jupitermon;UlforceVeedramon;Glowing Dawn" OURAI_GAMES=32 OURAI_EVAL_SEED=1500000000 OURAI_OUT=$P/pilotcheck.jsonl npx vitest run src/ourai/pilotcheck.test.ts > $P/check_a.log 2>&1 &
AEGIS_CARDS_BUNDLE=0 OURAI_PILOT_DIR=$P OURAI_DECKS="TS Mervamon;Toho Braves;Chronomon" OURAI_GAMES=32 OURAI_EVAL_SEED=1500000000 OURAI_OUT=$P/pilotcheck.jsonl npx vitest run src/ourai/pilotcheck.test.ts > $P/check_b.log 2>&1 &
wait
echo "CHECK DONE $(date)" >> $P/status
