#!/bin/bash
# 정체 3회 후 수단 (2026-11-10 사전 등록): 평가 판수 상대당 4→8 (개체당 32→64판). 나머지 동일.
i=$1; D=C:/Users/Daewonmedia/ourai_data
PEERS="$D/evom_1.jsonl;$D/evom_2.jsonl;$D/evom_3.jsonl;$D/evom_4.jsonl;$D/evom_5.jsonl"
lastgen() { tail -1 $D/evom_$i.jsonl | python -c "import json,sys;print(json.loads(sys.stdin.read())['gen'])"; }
runs() { grep -c 'Test Files' $D/evom_$i.log; }
until [ $(runs) -gt $R0 ]; do sleep 30; done   # 진행 중이던 250세대 묶음 종료 대기
cd /c/Users/Daewonmedia/aegis_engine/apps/api
while [ ! -f $D/evom_STOP ]; do
  G=$(( $(lastgen) / 25 * 25 + 25 ))
  AEGIS_CARDS_BUNDLE=0 OURAI_GENS=$G OURAI_SEED=$((250+i)) OURAI_GAMES=8 OURAI_GAUNTLET=current OURAI_PILOT_DIR=$D/pilots_use OURAI_BLOCK=0.5 OURAI_PEERS="$PEERS" OURAI_OUT=$D/evom_$i.jsonl npx vitest run src/ourai/evo.test.ts >> $D/evom_$i.log 2>&1
  sleep 5
done
echo "GOAL ISLAND STOP $(date +%T)" >> $D/evom_$i.log
