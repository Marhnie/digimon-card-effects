"""Group effect units: level 1 = interpretable type (timing x main action / keyword / special kind),
level 2 = ML pattern clusters (TF-IDF over templated wording + element tags, agglomerative cosine)."""
import json, re, collections
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import normalize
from parse_fx import ACTIONS, TIMING_RUN

U = json.load(open('units.json', encoding='utf-8'))

def main_action(u):
    body = TIMING_RUN.sub('', u['ntext'], count=1) if u['timing'] else u['ntext']
    best = None
    for n, p in ACTIONS:
        if n in ('코스트 무료',):   # a manner, not the act itself
            continue
        m = p.search(body)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), n)
    return best[1] if best else ('키워드 부여' if u['keywords'] else '기타')

ACT_EXCL = {'코스트 무료'}  # a manner of playing, not a result
for u in U:
    u['main'] = main_action(u)
    acts = [a for a in u['actions'] if a not in ACT_EXCL] or [a for a in u['actions']]
    u['acts'] = acts
    u['sub'] = '【' + '+'.join(u['timing']) + '】' if u['timing'] else ''
    if u['kind'] in ('타이밍 효과', '유발 효과(타이밍 표시 없음)'):
        # Q1/Q2: action-centred types; an effect belongs to every action it performs
        u['types'] = acts or ['기타(행동 미분류)']
        u['type'] = u['main'] if u['main'] in u['types'] else u['types'][0]
    elif u['kind'] == '키워드 능력':
        u['types'] = ['키워드 · 《' + k + '》' for k in u['keywords']] or ['키워드 · ?']
        u['type'] = u['types'][0]
    else:
        u['types'] = [u['kind']]
        u['type'] = u['kind']
    if u.get('trigger'):
        u['types'] = u['types'] + ['유발 · ' + u['trigger']]

# ---- level 2: pattern clusters ----
docs = [u['tpl'] for u in U]
tags = [' '.join(['T_' + t.replace(' ', '_') for t in u['timing']] + ['K_' + k.replace(' ', '_') for k in u['keywords']] +
                 ['A_' + a.replace(' ', '_') for a in u['actions']] + ['W_' + u['where']] + ['M_' + u['kind'].replace(' ', '_')] +
                 (['G_' + u['trigger'].replace(' ', '_')] * 2 if u.get('trigger') else [])) for u in U]
X1 = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), min_df=2, sublinear_tf=True).fit_transform(docs)
X2 = TfidfVectorizer(token_pattern=r'\S+', lowercase=False).fit_transform(tags)
X = normalize(hstack([X1, X2 * 0.8]).tocsr())
# cluster per main kind so different kinds never merge; average-linkage cosine with a distance cap
labels = np.full(len(U), -1)
nxt = 0
by_kind = collections.defaultdict(list)
for i, u in enumerate(U):
    by_kind[u['kind'] if u['kind'] not in ('타이밍 효과', '유발 효과(타이밍 표시 없음)') else '타이밍:' + u['main']].append(i)
for k, idx in by_kind.items():
    if len(idx) == 1:
        labels[idx[0]] = nxt; nxt += 1; continue
    sub = X[idx].toarray()
    cl = AgglomerativeClustering(n_clusters=None, metric='cosine', linkage='average', distance_threshold=0.42).fit(sub)
    for i, l in zip(idx, cl.labels_):
        labels[i] = nxt + l
    nxt += cl.labels_.max() + 1

# Q6: one pattern = same wording family AND same set of results
split = {}
for u, l in zip(U, labels):
    key = (int(l), frozenset(u['acts']))
    if key not in split:
        split[key] = len(split)
    u['pattern'] = split[key]
# same trigger condition + same results = one pattern, even when the timing tag or a trait filter differs
# (e.g. EX8-005 고로몬 and BT10-072: '이 카드가 진화원에서 효과로 파기되었을 때, 메모리 +1'), if the wording is not far apart
par = {}
def fnd(x):
    while par.setdefault(x, x) != x: par[x] = par[par[x]]; x = par[x]
    return x
fam = collections.defaultdict(list)
for i, u in enumerate(U):
    if u.get('trigger') and u['acts']: fam[(u['trigger'], frozenset(u['acts']))].append(i)
merged = 0
for idx in fam.values():
    if len({U[i]['pattern'] for i in idx}) < 2: continue
    sub = X[idx]; sims = (sub @ sub.T).toarray()
    for a_ in range(len(idx)):
        for b_ in range(a_ + 1, len(idx)):
            pa, pb = fnd(U[idx[a_]]['pattern']), fnd(U[idx[b_]]['pattern'])
            if pa != pb and sims[a_, b_] >= 0.35: par[pa] = pb; merged += 1
for u in U: u['pattern'] = fnd(u['pattern'])
print('유발 조건·결과가 같은 패턴 병합', merged)
labels = np.array([u['pattern'] for u in U])

# name each pattern by its medoid (unit closest to the cluster centroid)
P = collections.defaultdict(list)
for i, u in enumerate(U):
    P[u['pattern']].append(i)
pats = []
for pid, idx in P.items():
    sub = X[idx]
    c = np.asarray(sub.mean(axis=0)).ravel()
    sims = sub @ c
    med = idx[int(np.argmax(sims))]
    cards = sorted({U[i]['card'] for i in idx})
    pats.append({'id': pid, 'size': len(idx), 'cards': cards, 'medoid': med, 'type': collections.Counter(U[i]['type'] for i in idx).most_common(1)[0][0],
                 'types': sorted({x for i in idx for x in U[i]['types']}), 'sub': collections.Counter(U[i]['sub'] for i in idx).most_common(1)[0][0],
                 'tpl': U[med]['tpl'], 'example': U[med]['text']})
pats.sort(key=lambda p: -p['size'])
rank = {p['id']: n + 1 for n, p in enumerate(pats)}
for u in U:
    u['pattern'] = rank[u['pattern']]
for p in pats:
    p['id'] = rank[p['id']]
json.dump(U, open('units2.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(pats, open('patterns.json', 'w', encoding='utf-8'), ensure_ascii=False)
sizes = [p['size'] for p in pats]
print('types', len({x for u in U for x in u['types']}), 'patterns', len(pats), 'singletons', sum(1 for s in sizes if s == 1), 'size>=5', sum(1 for s in sizes if s >= 5))
for p in pats[:25]:
    print(p['id'], p['size'], len(p['cards']), p['type'], '|', p['example'][:110])
