"""SNA with each card effect as a node (card info such as evolution conditions excluded — not effects per 2-3).
Links: (s) rulebook-structure similarity kNN, (t) same trigger condition, (q) discussed in the same Q&A issue,
(c) on the same card, (m) effect text names another card (「쿠레미 쿄코」 …)."""
import json, re, collections, math, numpy as np, networkx as nx
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
S = json.load(open('struct2.json', encoding='utf-8'))
U = json.load(open('units3.json', encoding='utf-8'))
QI = json.load(open('qa_items.json', encoding='utf-8'))
CARDS = {c['no']: c for c in json.load(open('cards.json', encoding='utf-8'))}
qlab = np.load('qa_labels_0.25.npy')
cn = lambda no: re.sub(r'^\S+\s*', '', CARDS[no]['name']) if no in CARDS else no
nodes = [s for s in S if s['분류'] != '카드 정보(효과 아님)']
idx = {s['i']: k for k, s in enumerate(nodes)}; N = len(nodes)

def toks(s):
    t = ['C_' + s['분류'], 'O_' + s['출처']] + ['T_' + x for x in s.get('타이밍', [])] + ['I_' + x for x in s.get('아이콘', [])]
    if s.get('유발 키'): t += ['G_' + s['유발 키']] * 2 + ['E_' + s['유발 키'].split(' · ')[-1]]
    if s.get('처리 조건'): t.append('COND')
    for c in s.get('임의 처리 조건', []): t += ['COST'] + ['CA_' + a for a in c['acts']]
    for k, p in enumerate(s.get('처리', [])):
        t += ['A_' + a for a in p['acts']] + (['A1_' + a for a in p['acts']] if k == 0 else [])
        t += ['SC_' + p['scope']] if p['scope'] else []; t += ['OPT'] if p['임의'] else ['FORCE']
        t += ['DUR_' + p['dur']] if p['dur'] else []
    if s['분류'] == '키워드 효과': t += ['K_' + k for k in s.get('세부', '').split(' / ')]
    return ' '.join(x.replace(' ', '_') for x in t)
X1 = TfidfVectorizer(token_pattern=r'\S+', lowercase=False, sublinear_tf=True).fit_transform([toks(s) for s in nodes])
X2 = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 3), min_df=3, sublinear_tf=True).fit_transform([U[s['i']]['tpl'] for s in nodes])
X = normalize(hstack([X1, X2 * 0.5]).tocsr())

G = nx.Graph()
for k, s in enumerate(nodes): G.add_node(k)
def link(a, b, typ, w):
    """one link per pair; each reason keeps its own score (the strongest one if repeated)"""
    if a == b: return
    if not G.has_edge(a, b): G.add_edge(a, b, comp={})
    c = G[a][b]['comp']; c[typ] = max(c.get(typ, 0), w)
# (s) structure similarity: 4 nearest neighbours, cosine >= 0.55
K = 8
for st in range(0, N, 1500):
    sims = (X[st:st + 1500] @ X.T).toarray()
    for r in range(sims.shape[0]):
        a = st + r; sims[r, a] = -1
        for b in np.argpartition(-sims[r], K)[:K]:
            if sims[r, b] >= 0.35: link(a, int(b), 's', 0.2 + 0.7 * (float(sims[r, b]) - 0.35) / 0.65)   # spread 0.35..1 -> 0.2..0.9
# (t) same trigger condition: chain each node to its 3 most similar effects with the same trigger
bytrig = collections.defaultdict(list)
for k, s in enumerate(nodes):
    if s.get('유발 키'): bytrig[s['유발 키']].append(k)
for ks in bytrig.values():
    if len(ks) < 2: continue
    sub = (X[ks] @ X[ks].T).toarray(); np.fill_diagonal(sub, -1)
    for r, a in enumerate(ks):
        for c in np.argsort(-sub[r])[:5]: link(a, ks[c], 't', 0.5 + 0.5 * max(0.0, float(sub[r, c])))
# (q) the same tight Q&A issue discusses both effects
iss = collections.defaultdict(set)
for k, q in enumerate(QI):
    if q['unit'] is not None and q['unit'] in idx: iss[int(qlab[k])].add(idx[q['unit']])
for ks in iss.values():
    ks = sorted(ks)
    if 2 <= len(ks) <= 20:
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)): link(ks[i], ks[j], 'q', 0.9 if len(ks) <= 8 else 0.7)
# (c) effects printed on the same card
bycard = collections.defaultdict(list)
for k, s in enumerate(nodes): bycard[s['card']].append(k)
for ks in bycard.values():
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)): link(ks[i], ks[j], 'c', 0.35)
# (m) the effect names another card in 「…」 -> effects of cards with that exact name
byname = collections.defaultdict(list)
for k, s in enumerate(nodes): byname[cn(s['card'])].append(k)
for k, s in enumerate(nodes):
    for nm in set(re.findall(r'「([^「」]{2,20})」', s['text'])):
        tgt = [b for b in byname.get(nm, []) if nodes[b]['card'] != s['card']]
        for b in tgt[:10]: link(k, b, 'm', 0.45)
