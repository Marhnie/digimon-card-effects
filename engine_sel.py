"""Selective Claude-free ruling engine (E19).
Time split: the engine may only use card Q&A of OLDER products; it is tested on the Q&A of the newest products
(the real situation: a new set's questions answered from past rulings). It answers only when its calibrated
confidence clears a threshold; the rest goes to Claude. Reports the accuracy–coverage curve.
usage: python engine_sel.py            -> paper/results/engine_sel.json, net/engine_model.json (weights for the page)"""
import json, re, collections, numpy as np, os
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import normalize

NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}          # newest products = test
QI = json.load(open('qa_items.json', encoding='utf-8'))
U = json.load(open('units3.json', encoding='utf-8'))
S2 = {s['i']: s for s in json.load(open('struct2.json', encoding='utf-8'))}
NET = json.load(open('net/effect_sna.json', encoding='utf-8'))
_nodes = [s for s in json.load(open('struct2.json', encoding='utf-8')) if s['분류'] != '카드 정보(효과 아님)']
CLU = {s['i']: NET['nodes'][k]['c'] for k, s in enumerate(_nodes)}
TRIG_TM = {'등장 시', '진화 시', '소멸 시', '어택 시', '링크 시', '시큐리티', '자신의 턴 개시 시', '상대의 턴 개시 시', '자신의 턴 종료 시', '상대의 턴 종료 시',
           '서로의 턴 종료 시', '자신의 메인 페이즈 개시 시', '상대의 메인 페이즈 개시 시', '어택 종료 시', '이동 시'}
def trig(i):
    s = S2.get(i)
    if not s: return ''
    k = ['【' + x + '】' for x in s.get('타이밍', []) if x in TRIG_TM] + ([s['유발 키']] if s.get('유발 키') else [])
    return k[0] if k else ''

cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
lab = lambda a: 1 if re.match(r'^\s*(네|예)[,，.\s]', a) else (0 if re.match(r'^\s*(아니요|아니오|아뇨)[,，.\s]', a) else None)
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
D = []
for q in QI:
    y = lab(cq(q['a']))
    if y is None or not q['card']: continue
    u = q['unit']
    D.append({'id': q['id'], 'card': q['card'], 'q': cq(q['q']), 'y': y, 'unit': u, 'new': prod(q['card']) in NEW,
              'pat': U[u]['pattern'] if u is not None else -1, 'types': U[u]['types'] if u is not None else [],
              'clu': CLU.get(u, -1) if u is not None else -1, 'trig': trig(u) if u is not None else '', 'grp': S2[u]['group'] if u is not None and u in S2 else ''})
n = len(D); Y = np.array([d['y'] for d in D]); NEWM = np.array([d['new'] for d in D])
print('items', n, 'test(new products)', int(NEWM.sum()), 'pool', int((~NEWM).sum()), 'yes rate', Y.mean().round(3))

def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    s = re.sub(r'[A-Z]{1,3}\d{0,2}-\d{2,3}', 'CARD', s)
    return re.sub(r'\d+', 'N', s)
raw = [d['q'] for d in D]; tq = [tpl(d['q']) for d in D]
V1 = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit(raw)
V2 = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit(tq)
X = normalize(hstack([V1.transform(raw), V2.transform(tq)]).tocsr())
S = (X @ X.T).toarray(); np.fill_diagonal(S, 0)
cards = np.array([d['card'] for d in D]); pats = np.array([d['pat'] for d in D]); clus = np.array([d['clu'] for d in D])
trigs = np.array([d['trig'] for d in D]); grps = np.array([d['grp'] for d in D]); type_sets = [set(d['types']) for d in D]
NEG = re.compile(r'(?:없|않|못|아닌|아니)[^「」]{0,6}[?？]?\s*$|(?:없|않|못)(?:습니까|나요|는지|을까요|게 되나요|게 됩니까)')
neg = np.array([1 if NEG.search(d['q']) else 0 for d in D])

# near-duplicate groups inside the pool, so the pool's own CV never sees a restatement of the item
par = list(range(n))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for a, b in zip(*np.where(np.triu(S, 1) > 0.80)): par[f(a)] = f(b)
for a, b in zip(*np.where(np.triu(S, 1) > 0.55)):
    if cards[a] == cards[b]: par[f(a)] = f(b)
G = np.array([f(i) for i in range(n)])

