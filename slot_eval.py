"""E44: which situation slots can be ignored when matching precedents? Learned from OLDER products only, measured on the newest.
Pairs of older yes/no Q&A on the same effect (pattern or rulebook structure) asking the same thing: does the answer (aligned for
negation) still agree when the two questions differ in slot x? A logistic model on 'slot x is in the symmetric difference'
gives each slot's effect on agreement; slots whose difference does not lower agreement are dropped from the match key.
  python slot_eval.py  -> paper/results/slot_eval.json, net/slot_drop.json
"""
import json, re, collections, itertools
import numpy as np
from sklearn.linear_model import LogisticRegression
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']; U = T['units']; ST = T['st']; SL = T['form']['slots']
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}; HALF = [{'BT22', 'EX9', 'ST21'}, {'BT23', 'BT24', 'EX10', 'ST22'}]
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
NEG = len(SL) - 1
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
simQ = lambda a, b: (lambda A, B: len(A & B) / (len(A | B) or 1))(bg(a), bg(b))
def sig(u):
    s = ST[u]
    if not s or not s[4]: return None
    return (s[0], tuple(sorted(s[1])), len(s[2]) > 0, tuple(tuple(x[:4]) for x in s[4]))
YN = [i for i, r in enumerate(QA) if r[0] and r[8] >= 0 and r[3] is not None and r[3] >= 0]
pool = [i for i in YN if prod(QA[i][0]) not in NEW]; test = [i for i in YN if prod(QA[i][0]) in NEW]
al = lambda j, i: QA[j][8] ^ (QA[j][9] ^ QA[i][9])
eff = lambda i: (U[QA[i][3]][10], sig(QA[i][3]))
same_eff = lambda a, b: eff(a)[0] == eff(b)[0] or (eff(a)[1] is not None and eff(a)[1] == eff(b)[1])

# ---- learn slot relevance on pool pairs ----
grp = collections.defaultdict(list)
for i in pool: grp[(QA[i][6], U[QA[i][3]][10])].append(i)
X, Y = [], []
for ks in grp.values():
    for a, b in itertools.combinations(ks, 2):
        d = set(QA[a][7]) ^ set(QA[b][7]); d.discard(NEG)
        x = np.zeros(len(SL)); x[list(d)] = 1; X.append(x); Y.append(int(al(a, b) == QA[b][8]))
X, Y = np.array(X), np.array(Y)
print('pool pairs (same effect pattern, same asked thing):', len(Y), 'agree rate', Y.mean().round(3))
m = LogisticRegression(C=1.0, max_iter=2000).fit(X, Y)
cnt = X.sum(0)
coef = {k: (round(float(m.coef_[0][k]), 3), int(cnt[k])) for k in range(len(SL))}
for k in sorted(coef, key=lambda k: coef[k][0]): print(f'  {SL[k][1]:<12} coef {coef[k][0]:+.3f}  pairs differing {coef[k][1]}')


def evaluate(drop):
    keyf = lambda i: (QA[i][6], tuple(sorted(set(QA[i][7]) - drop - {NEG})))
    by = collections.defaultdict(list)
    for j in pool: by[keyf(j)].append(j)
    rows = []
    for i in test:
        c = [j for j in by.get(keyf(i), []) if same_eff(i, j)]
        if not c: continue
        ys = [al(j, i) for j in c]; ans = int(sum(ys) * 2 >= len(ys))
        if all(y == ans for y in ys): rows.append({'ok': int(ans == QA[i][8]), 'half': 0 if prod(QA[i][0]) in HALF[0] else 1})
    return rows


res = {'coef': {SL[k][1]: v for k, v in coef.items()}, 'runs': []}
for thr in (None, 0.3, 0.1, 0.0, -0.1, -0.2):
    drop = set() if thr is None else {k for k in range(len(SL)) if k != NEG and coef[k][0] >= thr and coef[k][1] >= 20}
    r = evaluate(drop); h = [[sum(x['ok'] for x in r if x['half'] == hh), sum(1 for x in r if x['half'] == hh)] for hh in (0, 1)]
    out = {'thr': thr, 'dropped': sorted(SL[k][1] for k in drop), 'sure': len(r), 'acc': round(sum(x['ok'] for x in r) / max(1, len(r)), 4), 'halves': h}
    res['runs'].append(out); print(json.dumps(out, ensure_ascii=False))
json.dump(res, open('paper/results/slot_eval.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
