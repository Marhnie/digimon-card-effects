"""Engine lite (E19b): the selective Claude-free judge using ONLY signals the judge-helper page computes in the browser
(character-bigram Jaccard over questions, the page's negation flag, effect pattern / cluster, reason groups), so the
weights learned here can be shipped into the page. Same time split as engine_sel.py (newest products = test).
Output: net/engine_lite.json (weights + thresholds for the page), paper/results/engine_lite.json (accuracy–coverage)."""
import json, re, collections, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.cluster import AgglomerativeClustering

T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']; UN = T['units']; ST = T['st']
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
bg = lambda s: {s[i:i + 2] for i in range(len(re.sub(r'\s+', '', s)) - 1)} if False else (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
L = [i for i, r in enumerate(QA) if r[8] >= 0 and r[0]]
y = {i: QA[i][8] for i in L}; ng = {i: QA[i][9] for i in L}
BG = {i: bg(QA[i][1]) for i in range(len(QA))}
pat = lambda u: UN[u][10] if u is not None and u >= 0 else None
clu = lambda u: ST[u][6] if u is not None and u >= 0 else -1
test = [i for i in L if prod(QA[i][0]) in NEW]; pool = [i for i in L if prod(QA[i][0]) not in NEW]; poolset = set(pool)
print('yes/no Q&A', len(L), 'pool', len(pool), 'test', len(test))

# reason groups from the pool only (explanations in the answers)
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    s = re.sub(r'[A-Z]{1,3}\d{0,2}-\d{2,3}', 'CARD', s); return re.sub(r'\d+', 'N', s)
reason = lambda a: tpl(re.sub(r'^\s*(네|예|아니요|아니오|아뇨)[,，.\s]+[^.]*?니다\.\s*', '', cq(a), count=1).strip())
def reason_groups(ids):
    ids = [i for i in ids if len(reason(QA[i][2])) >= 15]
    X = normalize(TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform([reason(QA[i][2]) for i in ids]))
    lab = AgglomerativeClustering(n_clusters=None, distance_threshold=0.35, metric='cosine', linkage='average').fit(X.toarray()).labels_
    g = dict(zip(ids, lab)); m = collections.defaultdict(list)
    for i, l in g.items():
        if QA[i][8] >= 0: m[l].append(QA[i][8] ^ QA[i][9])
    good = {l: (int(np.mean(v) >= .5), max(np.mean(v), 1 - np.mean(v))) for l, v in m.items() if len(v) >= 3 and max(np.mean(v), 1 - np.mean(v)) >= 0.9}
    return g, good
RGp, GOODp = reason_groups([i for i in range(len(QA)) if prod(QA[i][0]) not in NEW and QA[i][0]])

import os
DX = json.load(open('collab/dcgo_effects.json', encoding='utf-8')) if os.environ.get('DCGO_FEAT') else None
FN = ['vote5', 'top1', 'top1y', 'agree5', 'n_hi', 'rg_vote', 'rg_str', 'clu_vote', 'same_card_vote'] + (['dx_skip', 'dx_again', 'dx_leave', 'dx_inh'] if DX else [])
def feats(i, cand, RG, GOOD, exclude=None):
    A = BG[i]; u = QA[i][3]; my = ng[i]; sc = []
    for j in cand:
        if j == i or (exclude and exclude(j)): continue
        B = BG[j]; x = len(A & B); s = x / ((len(A) + len(B) - x) or 1)
        if s < 0.12: continue
        if QA[j][0] == QA[i][0]: s += 0.12
        if pat(u) is not None and pat(QA[j][3]) == pat(u): s += 0.08
        sc.append((s, j))
    sc.sort(reverse=True); top = sc[:10]
    if not top: return [0] * len(FN)
    al = lambda j: y[j] ^ (ng[j] ^ my)
    t5 = top[:5]; w = [(s ** 3, al(j)) for s, j in t5]; yes = sum(a for a, b in w if b); no = sum(a for a, b in w if not b)
    vote = (yes - no) / ((yes + no) or 1); ans = 1 if yes >= no else 0
    agree = sum(1 for s, j in t5 if al(j) == ans) / len(t5)
    acc = collections.defaultdict(float)
    for s, j in top:
        g = RG.get(j)
        if g in GOOD and s > 0.3: acc[g] += s * s
    if acc:
        g = max(acc, key=acc.get); gy, gc = GOOD[g]; rv, rs = (2 * (gy ^ my) - 1) * gc, acc[g]
    else: rv = rs = 0
    cu = clu(u); cw = [(s ** 2, al(j)) for s, j in top if cu >= 0 and clu(QA[j][3]) == cu]
    cv = (sum(a for a, b in cw if b) - sum(a for a, b in cw if not b)) / ((sum(a for a, b in cw)) or 1) if cw else 0
    sw = [(s, al(j)) for s, j in top if QA[j][0] == QA[i][0]]
    scv = (sum(1 for s, b in sw if b) - sum(1 for s, b in sw if not b)) / len(sw) if sw else 0
    base = [vote, top[0][0], 2 * al(top[0][1]) - 1, agree, sum(1 for s, j in top if s >= 0.45), rv, rs, cv, scv]
    if DX is None: return base
    q = QA[i][1]; c = QA[i][0]; ic = re.findall(r'【([^】]+)】', q)
    bs = [b for b in DX.get(c, []) if b['tags'] and (not ic or set(ic) & set(b['tags']))]
    has = 1 if bs else 0
    opt = float(any(b['optional'] or b['noselect'] or b['endnotmax'] for b in bs)); once = float(any(b['once'] for b in bs))
    rec = float(any(b['recheck_field'] for b in bs)); inh = float(any(b['inherited'] for b in DX.get(c, [])))
    sk = 1 if re.search(r'(하지\s*않|않고|않을\s*수|선택하지\s*않|일부만)', q) else 0
    ag = 1 if re.search(r'(다시|두 번|2번|2회|한 번 더|재차)', q) else 0
    lv = 1 if re.search(r'(벗어|소멸한|되돌아|되돌린|패로|덱으로|트래시로)', q) else 0
    sg = 1 if my else -1
    return base + [sg * has * sk * (2 * opt - 1), sg * has * ag * (1 - 2 * once), sg * has * lv * (1 - 2 * rec), sg * inh * (1 if '진화원' in q else 0)]

# near-duplicate groups inside the pool so its CV does not see restatements (same rule as engine_sel)
grp = {}
for i in pool: grp[i] = i
def root(i):
    while grp[i] != i: grp[i] = grp[grp[i]]; i = grp[i]
    return i
for a in pool:
    A = BG[a]
    for b in pool:
        if b <= a: continue
        B = BG[b]; x = len(A & B); s = x / ((len(A) + len(B) - x) or 1)
        if s > 0.8 or (QA[a][0] == QA[b][0] and s > 0.55): grp[root(a)] = root(b)
G = np.array([root(i) for i in pool])
print('pool near-duplicate groups', len(set(G)))
P = np.array(pool); Yp = np.array([y[i] for i in pool]); Xp = np.zeros((len(pool), len(FN)))
for tr, te in GroupKFold(5).split(P, groups=G):
    cand = set(P[tr]); gte = set(G[te])
    for k in te:
        i = P[k]; Xp[k] = feats(i, cand, RGp, GOODp)
Xt = np.array([feats(i, poolset, RGp, GOODp) for i in test]); Yt = np.array([y[i] for i in test])
mu, sd = Xp.mean(0), Xp.std(0) + 1e-9; Zp, Zt = (Xp - mu) / sd, (Xt - mu) / sd
A = LogisticRegression(C=1.0, max_iter=3000).fit(Zp, Yp)
# correctness model: trained on the pool's out-of-fold answers
oof = np.zeros(len(pool))
for tr, te in GroupKFold(5).split(P, groups=G): oof[te] = LogisticRegression(C=1.0, max_iter=3000).fit(Zp[tr], Yp[tr]).predict_proba(Zp[te])[:, 1]
cfeat = lambda Z, p: np.hstack([Z, np.abs(p - .5)[:, None], (np.abs(p - .5)[:, None] * Z[:, [1, 3, 6]])])
C = LogisticRegression(C=0.5, max_iter=3000).fit(cfeat(Zp, oof), ((oof > .5) == Yp).astype(int))
pt = A.predict_proba(Zt)[:, 1]; pred = (pt > .5).astype(int); conf = C.predict_proba(cfeat(Zt, pt))[:, 1]
o = np.argsort(-conf)
def cov(t):
    ok = [k for k in range(20, len(o) + 1) if (pred[o[:k]] == Yt[o[:k]]).mean() >= t]
    return (max(ok) / len(o), float(conf[o[max(ok) - 1]])) if ok else (0, 1)
c95, c97 = cov(.95), cov(.97)
curve = [{'coverage': c, 'acc': round(float((pred[o[:int(c * len(o))]] == Yt[o[:int(c * len(o))]]).mean()), 4)} for c in (.1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0)]
print('answer everything', (pred == Yt).mean().round(3), '| cov@95', round(c95[0], 3), 'thr', round(c95[1], 3), '| cov@97', round(c97[0], 3), 'thr', round(c97[1], 3))
for c in curve: print(f"  {c['coverage']:.0%}: {c['acc']:.1%}")
json.dump({'n_test': len(test), 'acc_all': round(float((pred == Yt).mean()), 4), 'cov95': c95, 'cov97': c97, 'curve': curve},
          open(os.environ.get('OUTJ','collab/engine_dcgo.json'), 'w', encoding='utf-8'), indent=1)

for thr in (0.75, 0.80, 0.85):
    m = conf >= thr; print('thr', thr, 'cov', round(m.mean(), 3), 'acc', round((pred[m] == Yt[m]).mean(), 4))
print('coef', dict(zip(FN, A.coef_[0].round(3))))
