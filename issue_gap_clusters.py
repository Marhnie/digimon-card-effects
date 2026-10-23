"""E50: 판정 못 하는 최신 팩 질문(엔진 확신<0.8, 쟁점 없음)을 의미 임베딩으로 묶어, 심판이 한 번 답하면 여러 질문이 풀리는 「새 쟁점 후보」를 만든다.
Usage: python issue_gap_clusters.py <E.npy>   -> paper/results/e50_gap_clusters.json"""
import json, re, sys, collections
import numpy as np
from sklearn.cluster import AgglomerativeClustering
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
OF = {int(k): v for k, v in T['rg']['of'].items()}
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
DOC = [i for i, r in enumerate(QA) if r[0]]; POS = {i: k for k, i in enumerate(DOC)}
E = np.load(sys.argv[1]).astype(np.float32)
eng = json.load(open('train/data/engine_test.json', encoding='utf-8'))
yn = lambda i: QA[i][8] >= 0; pos = lambda i: QA[i][8] ^ QA[i][9]
gap = [i for i in DOC if prod(QA[i][0]) in NEW and yn(i) and eng.get(str(i), [0, 0, 0])[1] < 0.8]
print('gap', len(gap))
X = E[[POS[i] for i in gap]]
res = {}
for thr in (0.25, 0.35, 0.45):
    lab = AgglomerativeClustering(n_clusters=None, distance_threshold=thr, metric='cosine', linkage='average').fit(X).labels_
    mem = collections.defaultdict(list)
    for i, g in zip(gap, lab): mem[int(g)].append(i)
    cl = [v for v in mem.values() if len(v) >= 3]
    cons = [max(np.mean([pos(i) for i in v]), 1 - np.mean([pos(i) for i in v])) for v in cl]
    unan = [v for v, c in zip(cl, cons) if c >= 0.9]
    res[str(thr)] = {'clusters>=3': len(cl), 'items_in': sum(map(len, cl)), 'unanimous_clusters': len(unan), 'items_in_unanimous': sum(map(len, unan)), 'mean_consistency': round(float(np.mean(cons)), 3) if cons else None}
    print(thr, res[str(thr)])
thr = 0.35
lab = AgglomerativeClustering(n_clusters=None, distance_threshold=thr, metric='cosine', linkage='average').fit(X).labels_
mem = collections.defaultdict(list)
for i, g in zip(gap, lab): mem[int(g)].append(i)
out = []
for v in sorted(mem.values(), key=lambda v: -len(v)):
    if len(v) < 3: break
    c = np.mean([pos(i) for i in v]); cen = X[[gap.index(i) for i in v]].mean(0); rep = v[int(np.argmax(X[[gap.index(i) for i in v]] @ cen))]
    out.append({'n': len(v), 'agree': round(float(max(c, 1 - c)), 2), 'representative': QA[rep][1], 'qa_index': rep, 'members': v, 'cards': sorted({QA[i][0] for i in v})[:6]})
json.dump({'stats': res, 'clusters@0.35': out}, open('paper/results/e50_gap_clusters.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for o in out[:8]: print(o['n'], o['agree'], o['representative'][:80])
