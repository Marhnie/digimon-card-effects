"""⑤ 처리 단계 채점 (E30).
기준: paper/results/gold_proc_rejudge.json — 검수 정답셋 300문항 중 처리 단계가 있는 248문항을 엄격 기준으로 다시 판정한 O/X.
  판정 기준: (1) 단계 분할(처리 단위·조건 문구가 섞이지 않음) (2) 행동 (3) 강제/임의 (4) 대상 종류·편(대명사는 앞 단계를 이어받음)
            (5) 필터는 대상을 좁히는 조건만(세는 기준·비교 기준 제외) (6) 수량·기간.
각 문항에는 판정 당시 출력의 서명(sig)이 있다. 현재 출력의 서명이 같으면 그 판정을 그대로 쓰고, 다르면 '재판정 필요'로 따로 낸다.
(옛 v4.0 다수결 .838은 paper/results/gold_eval3.json 참고.)
사용: python gold_eval_proc.py [struct.json]"""
import json, sys
S = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'struct.json', encoding='utf8'))
def sig_new(st): return json.dumps([(tuple(s['acts']), s['임의'], s['scope'], s['dur'], s['target'], s['side'], tuple(s['filters']), s['text']) + ((s['선택지'],) if '선택지' in s else ()) for s in st], ensure_ascii=False)
for name, f in [('검수 정답셋 300문항(처리 단계 있는 248)', 'paper/results/gold_proc_rejudge.json'), ('표본 90문항 (1차: 수정 도중 오류 확인에 사용)', 'paper/results/gold_proc_heldout.json'), ('표본 100문항 (2차: 1차 수정 뒤 처음 보고 수정에 사용)', 'paper/results/gold_proc_dev2.json'), ('표본 100문항 (3차: 수정에 쓰기 전 한 번만 판정, 눈가림)', 'paper/results/gold_proc_blind.json')]:
    RJ = json.load(open(f, encoding='utf8'))
    o = x = 0; need = []; bo = bx = 0
    for k, r in RJ.items():
        if sig_new(S[int(k)]['처리']) == r['sig']:
            if r['v'] == 'O': o += 1
            else: x += 1
        else: need.append(int(k))
        if r.get('base', r['v']) == 'O': bo += 1
        else: bx += 1
    print('%s: 기준선(E30 전) %d/%d = %.3f' % (name, bo, bo + bx, bo / (bo + bx)))
    if any('v_at_test' in r for r in RJ.values()): vo = sum(1 for r in RJ.values() if r['v_at_test'] == 'O'); print('   판정 당시(수정 전 마지막 버전) %d/%d = %.3f' % (vo, len(RJ), vo / len(RJ)))
    print('   현재: 판정 유지 %d (맞음 %d 틀림 %d), 재판정 필요 %d, 정확도 %.3f' % (o + x, o, x, len(need), o / max(1, o + x)))
    json.dump(need, open('need_%s.tmp.json' % ('gold' if 'rejudge' in f else ('held' if 'heldout' in f else ('dev2' if 'dev2' in f else 'blind'))), 'w'))
