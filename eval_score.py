import json, glob, collections, os
gold = json.load(open('eval/gold.json', encoding='utf-8'))
s1 = json.load(open('eval/S1_pred.json', encoding='utf-8'))
P = {'S1': {k: ('네' if v['pred'] == 'Y' else '아니요') for k, v in s1.items()}}
C = {}
for s in ('S2', 'S3', 'S4'):
    P[s], C[s] = {}, {}
    for f in sorted(glob.glob(f'eval/{s}_b*_out.json')):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception as e:
            print('bad file', f, e); continue
        for k, v in d.items():
            P[s][k] = v.get('answer'); C[s][k] = v.get('conf')
ans = {k: ('네' if g['lab'] == 'Y' else '아니요') for k, g in gold.items()}
names = {'S1': '분류 엔진 단독(Claude 없음)', 'S2': 'Claude 단독', 'S3': 'Claude + 기존 검색', 'S4': 'Claude + 분류 엔진 근거'}
print('answered:', {s: len(P[s]) for s in P})
for s in P:
    ks = [k for k in gold if k in P[s]]
    ok = sum(P[s][k] == ans[k] for k in ks)
    yes_ok = sum(P[s][k] == ans[k] for k in ks if ans[k] == '네'); no_ok = sum(P[s][k] == ans[k] for k in ks if ans[k] == '아니요')
    print(f'{s} {names[s]:22} 정답 {ok}/{len(ks)}  오답률 {100 - 100 * ok / max(1, len(ks)):.0f}%  (네 {yes_ok}/50, 아니요 {no_ok}/50)')
for a, b in (('S3', 'S4'), ('S2', 'S4'), ('S2', 'S3'), ('S1', 'S4')):
    ks = [k for k in gold if k in P[a] and k in P[b]]
    only_a = sum(1 for k in ks if P[a][k] == ans[k] and P[b][k] != ans[k]); only_b = sum(1 for k in ks if P[b][k] == ans[k] and P[a][k] != ans[k])
    print(f'{a} vs {b}: {a}만 맞힘 {only_a}, {b}만 맞힘 {only_b}')
# confidence calibration for S4
for s in ('S2', 'S3', 'S4'):
    hi = [k for k in P[s] if (C[s].get(k) or 0) >= 0.8]; lo = [k for k in P[s] if (C[s].get(k) or 0) < 0.8]
    f = lambda ks: f'{sum(P[s][k] == ans[k] for k in ks)}/{len(ks)}'
    print(f'{s} 확신≥0.8: {f(hi)}  확신<0.8: {f(lo)}')
rows = []
for k, g in gold.items():
    rows.append({'id': k, 'card': g['card'], 'q': g['q'], 'gold': ans[k], **{s: P[s].get(k) for s in P}})
json.dump(rows, open('eval/results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
