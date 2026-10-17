"""E18 scoring: accuracy with Wilson 95% CI, exact McNemar between methods, confidence calibration; pooled with E3 where the method exists in both."""
import json, glob, math, os
from scipy.stats import binomtest

def load(d, s):
    P, C = {}, {}
    for f in sorted(glob.glob(f'{d}/{s}_b*_out.json')):
        for k, v in json.load(open(f, encoding='utf-8')).items():
            a = str(v.get('answer', '')).strip()
            P[k] = '네' if a.startswith('네') else ('아니요' if a.startswith('아니') else a); C[k] = v.get('conf')
    return P, C

def wilson(k, n, z=1.96):
    if not n: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - h) / d, 3), round((c + h) / d, 3))

def mcnemar(P, a, b, gold):
    ks = [k for k in gold if k in P[a] and k in P[b]]
    oa = sum(1 for k in ks if P[a][k] == gold[k] and P[b][k] != gold[k]); ob = sum(1 for k in ks if P[b][k] == gold[k] and P[a][k] != gold[k])
    p = binomtest(oa, oa + ob, 0.5).pvalue if oa + ob else 1.0
    return {'only_' + a: oa, 'only_' + b: ob, 'p_exact': round(p, 4)}

out = {}
for d, methods in (('eval2', ['S2', 'S3', 'S5']), ('eval', ['S2', 'S3', 'S4'])):
    g = json.load(open(f'{d}/gold.json', encoding='utf-8'))
    gold = {k: ('네' if v['lab'] == 'Y' else '아니요') for k, v in g.items()}
    s1 = json.load(open(f'{d}/S1_pred.json', encoding='utf-8'))
    P = {'S1': {k: ('네' if v['pred'] == 'Y' else '아니요') for k, v in s1.items()}}; C = {}
    for s in methods: P[s], C[s] = load(d, s)
    res = {'n': len(gold), 'methods': {}, 'pairs': {}}
    for s in P:
        ks = [k for k in gold if k in P[s]]; ok = sum(P[s][k] == gold[k] for k in ks)
        r = {'answered': len(ks), 'correct': ok, 'acc': round(ok / max(1, len(ks)), 4), 'ci95': wilson(ok, len(ks)),
             'yes_acc': round(sum(P[s][k] == gold[k] for k in ks if gold[k] == '네') / max(1, sum(1 for k in ks if gold[k] == '네')), 3),
             'no_acc': round(sum(P[s][k] == gold[k] for k in ks if gold[k] == '아니요') / max(1, sum(1 for k in ks if gold[k] == '아니요')), 3)}
        if s in C:
            hi = [k for k in ks if (C[s].get(k) or 0) >= 0.8]; lo = [k for k in ks if (C[s].get(k) or 0) < 0.8]
            r['conf_hi'] = [sum(P[s][k] == gold[k] for k in hi), len(hi)]; r['conf_lo'] = [sum(P[s][k] == gold[k] for k in lo), len(lo)]
        res['methods'][s] = r
    ms = list(P)
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)): res['pairs'][f'{ms[i]} vs {ms[j]}'] = mcnemar(P, ms[i], ms[j], gold)
    res['wrong'] = {s: [k for k in gold if k in P[s] and P[s][k] != gold[k]] for s in P}
    out[d] = res
# pooled 300 for the methods run in both tests (S2 Claude alone, S3 Claude + 2-gram retrieval)
pool = {}
for s in ('S1', 'S2', 'S3'):
    c = sum(out[d]['methods'][s]['correct'] for d in out); n = sum(out[d]['methods'][s]['answered'] for d in out)
    pool[s] = {'correct': c, 'n': n, 'acc': round(c / n, 4), 'ci95': wilson(c, n)}
out['pooled_E3_E18'] = pool
os.makedirs('paper/results', exist_ok=True)
json.dump(out, open('paper/results/llm_eval2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
names = {'S1': '분류 엔진 단독(LLM 없음)', 'S2': 'Claude 단독', 'S3': 'Claude + 문구 검색 근거', 'S4': 'Claude + 분류 엔진 근거(v3)', 'S5': 'Claude + 판정 도우미 근거(v4 구조·무리)'}
for d in ('eval2', 'eval'):
    print(f"== {d} (n={out[d]['n']})")
    for s, r in out[d]['methods'].items():
        print(f"  {s} {names[s]:26} {r['correct']}/{r['answered']} = {r['acc']:.1%}  95%CI {r['ci95']}  네 {r['yes_acc']} 아니요 {r['no_acc']}" + (f"  확신≥0.8 {r['conf_hi']} <0.8 {r['conf_lo']}" if 'conf_hi' in r else ''))
    for k, v in out[d]['pairs'].items(): print('   ', k, v)
print('== 합산 300', pool)