FN = ['knn', 'top1sim', 'top1y', 'top3y', 'n_hi', 'agree_hi', 'same_clu_vote', 'same_trig_vote', 'same_grp_vote', 'pat_prior', 'type_prior', 'text', 'rg_vote', 'rg_strength', 'rg_size']
def feats(test_idx, train_mask, exclude_group=True, k=9, p=3.0):
    out = np.zeros((len(test_idx), 9))
    for r, i in enumerate(test_idx):
        s = S[i].copy(); s[~train_mask] = -1
        if exclude_group: s[G == G[i]] = -1
        top = np.argpartition(-s, k)[:k]; top = top[np.argsort(-s[top])]
        yy = Y[top] ^ (neg[top] ^ neg[i])
        w = np.clip(s[top], 0, None) ** p
        for t, j in enumerate(top):
            if pats[i] >= 0 and pats[j] == pats[i]: w[t] *= 1.8
            elif type_sets[i] & type_sets[j]: w[t] *= 1.25
            if clus[i] >= 0 and clus[j] == clus[i]: w[t] *= 1.3
        sv = lambda m: ((w * m * (2 * yy - 1)).sum() / ((w * m).sum() + 1e-9))
        hi = s[top] >= 0.6
        out[r] = [sv(np.ones(k)), s[top[0]], 2 * yy[0] - 1, (2 * yy[:3] - 1).mean(), hi.sum(),
                  (abs((2 * yy[hi] - 1).mean()) if hi.any() else 0),
                  sv((clus[top] == clus[i]) & (clus[i] >= 0)), sv((trigs[top] == trigs[i]) & (trigs[i] != '')), sv((grps[top] == grps[i]) & (grps[i] != ''))]
    return out
def prior(test_idx, train_mask):
    base = Y[train_mask].mean(); pc = collections.defaultdict(lambda: [0, 0]); tc = collections.defaultdict(lambda: [0, 0])
    for j in np.where(train_mask)[0]:
        if pats[j] >= 0: pc[pats[j]][0] += Y[j]; pc[pats[j]][1] += 1
        for t in type_sets[j]: tc[t][0] += Y[j]; tc[t][1] += 1
    o = np.zeros((len(test_idx), 2))
    for r, i in enumerate(test_idx):
        a, b = pc[pats[i]] if pats[i] >= 0 else (0, 0); o[r, 0] = (a + 3 * base) / (b + 3) - base
        o[r, 1] = np.mean([(tc[t][0] + 5 * base) / (tc[t][1] + 5) for t in type_sets[i]] or [base]) - base
    return o
VW = TfidfVectorizer(analyzer='word', token_pattern=r'[^\s]+', ngram_range=(1, 2), min_df=2, sublinear_tf=True)
VC = TfidfVectorizer(analyzer='char', ngram_range=(1, 3), min_df=3, sublinear_tf=True)
def text(train_idx, test_idx):
    A = hstack([VW.fit_transform([tq[i] for i in train_idx]), VC.fit_transform([tq[i] for i in train_idx])]).tocsr()
    B = hstack([VW.transform([tq[i] for i in test_idx]), VC.transform([tq[i] for i in test_idx])]).tocsr()
    return LogisticRegression(C=2.0, max_iter=2000).fit(A, Y[train_idx]).decision_function(B)
def F(train_idx, test_idx, exclude_group=True):
    m = np.zeros(n, bool); m[train_idx] = True
    return np.hstack([feats(test_idx, m, exclude_group), prior(test_idx, m), text(train_idx, test_idx)[:, None], rg_feats(test_idx, m, exclude_group)])

pool = np.where(~NEWM)[0]; test = np.where(NEWM)[0]
# ---- reason groups: the official answers' explanation (after the 「네/아니요」 sentence), templated and clustered — built from the pool only
from sklearn.cluster import AgglomerativeClustering
AQ = {q['id']: cq(q['a']) for q in QI}
def reason(a):
    a = re.sub(r'^\s*(네|예|아니요|아니오|아뇨)[,，.\s]+[^.]*?니다\.\s*', '', a, count=1)
    return tpl(a.strip())
