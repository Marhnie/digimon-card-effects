"""Claude-free yes/no ruling predictor.
Grouped 5-fold CV over every 네/아니요 card Q&A (near-duplicate questions share a group, so a
question never sees its own restatement), plus the fixed 100-item test from the Claude comparison."""
import json, re, collections, numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import normalize

QI = json.load(open('qa_items.json', encoding='utf-8'))
U = json.load(open('units3.json', encoding='utf-8'))
gold100 = json.load(open('eval/gold.json', encoding='utf-8'))
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
lab = lambda a: 1 if re.match(r'^\s*(네|예)[,，.\s]', a) else (0 if re.match(r'^\s*(아니요|아니오|아뇨)[,，.\s]', a) else None)
D = []
for q in QI:
    q['q'] = cq(q['q']); y = lab(cq(q['a']))
    if y is None: continue
    u = U[q['unit']] if q['unit'] is not None else None
    D.append({'id': q['id'], 'card': q['card'] or '', 'q': q['q'], 'y': y,
              'pat': u['pattern'] if u else -1, 'types': u['types'] if u else [], 'timing': u['timing'] if u else []})
n = len(D); Y = np.array([d['y'] for d in D])
print('items', n, 'yes rate', Y.mean().round(3))

def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    return re.sub(r'\d+', 'N', s)
raw = [d['q'] for d in D]; tq = [tpl(d['q']) for d in D]

# similarity space: char 2-4grams of the question (as written) + of its template
V1 = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit(raw)
V2 = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit(tq)
X = normalize(hstack([V1.transform(raw), V2.transform(tq)]).tocsr())
S = (X @ X.T).toarray(); np.fill_diagonal(S, 0)

# near-duplicate groups (union-find): very similar wording, or similar wording on the same card
par = list(range(n))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
cards = np.array([d['card'] for d in D])
import sys
DUP = float(sys.argv[1]) if len(sys.argv) > 1 else 0.80
ii, jj = np.where(np.triu(S, 1) > DUP)
for i, j in zip(ii, jj): par[f(i)] = f(j)
ii, jj = np.where(np.triu(S, 1) > 0.55)
for i, j in zip(ii, jj):
    if cards[i] == cards[j]: par[f(i)] = f(j)
G = np.array([f(i) for i in range(n)])
print('groups', len(set(G)))

pats = np.array([d['pat'] for d in D])
# negated questions (「~할 수 없습니까」, 「~하지 않습니까」) flip the meaning of a neighbour's answer
NEG = re.compile(r'(?:없|않|못|아닌|아니)[^「」]{0,6}[?？]?\s*$|(?:없|않|못)(?:습니까|나요|는지|을까요|게 되나요|게 됩니까)')
neg = np.array([1 if NEG.search(d['q']) else 0 for d in D])
import os
K = int(os.environ.get('K', 9)); PW = float(os.environ.get('PW', 3.0)); FLIP = os.environ.get('FLIP', '1') == '1'
type_sets = [set(d['types']) for d in D]

def knn_feats(test_idx, train_mask, k=None, p=None):
    k = k or K; p = p or PW
    """weighted vote of the most similar training questions, with structure boosts"""
    out = np.zeros((len(test_idx), 6))
    for r, i in enumerate(test_idx):
        s = S[i].copy(); s[~train_mask] = -1; s[G == G[i]] = -1
        top = np.argpartition(-s, k)[:k]; top = top[np.argsort(-s[top])]
        w = np.clip(s[top], 0, None) ** p
        boost = np.ones(k)
        for t, j in enumerate(top):
            if pats[i] >= 0 and pats[j] == pats[i]: boost[t] *= 1.8
            elif type_sets[i] & type_sets[j]: boost[t] *= 1.25
            if cards[j] == cards[i]: boost[t] *= 1.5
        w = w * boost
        yy = Y[top] ^ (neg[top] ^ neg[i]) if FLIP else Y[top]
        yes = (w * (yy == 1)).sum(); no = (w * (yy == 0)).sum()
        out[r] = [(yes - no) / (yes + no + 1e-9), s[top[0]], yy[0] * 2 - 1, (yy[:3] * 2 - 1).mean(), yes, no]
    return out