# strength 0-100: independent reasons combine like probabilities (1 - prod(1 - score)), so several weak reasons add up
for a, b, d in G.edges(data=True):
    c = d['comp']; d['types'] = ''.join(sorted(c)); p_ = 1.0
    for v in c.values(): p_ *= (1 - min(0.95, v))
    d['strength'] = round(100 * (1 - p_)); d['weight'] = d['strength'] / 100
st = np.array([d['strength'] for _, _, d in G.edges(data=True)])
print('노드', G.number_of_nodes(), '링크', G.number_of_edges(), '링크 종류', collections.Counter(t for _, _, d in G.edges(data=True) for t in d['types']))
print('강도 분포: 25/50/75/90%', np.percentile(st, [25, 50, 75, 90]).round(), ' 강도≥70', int((st >= 70).sum()), ' ≥50', int((st >= 50).sum()))

comms = sorted(nx.community.louvain_communities(G, weight='weight', resolution=1.0, seed=5), key=len, reverse=True)
comm = np.zeros(N, int)
for c_, mem in enumerate(comms):
    for k in mem: comm[k] = c_
pr = nx.pagerank(G, weight='weight')
deg = dict(G.degree())
def cname_of(mem):
    z = collections.Counter()
    for k in mem:
        s = nodes[k]; z[s['분류']] += 1
        if s.get('유발 키'): z['유발: ' + s['유발 키']] += 1
        for t_ in s.get('타이밍', []): z['【' + t_ + '】'] += 1
        for p in s.get('처리', [])[:1]:
            for a in p['acts'][:1]: z[a] += 1
    return ' · '.join(k for k, _ in z.most_common(3))
names = [cname_of(m) for m in comms]
print('커뮤니티', len(comms), '상위:')
for c_ in range(10): print(f'  {c_ + 1}. {len(comms[c_])}효과  {names[c_]}')
# layout: spring on the weighted graph, seeded by community so families sit together
rng = np.random.default_rng(3); ang = {c_: 2 * math.pi * c_ / max(1, min(len(comms), 40)) for c_ in range(len(comms))}
init = {k: (math.cos(ang[comm[k] % 40]) * (1 + rng.random() * .3), math.sin(ang[comm[k] % 40]) * (1 + rng.random() * .3)) for k in range(N)}
pos = nx.spring_layout(G, pos=init, weight='weight', iterations=60, seed=3, k=0.6 / math.sqrt(N))
qa_by_node = collections.defaultdict(list)
for k, q in enumerate(QI):
    if q['unit'] is not None and q['unit'] in idx: qa_by_node[idx[q['unit']]].append(k)
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
out = {
  'nodes': [{'k': k, 'card': s['card'], 'name': cn(s['card']), 'cls': s['분류'], 'src': s['출처'], 'tm': s.get('타이밍', []), 'trig': s.get('유발 키', ''),
             'grp': s['group'], 'text': s['text'], 'x': round(float(pos[k][0]), 4), 'y': round(float(pos[k][1]), 4), 'c': int(comm[k]),
             'pr': round(pr[k] * N, 3), 'deg': deg[k], 'qa': [[cq(QI[j]['q'])[:160], cq(QI[j]['a'])[:120]] for j in qa_by_node[k][:4]], 'nqa': len(qa_by_node[k])}
            for k, s in enumerate(nodes)],
  'links': [[a, b, d['types'], d['strength'], ','.join(f'{k}{round(v * 100)}' for k, v in sorted(d['comp'].items()))] for a, b, d in G.edges(data=True)],
  'comms': names, 'csize': [len(m) for m in comms],
}
json.dump(out, open('net/effect_sna.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
import os; print('json KB', os.path.getsize('net/effect_sna.json') // 1024)
g2 = nx.Graph()
for k, s in enumerate(nodes): g2.add_node(k, label=f"{s['card']} {cn(s['card'])}", cls=s['분류'], group=s['group'], trigger=s.get('유발 키', ''), community=int(comm[k]), pagerank=float(pr[k] * N))
for a, b, d in G.edges(data=True): g2.add_edge(a, b, types=d['types'], weight=d['weight'], strength=d['strength'])
nx.write_gexf(g2, 'net/effects_as_nodes.gexf')
