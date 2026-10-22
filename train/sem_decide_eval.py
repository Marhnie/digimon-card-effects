"""E37: can the server's semantic search DECIDE yes/no questions? (time split, honest thresholds)

For each newest-product yes/no question, take the top-1 older official Q&A by the server's fused ranking
(retriever cosine + 2-gram Jaccard, RRF as in qfuse.py) and answer with its official answer (aligned for negation).
Rules are gated by cosine and by structure agreement (same asked-thing / same situation slots / same effect pattern).
Thresholds are chosen on one half of the new products and measured on the other half (both directions).
Also reports how much it adds beyond what the page already decides (engine conf>=0.80, rule issues, exact precedents).
  python train/sem_decide_eval.py [model_dir]   -> paper/results/sem_decide_eval.json
"""
import json, os, re, sys, collections
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
MODEL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'train', 'runs', 'retriever_cpu', 'model')
from sentence_transformers import SentenceTransformer
from qfuse import Fuser

T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8')); QA = T['qa']; UN = T['units']
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
HALF = [{'BT22', 'EX9', 'ST21'}, {'BT23', 'BT24', 'EX10', 'ST22'}]
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
pat = lambda u: UN[u][10] if u is not None and u >= 0 else None
DOC = [i for i, r in enumerate(QA) if r[0]]
POOL = [i for i in DOC if prod(QA[i][0]) not in NEW and QA[i][8] >= 0]
TEST = [i for i in DOC if prod(QA[i][0]) in NEW and QA[i][8] >= 0]
print('pool yes/no', len(POOL), 'test yes/no', len(TEST))

m = SentenceTransformer(MODEL, device='cpu')
enc = lambda xs: m.encode(xs, normalize_embeddings=True, batch_size=64, show_progress_bar=False)
EP = enc([QA[i][1] for i in POOL]); ET = enc([QA[i][1] for i in TEST])
F = Fuser(QA, POOL)

rows = []
for k, i in enumerate(TEST):
    cos = EP @ ET[k]
    h = F.hits(QA[i][1], cos, 3)
    j = h[0]['i']; c = h[0]['cos']
    ans = QA[j][8] ^ (QA[j][9] ^ QA[i][9])
    rows.append({'i': i, 'j': j, 'cos': c, 'jac': h[0]['jac'], 'ok': int(ans == QA[i][8]), 'ans': ans,
                 'same_it': QA[j][6] == QA[i][6], 'same_sl': QA[j][7] == QA[i][7], 'same_pat': pat(QA[j][3]) is not None and pat(QA[j][3]) == pat(QA[i][3]),
                 'agree2': (QA[h[1]['i']][8] ^ (QA[h[1]['i']][9] ^ QA[i][9])) == ans, 'half': 0 if prod(QA[i][0]) in HALF[0] else 1})

RULES = {
    'cos': lambda r: True,
    'cos+it': lambda r: r['same_it'],
    'cos+it+sl': lambda r: r['same_it'] and r['same_sl'],
    'cos+it+sl+agree2': lambda r: r['same_it'] and r['same_sl'] and r['agree2'],
    'cos+it+agree2': lambda r: r['same_it'] and r['agree2'],
}


def best_thr(rs, rule, target=0.98, min_n=10):
    cand = sorted({round(r['cos'], 3) for r in rs if RULES[rule](r)}, reverse=True)
    best = None
    for t in cand:
        s = [r for r in rs if RULES[rule](r) and r['cos'] >= t]
        if len(s) >= min_n and sum(r['ok'] for r in s) / len(s) >= target: best = t
    return best


E = json.load(open(os.path.join(ROOT, 'net', 'engine_py_test.json')))
eng_sure = {int(k) for k, v in E.items() if v[1] >= 0.8}
out = {'n_test': len(TEST), 'rules': {}}
for rule in RULES:
    res = []
    for a, b in ((0, 1), (1, 0)):
        t = best_thr([r for r in rows if r['half'] == a], rule)
        ev = [r for r in rows if r['half'] == b and t is not None and RULES[rule](r) and r['cos'] >= t]
        res.append({'tune_half': a, 'thr': t, 'eval_n': sum(1 for r in rows if r['half'] == b), 'answered': len(ev),
                    'acc': round(sum(r['ok'] for r in ev) / len(ev), 4) if ev else None,
                    'beyond_engine': sum(1 for r in ev if r['i'] not in eng_sure), 'beyond_engine_ok': sum(r['ok'] for r in ev if r['i'] not in eng_sure)})
    out['rules'][rule] = res
    print(rule, res)
# a single threshold for the page: the stricter of the two halves' choices, measured on all test items
for rule in RULES:
    ts = [x['thr'] for x in out['rules'][rule] if x['thr'] is not None]
    if not ts: continue
    t = max(ts); s = [r for r in rows if RULES[rule](r) and r['cos'] >= t]
    be = [r for r in s if r['i'] not in eng_sure]
    out['rules'][rule].append({'page_thr': t, 'answered_all': len(s), 'acc_all': round(sum(r['ok'] for r in s) / len(s), 4) if s else None,
                               'beyond_engine': len(be), 'beyond_engine_acc': round(sum(r['ok'] for r in be) / len(be), 4) if be else None})
    print('  page', rule, out['rules'][rule][-1])
json.dump(out, open(os.path.join(ROOT, 'paper', 'results', 'sem_decide_eval.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(rows, open(os.path.join(ROOT, 'net', 'sem_decide_rows.json'), 'w'))