RS = [reason(AQ[d['id']]) for d in D]
has_r = np.array([len(r) >= 15 for r in RS])
pr_idx = pool[has_r[pool]]
VR = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit([RS[i] for i in pr_idx])
XR = normalize(VR.transform([RS[i] for i in pr_idx]))
agg = AgglomerativeClustering(n_clusters=None, distance_threshold=0.35, metric='cosine', linkage='average').fit(XR.toarray())
RG = np.full(n, -1); RG[pr_idx] = agg.labels_
rg_lab = collections.defaultdict(list)
for i in pr_idx: rg_lab[RG[i]].append(Y[i] ^ neg[i])           # answer as if the question were asked positively
rg_cons = {g: (max(np.mean(v), 1 - np.mean(v)), int(np.mean(v) >= 0.5), len(v)) for g, v in rg_lab.items()}
big = {g for g, (c, _, m) in rg_cons.items() if m >= 3 and c >= 0.9}
print('reason groups', len(rg_lab), 'with >=3 Q&A and >=90% same answer', len(big), 'covering', sum(rg_cons[g][2] for g in big), 'pool Q&A')
def rg_feats(test_idx, train_mask, exclude_group=True, k=15):
    o = np.zeros((len(test_idx), 3))
    for r, i in enumerate(test_idx):
        s = S[i].copy(); s[~train_mask] = -1
        if exclude_group: s[G == G[i]] = -1
        top = np.argpartition(-s, k)[:k]
        acc = collections.defaultdict(float)
        for j in top:
            g = RG[j]
            if g in big and s[j] > 0.3: acc[g] += s[j] ** 2
        if acc:
            g = max(acc, key=acc.get); c, y, m = rg_cons[g]
            o[r] = [(2 * (y ^ neg[i]) - 1) * c, acc[g], m]
    return o

# stacker trained on out-of-fold features inside the pool (grouped CV, so it learns how much to trust each signal)
Fp = np.zeros((len(pool), len(FN)))
for tr, te in GroupKFold(5).split(pool, groups=G[pool]): Fp[te] = F(pool[tr], pool[te])
# test items see the whole pool (older products) — no group exclusion: an older card's identical question is legitimate evidence
Ft = F(pool, test, exclude_group=False)
from sklearn.ensemble import HistGradientBoostingClassifier
MODEL = os.environ.get('MODEL', 'hgb')
M = (HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, max_leaf_nodes=15, l2_regularization=1.0, random_state=0) if MODEL == 'hgb'
     else LogisticRegression(C=1.0, max_iter=2000)).fit(Fp, Y[pool])
pt = M.predict_proba(Ft)[:, 1]; yt = Y[test]; pred = (pt > 0.5).astype(int); conf = np.maximum(pt, 1 - pt)
print('test accuracy (answer everything)', (pred == yt).mean().round(3), '| kNN vote only', ((Ft[:, 0] > 0).astype(int) == yt).mean().round(3))
order = np.argsort(-conf); curve = []
for c in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
    k = int(round(c * len(test))); sel = order[:k]
    curve.append({'coverage': c, 'n': k, 'acc': round(float((pred[sel] == yt[sel]).mean()), 4), 'min_conf': round(float(conf[sel].min()), 3)})
def best_cov(target):
    ok = [(k, conf[order[k - 1]]) for k in range(20, len(test) + 1) if (pred[order[:k]] == yt[order[:k]]).mean() >= target]
    return (max(ok)[0] / len(test), float(max(ok)[1])) if ok else (0, 1)
res = {'n_test': int(len(test)), 'n_pool': int(len(pool)), 'acc_all': round(float((pred == yt).mean()), 4), 'curve': curve,
       'cov_at_95': best_cov(0.95), 'cov_at_97': best_cov(0.97), 'model': MODEL, 'weights': dict(zip(FN, M.coef_[0].round(3).tolist())) if hasattr(M, 'coef_') else {}}
for c in curve: print(f"  답하는 비율 {c['coverage']:.0%} ({c['n']}문항): 정확도 {c['acc']:.1%}  최소 확신 {c['min_conf']}")
print('정확도 95% 유지 최대 커버', res['cov_at_95'], ' 97%', res['cov_at_97'])
print('가중치', res['weights'])
import pickle; pickle.dump({'Fp': Fp, 'Ft': Ft, 'Y': Y, 'pool': pool, 'test': test, 'G': G, 'FN': FN}, open('net/engine_feats.pkl', 'wb'))
os.makedirs('paper/results', exist_ok=True)
json.dump(res, open(f'paper/results/engine_sel_{MODEL}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