def prior_feats(test_idx, train_mask):
    """how often the answer is 네 for the same effect pattern / effect type in the training fold (smoothed)"""
    base = Y[train_mask].mean()
    pc = collections.defaultdict(lambda: [0, 0]); tc = collections.defaultdict(lambda: [0, 0])
    for j in np.where(train_mask)[0]:
        if pats[j] >= 0: pc[pats[j]][0] += Y[j]; pc[pats[j]][1] += 1
        for t in type_sets[j]: tc[t][0] += Y[j]; tc[t][1] += 1
    out = np.zeros((len(test_idx), 2))
    for r, i in enumerate(test_idx):
        a, b = pc[pats[i]] if pats[i] >= 0 else (0, 0); out[r, 0] = (a + 3 * base) / (b + 3) - base
        vals = [(tc[t][0] + 5 * base) / (tc[t][1] + 5) for t in type_sets[i]] or [base]; out[r, 1] = np.mean(vals) - base
    return out

# question-text classifier: word + char n-grams of the template (phrasing like 「~할 수 있습니까」, 「~도」, 「이미」…)
VW = TfidfVectorizer(analyzer='word', token_pattern=r'[^\s]+', ngram_range=(1, 2), min_df=2, sublinear_tf=True)
VC = TfidfVectorizer(analyzer='char', ngram_range=(1, 3), min_df=3, sublinear_tf=True)
def text_model(train_idx, test_idx):
    A = hstack([VW.fit_transform([tq[i] for i in train_idx]), VC.fit_transform([tq[i] for i in train_idx])]).tocsr()
    B = hstack([VW.transform([tq[i] for i in test_idx]), VC.transform([tq[i] for i in test_idx])]).tocsr()
    m = LogisticRegression(C=2.0, max_iter=2000).fit(A, Y[train_idx])
    return m.decision_function(B)

def features(train_idx, test_idx):
    mask = np.zeros(n, bool); mask[train_idx] = True
    return np.hstack([knn_feats(test_idx, mask), prior_feats(test_idx, mask), text_model(train_idx, test_idx)[:, None]])

def oof(idx_all, groups, folds=5):
    F = np.zeros((len(idx_all), 9))
    for tr, te in GroupKFold(folds).split(idx_all, groups=groups[idx_all]):
        F[te] = features(idx_all[tr], idx_all[te])
    return F

allidx = np.arange(n)
F = oof(allidx, G)
acc = lambda pred, y: (pred == y).mean()
print('\n== grouped 5-fold CV over', n, 'items ==')
print('always 네              ', acc(np.ones(n), Y).round(3))
print('kNN vote (improved)   ', acc((F[:, 0] > 0).astype(int), Y).round(3))
print('text classifier        ', acc((F[:, 8] > 0).astype(int), Y).round(3))
print('pattern/type prior    ', acc((F[:, 6] + F[:, 7] > 0).astype(int), Y).round(3))
# stacker trained on out-of-fold features, evaluated with a second grouped CV
st_pred = np.zeros(n)
for tr, te in GroupKFold(5).split(allidx, groups=G):
    m = LogisticRegression(C=1.0, max_iter=1000).fit(F[tr], Y[tr]); st_pred[te] = m.predict(F[te])
print('stacked (all signals) ', acc(st_pred, Y).round(3))

# the fixed 100 items: train on everything outside their groups
id2i = {d['id']: i for i, d in enumerate(D)}
test_i = np.array([id2i[g['qa_id']] for g in gold100.values()])
tg = set(G[test_i]); train_i = np.array([i for i in allidx if G[i] not in tg])
Ftr = oof(train_i, G)
Fte = features(train_i, test_i)
m = LogisticRegression(C=1.0, max_iter=1000).fit(Ftr, Y[train_i])
p100 = m.predict(Fte); pk = (Fte[:, 0] > 0).astype(int)
print('\n== fixed 100-item test (Claude comparison set) ==')
print('kNN vote (improved)   ', acc(pk, Y[test_i]))
print('stacked (all signals) ', acc(p100, Y[test_i]))
print('stacker weights', dict(zip(['knn','top1sim','top1y','top3y','yesw','now','pat','type','text'], m.coef_[0].round(2))))
# confidence: how accurate when the model is sure
pr = m.predict_proba(Fte)[:, 1]; sure = np.abs(pr - 0.5) > 0.3
print('100-item: confident subset', int(sure.sum()), 'acc', acc(p100[sure], Y[test_i][sure]).round(3), '| rest', acc(p100[~sure], Y[test_i][~sure]).round(3))
pall = np.zeros(n)
for tr, te in GroupKFold(5).split(allidx, groups=G):
    mm = LogisticRegression(C=1.0, max_iter=1000).fit(F[tr], Y[tr]); pall[te] = mm.predict_proba(F[te])[:, 1]
for th in (0.2, 0.3, 0.4):
    s = np.abs(pall - 0.5) > th
    print(f'CV: |p-0.5|>{th}: covers {s.mean():.0%}, acc {acc((pall[s] > 0.5).astype(int), Y[s]):.3f}')
