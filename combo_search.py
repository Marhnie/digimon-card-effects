"""E46: brute-force search over combinations of the signals the page already computes (tests/tdec.js TDEC_FULL dump),
for questions the page leaves undecided. A rule = a conjunction of signal conditions that all point to the same answer.
Honest: rules are chosen on one half of the newest products (acc >= TARGET, n >= MINN) and measured on the other half.
  python combo_search.py  -> paper/results/combo_search.json"""
import json, itertools, os, re
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
HALF0 = {'BT22', 'EX9', 'ST21'}; prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
D = json.load(open('net/tdec_full.json')); TARGET = float(os.environ.get('TARGET', '0.97')); MINN = int(os.environ.get('MINN', '5'))
SEM = {r['i']: r for r in json.load(open('net/sem_decide_rows.json'))} if os.path.exists('net/sem_decide_rows.json') else {}
und = [d for d in D if not d['by']]
print('undecided', len(und), 'of', len(D))
# each signal: (name, function(d) -> answer or None when the condition does not hold)
def S(name, f): return (name, f)
sig = []
for t in (0.6, 0.7, 0.8, 0.9):
    sig.append(S(f'eng p>={t}', lambda d, t=t: (d['eng']['ans'] if d.get('eng') and max(d['eng']['p'], 1 - d['eng']['p']) >= t else None)))
for t in (0.5, 0.6, 0.7):
    sig.append(S(f'eng conf>={t}', lambda d, t=t: (d['eng']['ans'] if d.get('eng') and d['eng']['conf'] >= t else None)))
for t in (0.3, 0.45, 0.6):
    sig.append(S(f'est top>={t} agree>=4', lambda d, t=t: (d['est']['ans'] if d.get('est') and d['est']['top'] >= t and d['est']['agree'] >= 4 else None)))
sig.append(S('est agree 5/5', lambda d: (d['est']['ans'] if d.get('est') and d['est']['n'] >= 5 and d['est']['agree'] == 5 else None)))
sig.append(S('prec ref unanimous', lambda d: (d['prec']['ans'] if d['prec'].get('level') == 'ref' and d['prec'].get('unan') else None)))
sig.append(S('prec ref unanimous n>=3', lambda d: (d['prec']['ans'] if d['prec'].get('level') == 'ref' and d['prec'].get('unan') and d['prec']['n'] >= 3 else None)))
sig.append(S('prec ref tier<=1', lambda d: (d['prec']['ans'] if d['prec'].get('level') == 'ref' and d['prec'].get('tier', 9) <= 1 else None)))
for c in (0.8, 1.0):
    sig.append(S(f'group cons>={c} n>=3', lambda d, c=c: (d['g']['ans'] if d.get('g') and d['g']['cons'] >= c and d['g']['n'] >= 3 else None)))
sig.append(S('group best>=0.4 cons1', lambda d: (d['g']['ans'] if d.get('g') and d['g']['best'] >= 0.4 and d['g']['cons'] >= 1 and d['g']['n'] >= 2 else None)))
sig.append(S('reason group vote', lambda d: (d['eng']['rg'] if d.get('eng') and d['eng'].get('rg') is not None else None)))
sig.append(S('combo ref', lambda d: d.get('cref')))
for t in (0.6, 0.7, 0.8):
    sig.append(S(f'semantic cos>={t}', lambda d, t=t: (SEM[d['i']]['ans'] if d['i'] in SEM and SEM[d['i']]['cos'] >= t else None)))
y = {d['i']: QA[d['i']][8] for d in D}
half = {d['i']: 0 if prod(QA[d['i']][0]) in HALF0 else 1 for d in D}


def apply(rule, d):
    a = None
    for name, f in rule:
        v = f(d)
        if v is None or (a is not None and v != a): return None
        a = v
    return a


cands = [r for k in (1, 2, 3) for r in itertools.combinations(sig, k)]
print('rules', len(cands))
res = []
for a, b in ((0, 1), (1, 0)):
    best = None
    for r in cands:
        hit = [(d['i'], apply(r, d)) for d in und if half[d['i']] == a]
        hit = [(i, v) for i, v in hit if v is not None]
        if len(hit) < MINN: continue
        acc = sum(v == y[i] for i, v in hit) / len(hit)
        if acc >= TARGET and (best is None or len(hit) > best[1]): best = (r, len(hit), acc)
    if not best: res.append({'tuned_on': a, 'rule': None}); continue
    ev = [(d['i'], apply(best[0], d)) for d in und if half[d['i']] == b]; ev = [(i, v) for i, v in ev if v is not None]
    res.append({'tuned_on': a, 'rule': [n for n, _ in best[0]], 'tune_n': best[1], 'eval_n': len(ev), 'eval_ok': sum(v == y[i] for i, v in ev)})
    print(res[-1])
# also: the single best rule on all undecided questions (optimistic, for reference only)
allb = sorted(((sum(apply(r, d) == y[d['i']] for d in und if apply(r, d) is not None), sum(apply(r, d) is not None for d in und), [n for n, _ in r]) for r in cands), key=lambda x: (-(x[0] / x[1] if x[1] >= 8 else 0), -x[1]))[:8]
print('reference (not honest) top rules on all undecided:', [(ok, n, r) for ok, n, r in allb])
json.dump({'undecided': len(und), 'honest': res, 'reference_top': allb}, open('paper/results/combo_search.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
