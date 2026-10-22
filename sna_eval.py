"""E42: is the effect network (SNA) useful for judging? Time split (newest products = test, older = evidence).

For a test yes/no question on effect u, evidence = older official Q&A about effects linked to u in the network,
asking the same thing (it). Answer = weighted vote of their answers (aligned for negation). Compared with: same
fine cluster (what the engine uses now), and text-only top-1. Link reasons: s structure, p same processing step,
t same trigger, m name mention, c same card, q same Q&A issue (q is left out: it is built from Q&A incl. the test set).
  python sna_eval.py [net/effect_sna.json]  -> paper/results/sna_eval.json
"""
import json, re, sys, collections, math
import numpy as np
NETF = sys.argv[1] if len(sys.argv) > 1 else 'net/effect_sna.json'
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
U3 = json.load(open('units3.json', encoding='utf-8')); NET = json.load(open(NETF, encoding='utf-8'))
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}; HALF = [{'BT22', 'EX9', 'ST21'}, {'BT23', 'BT24', 'EX10', 'ST22'}]
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
byct = {(n['card'], n['text']): n['k'] for n in NET['nodes']}; CL = {n['k']: n['c'] for n in NET['nodes']}
node = lambda u: byct.get((U3[u]['card'], U3[u]['text'])) if u is not None and 0 <= u < len(U3) else None
SKIP = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else {'q'}
adj = collections.defaultdict(dict)
for a, b, _, _, why in NET['links']:
    sc = {w[0]: int(w[1:]) / 100 for w in why.split(',') if w and w[0] not in SKIP}
    if not sc: continue
    s = 1 - math.prod(1 - v for v in sc.values())
    adj[a][b] = max(adj[a].get(b, 0), s); adj[b][a] = max(adj[b].get(a, 0), s)
YN = [i for i, r in enumerate(QA) if r[0] and r[8] >= 0]
pool = [i for i in YN if prod(QA[i][0]) not in NEW]; test = [i for i in YN if prod(QA[i][0]) in NEW]
by_node = collections.defaultdict(list)
for j in pool:
    k = node(QA[j][3])
    if k is not None: by_node[k].append(j)
al = lambda j, i: QA[j][8] ^ (QA[j][9] ^ QA[i][9])
jac = lambda a, b: len(set(a) & set(b)) / (len(set(a) | set(b)) or 1)


def vote(i, cands):
    """cands: [(weight, j)] -> (answer, margin, n)"""
    c = [(w * (0.5 + jac(QA[i][7], QA[j][7])), al(j, i)) for w, j in cands if QA[j][6] == QA[i][6]]
    if not c: return None
    yes = sum(w for w, a in c if a); no = sum(w for w, a in c if not a)
    return (1 if yes >= no else 0, abs(yes - no) / (yes + no), len(c))


def run(kind, thr=0.0):
    rows = []
    for i in test:
        k = node(QA[i][3])
        if k is None: continue
        if kind == 'link':
            cands = [(s, j) for nb, s in adj[k].items() if s >= thr for j in by_node.get(nb, [])] + [(1.0, j) for j in by_node.get(k, [])]
        elif kind == 'cluster':
            c = CL[k]; cands = [(1.0, j) for nb in CLM[c] for j in by_node.get(nb, [])]
        v = vote(i, cands)
        if v: rows.append({'i': i, 'ans': v[0], 'm': v[1], 'n': v[2], 'ok': int(v[0] == QA[i][8]), 'half': 0 if prod(QA[i][0]) in HALF[0] else 1})
    return rows


CLM = collections.defaultdict(list)
for n in NET['nodes']: CLM[n['c']].append(n['k'])


def summarize(rows, name):
    n_all = sum(1 for i in test if node(QA[i][3]) is not None)
    out = {'answered': len(rows), 'of': n_all, 'acc': round(np.mean([r['ok'] for r in rows]), 4) if rows else None}
    # honest high-precision slice: margin threshold picked on one half, measured on the other
    sl = []
    for a, b in ((0, 1), (1, 0)):
        ra = sorted([r for r in rows if r['half'] == a], key=lambda r: -r['m'])
        best = None
        for t in sorted({round(r['m'], 3) for r in ra}, reverse=True):
            s = [r for r in ra if r['m'] >= t and r['n'] >= 2]
            if len(s) >= 15 and np.mean([r['ok'] for r in s]) >= 0.95: best = t
        ev = [r for r in rows if r['half'] == b and best is not None and r['m'] >= best and r['n'] >= 2]
        sl.append({'thr': best, 'answered': len(ev), 'acc': round(np.mean([r['ok'] for r in ev]), 4) if ev else None})
    out['high_precision'] = sl
    print(name, json.dumps(out, ensure_ascii=False))
    return out


res = {'net': NETF, 'skip': sorted(SKIP), 'test_with_node': sum(1 for i in test if node(QA[i][3]) is not None), 'n_test': len(test)}
res['cluster'] = summarize(run('cluster'), 'same cluster')
for thr in (0.0, 0.5, 0.7, 0.85):
    res[f'link>={thr}'] = summarize(run('link', thr), f'linked >= {thr}')
json.dump(res, open('paper/results/sna_eval.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- E42b: analog transfer = Q&A of structurally linked effects whose question (card names masked) reads the same ----
def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', 'X', s)
    s = re.sub(r'[A-Z]{1,3}\d{0,2}-\d{2,3}', 'X', s); return re.sub(r'\s+', '', re.sub(r'\d+', 'N', s))
bgs = lambda s: {s[i:i + 2] for i in range(len(s) - 1)}
TB = {i: bgs(tpl(QA[i][1])) for i in YN}
sim = lambda a, b: len(TB[a] & TB[b]) / (len(TB[a] | TB[b]) or 1)
import os
E = json.load(open('net/engine_py_test.json')) if os.path.exists('net/engine_py_test.json') else {}
eng_sure = {int(k) for k, v in E.items() if v[1] >= 0.8}


def analog(scope, thr=0.85):
    rows = []
    for i in test:
        k = node(QA[i][3])
        if k is None: continue
        if scope == 'sna':
            cands = [j for nb, s in adj[k].items() if s >= thr for j in by_node.get(nb, [])] + by_node.get(k, [])
        else:
            cands = pool
        best = max(((sim(i, j), j) for j in cands if QA[j][6] == QA[i][6]), default=None)
        if not best: continue
        s, j = best
        rows.append({'i': i, 'm': s, 'n': 2, 'ok': int(al(j, i) == QA[i][8]), 'half': 0 if prod(QA[i][0]) in HALF[0] else 1, 'eng': i in eng_sure})
    return rows


for scope, thr in (('all', 0), ('sna', 0.85), ('sna', 0.7), ('sna', 0.5)):
    rows = analog(scope, thr); name = f'analog {scope}' + (f'>={thr}' if scope == 'sna' else '')
    o = summarize(rows, name)
    for h, hp in zip((0, 1), o['high_precision']):
        ev = [r for r in rows if r['half'] != h and hp['thr'] is not None and r['m'] >= hp['thr']]
        hp['beyond_engine'] = sum(1 for r in ev if not r['eng']); hp['beyond_engine_ok'] = sum(r['ok'] for r in ev if not r['eng'])
    print('   beyond engine', [(hp['beyond_engine'], hp['beyond_engine_ok']) for hp in o['high_precision']])
    res[name] = o
json.dump(res, open('paper/results/sna_eval.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
