"""E50: 쟁점(이유 묶음) 인벤토리를 이전 팩 답변만으로 다시 만들고, 새 질문을 질문 문장으로 배정해 답을 낼 수 있는지 (시간 분할, 정직한 설정).

Why: the shipped reason groups were clustered with ALL answers (newest products included), so "group of a new question" leaks the
answer side.  Here the inventory uses OLDER answers only; a newest-product question is assigned to a group through its *question*
(neighbour retrieval: 2-gram / retriever cosine / RRF), and the group's unanimous answer is the prediction.
Cutoffs are chosen on a validation split of the older products (10 % of cards held out, queried against the rest), not on the test.
Usage: python issue_assign_eval.py <E.npy aligned with DOC>     (retriever embeddings of the official questions)
"""
import json, re, sys, collections, random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.cluster import AgglomerativeClustering

T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
DOC = [i for i, r in enumerate(QA) if r[0]]; POS = {i: k for k, i in enumerate(DOC)}
E = np.load(sys.argv[1]).astype(np.float32)
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    s = re.sub(r'[A-Z]{1,3}\d{0,2}-\d{2,3}', 'CARD', s); return re.sub(r'\d+', 'N', s)
def reason(a): return re.sub(r'^\s*(네|예|아니요|아니오|아뇨)[,，.\s]+[^.]*?니다\.\s*', '', cq(a), count=1).strip()
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
BG = {i: bg(QA[i][1]) for i in DOC}
yn = lambda i: QA[i][8] >= 0
pos = lambda i: QA[i][8] ^ QA[i][9]

old_all = [i for i in DOC if prod(QA[i][0]) not in NEW]
new_yn = [i for i in DOC if prod(QA[i][0]) in NEW and yn(i)]
cards = sorted({QA[i][0] for i in old_all}); random.Random(13).shuffle(cards)
vcards = set(cards[:len(cards) // 10])
val_q = [i for i in old_all if QA[i][0] in vcards and yn(i)]
inv_val = [i for i in old_all if QA[i][0] not in vcards]     # inventory/pool for the validation run


def build_groups(pool, thr, min_n, min_cards):
    idx = [i for i in pool if len(reason(QA[i][2])) >= 15]
    X = normalize(TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform([tpl(reason(QA[i][2])) for i in idx]))
    lab = AgglomerativeClustering(n_clusters=None, distance_threshold=thr, metric='cosine', linkage='average').fit(X.toarray()).labels_
    mem = collections.defaultdict(list)
    for i, g in zip(idx, lab): mem[int(g)].append(i)
    of = {}
    for g, ii in mem.items():
        if len(ii) >= min_n and len({QA[i][0] for i in ii}) >= min_cards:
            for i in ii: of[i] = g
    return of


def rank_scores(i, pool, how):
    """scores of pool items for query question i."""
    p = np.array([POS[j] for j in pool])
    cos = E[p] @ E[POS[i]]
    A = BG[i]; jc = np.array([len(A & BG[j]) / ((len(A) + len(BG[j]) - len(A & BG[j])) or 1) for j in pool], dtype=np.float32)
    rk = lambda s: np.argsort(np.argsort(-s)) + 1
    return {'2gram': jc, 'model': cos, 'rrf': 1 / (60 + rk(cos)) + 1 / (60 + rk(jc))}[how]


def predict(i, pool, of, how, topk=5):
    s = rank_scores(i, pool, how); o = np.argsort(-s)[:topk * 4]
    vote = collections.Counter()
    for r in o:
        j = pool[r]
        if j in of: vote[of[j]] += float(s[r])
        if sum(1 for _ in vote) >= topk: break
    if not vote: return None
    tot = sum(vote.values()); g, v = vote.most_common(1)[0]
    return g, v / tot, float(s[o[0]])


def group_answer(of, pool):
    ys = collections.defaultdict(list)
    for j in pool:
        if j in of and yn(j): ys[of[j]].append(pos(j))
    return {g: (np.mean(v), len(v)) for g, v in ys.items() if len(v) >= 2 and max(np.mean(v), 1 - np.mean(v)) >= 0.9}


def evaluate(queries, pool, of, how):
    GA = group_answer(of, pool); rows = []
    for i in queries:
        pr = predict(i, pool, of, how)
        if pr is None or pr[0] not in GA: continue
        p, n = GA[pr[0]]
        rows.append((pr[1] * pr[2], ((1 if p >= .5 else 0) ^ QA[i][9]) == QA[i][8], i))
    return rows


def curve(rows, nq):
    rows = sorted(rows, key=lambda r: -r[0]); out = []; ok = 0
    for k, r in enumerate(rows, 1):
        ok += r[1]; out.append((r[0], k, ok / k))
    return out


res = {}
engine = json.load(open('train/data/engine_test.json', encoding='utf-8'))
for thr in (0.35, 0.5, 0.65):
    for min_n, min_cards in ((2, 1), (3, 2)):
        of_val = build_groups(inv_val, thr, min_n, min_cards); of_old = build_groups(old_all, thr, min_n, min_cards)
        for how in ('2gram', 'model', 'rrf'):
            vr = evaluate(val_q, inv_val, of_val, how); cv = curve(vr, len(val_q))
            cut = next((c for c, k, a in reversed(cv) if a >= 0.97 and k >= 10), None)    # loosest cutoff with >=97 % on validation
            tr = evaluate(new_yn, old_all, of_old, how)
            sel = [r for r in tr if cut is not None and r[0] >= cut]
            eng_unsure = [r for r in sel if engine.get(str(r[2]), [0, 0, 0])[1] < 0.8]      # engine not confident (conf<0.8)
            key = f'd{thr}_min{min_n}x{min_cards}_{how}'
            res[key] = {'groups': len({g for g in of_old.values()}), 'val_cut': None if cut is None else round(cut, 4),
                        'test_reach': len(sel), 'test_acc': round(sum(r[1] for r in sel) / len(sel), 3) if sel else None,
                        'extra_where_engine_unsure': len(eng_unsure),
                        'extra_acc': round(sum(r[1] for r in eng_unsure) / len(eng_unsure), 3) if eng_unsure else None,
                        'assignable_any': len(tr)}
            print(key, res[key], flush=True)
json.dump(res, open('paper/results/e50_issue_assign.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
