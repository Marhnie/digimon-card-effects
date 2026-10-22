"""E31 follow-up: does fusing the 2-gram score with the fine-tuned retriever's cosine beat either alone? (no training; CPU ok)

Fusions (all per query over its own corpus):  model | 2-gram | RRF (k=60) | z-score mean | alpha*cos+(1-alpha)*jac for alpha in a grid.
Queries: time split (newest-product official questions -> older Q&A) and the colloquial test set (source removed).
Caveat: the colloquial dev set is NOT usable to choose alpha (its source Q&As are in the training pool); the grid is shown for
inspection only — prefer the parameter-free RRF / z-score rows when reporting.

  python train/fuse_eval.py --model train/runs/retriever_base/model        # weights live on the GPU machine (not committed)
  python train/fuse_eval.py --model sentence-transformers-testing/stsb-bert-tiny-safetensors --tiny   # code smoke test
"""
import argparse, json, os, re, sys, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--out', default=None)
ap.add_argument('--tiny', action='store_true'); a = ap.parse_args()
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8')); QA = T['qa']
OF = {int(k): v for k, v in T['rg']['of'].items()}
pol = lambda i: (QA[i][8] ^ QA[i][9]) if QA[i][8] >= 0 else None
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
jac = lambda A, B: len(A & B) / ((len(A) + len(B) - len(A & B)) or 1)
CS = json.load(open(os.path.join(ROOT, 'paper/results/colloquial_test.json'), encoding='utf-8'))['items']
BANNED = {x['qid'] for x in CS}
DOC = [i for i, r in enumerate(QA) if r[0]]
POOL = set(i for i in DOC if prod(QA[i][0]) not in NEW and i not in BANNED)
TESTQ = [i for i in DOC if prod(QA[i][0]) in NEW]
GRP = collections.defaultdict(set)
for i, g in OF.items(): GRP[g].add(i)
bycard = collections.defaultdict(set)
for i in DOC: bycard[QA[i][0]].add(i)
gold = lambda i, c: {j for j in GRP.get(OF.get(i), ()) if j in c and (pol(j) == pol(i) or pol(i) is None or pol(j) is None)} if i in OF else set()
ts = [(QA[i][1], POOL, gold(i, POOL)) for i in TESTQ]
co = [(x['colloquial'], (POOL | bycard[x['card']]) - {x['qid']}, gold(x['qid'], (POOL | bycard[x['card']]) - {x['qid']})) for x in CS]
SETS = {'time_split': [t for t in ts if t[2]], 'colloquial': [t for t in co if t[2]]}
# E38: under-specified versions of the colloquial items (same generator and seed as train_retriever.build_eval)
import random
_src = open(os.path.join(HERE, 'train_retriever.py'), encoding='utf-8').read()
exec(_src[_src.index('SUBS = '):_src.index('CTX = {}')])
_vr = random.Random(7)
SETS['vague'] = [(vague(QA[x['qid']][1], _vr), c, g) for x, (_, c, g) in zip(CS, co) if g]
if a.tiny: SETS = {k: v[:30] for k, v in SETS.items()}
from sentence_transformers import SentenceTransformer
m = SentenceTransformer(a.model)
E = dict(zip(DOC, m.encode([QA[i][1] for i in DOC], normalize_embeddings=True, batch_size=128, show_progress_bar=False)))
BG = {i: bg(QA[i][1]) for i in DOC}
z = lambda v: (v - v.mean()) / (v.std() or 1)
def scorers(cos, jc):
    rk = lambda s: np.argsort(np.argsort(-s)) + 1
    out = {'model': cos, '2gram': jc, 'rrf': 1 / (60 + rk(cos)) + 1 / (60 + rk(jc)), 'zmean': z(cos) + z(jc)}
    for al in (0.25, 0.5, 0.75): out[f'alpha{al}'] = al * cos + (1 - al) * jc
    return out
res = {}
for name, items in SETS.items():
    hit = collections.defaultdict(lambda: {1: 0, 3: 0, 10: 0})
    qv = m.encode([t for t, _, _ in items], normalize_embeddings=True, batch_size=128, show_progress_bar=False)
    for (t, c, g), v in zip(items, qv):
        c = sorted(c); cos = np.stack([E[j] for j in c]) @ v; q = bg(t); jc = np.array([jac(q, BG[j]) for j in c])
        for k, s in scorers(cos, jc).items():
            top = [c[x] for x in np.argsort(-s)[:10]]
            for kk in (1, 3, 10): hit[k][kk] += bool(g & set(top[:kk]))
    n = len(items)
    res[name] = {'n': n, **{k: {f'recall@{kk}': round(h[kk] / n, 3) for kk in (1, 3, 10)} for k, h in hit.items()}}
    print(name, json.dumps(res[name], ensure_ascii=False, indent=0))
out = a.out or os.path.join(HERE, 'runs', 'fuse_eval' + ('_tiny' if a.tiny else '') + '.json')
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
