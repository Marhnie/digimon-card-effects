#!/bin/bash
export PYTHONIOENCODING=utf-8
set -e
for s in parse_fx cluster_fx link_fx build_test build_test2 build_test3 qa_group build_test3 rule_struct struct_groups reason_groups build_v4data; do
  echo "== $s $(date +%H:%M:%S)"; python $s.py | tail -3 | cut -c1-200
done
echo "== build_v3"; python build_v3.py --dist | tail -2 | cut -c1-200
export TDEC_NEW=BT26,EX11,EX12,EX13,AD1,ST23,ST24,LM
echo "== tdec"; TDEC_FULL=1 TDEC_DUMP=net/tdec_next.json node tests/tdec.js | tail -5 | cut -c1-300
echo "== export"; EXPORT_NEW=$TDEC_NEW EXPORT_OUT=train/data_next python train/export_dataset.py | tail -3 | cut -c1-200
echo "== r1"; python jpnext/r1_score.py net/tdec_next.json jpnext/r1_official.json | cut -c1-300
echo BUILD_DONE
