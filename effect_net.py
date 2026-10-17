"""Card-effect networks.
 A. element network: timing / action / keyword / kind nodes, linked when they co-occur in one effect unit
    more often than chance (PMI > 0, count >= 5).
 B. effect-pattern network: patterns with >= 3 effects, linked by (1) shared elements (weighted Jaccard, top-k),
    (2) Q&A issues they share (tight Q&A groups spanning both), (3) appearing together on the same card.
Communities (Louvain), centrality, Gephi export (GEXF + CSV) and a JSON bundle for the viewer page."""
import json, math, collections, os, re, numpy as np, networkx as nx
U = json.load(open('units3.json', encoding='utf-8'))
PATS = {p['id']: p for p in json.load(open('patterns.json', encoding='utf-8'))}
QI = json.load(open('qa_items.json', encoding='utf-8'))
CARDS = {c['no']: c for c in json.load(open('cards.json', encoding='utf-8'))}
R = {r['n']: r['t'] for r in json.load(open('rules2.json', encoding='utf-8'))['rules'] if r['l'] >= 0}
qlab = np.load('qa_labels_0.25.npy')   # tight Q&A issue groups (agglomerative, distance 0.25)
cn = lambda no: re.sub(r'^\S+\s*', '', CARDS[no]['name']) if no in CARDS else no

# ---------------- A. element network ----------------
def elems(u):
    e = [('타이밍', t) for t in u['timing']] + [('키워드', k) for k in u['keywords']] + [('행동', a) for a in u['acts'] if a != '기타(행동 미분류)']
    if u['kind'] != '타이밍 효과': e.append(('종류', u['kind']))
    if u['where'] in ('진화원 효과', '시큐리티 효과'): e.append(('위치', u['where']))
    return sorted(set(e))
for u in U:
    u.setdefault('acts', u.get('types', []))
E = [elems(u) for u in U]
N = len(U)
cnt = collections.Counter(x for e in E for x in e)
pair = collections.Counter((a, b) for e in E for i, a in enumerate(e) for b in e[i + 1:])
GA = nx.Graph()
for x, c in cnt.items():
    if c >= 5: GA.add_node(x, kind=x[0], name=x[1], count=c)
for (a, b), c in pair.items():
    if c < 5 or a not in GA or b not in GA: continue
    pmi = math.log(c * N / (cnt[a] * cnt[b]))
    if pmi > 0: GA.add_edge(a, b, weight=c, pmi=round(pmi, 2))
GA.remove_nodes_from([x for x in list(GA) if GA.degree(x) == 0])
commA = nx.community.louvain_communities(GA, weight='weight', resolution=1.0, seed=3)
for k, c in enumerate(sorted(commA, key=lambda c: -sum(GA.nodes[x]['count'] for x in c))):
    for x in c: GA.nodes[x]['comm'] = k
btwA = nx.betweenness_centrality(GA, weight=None)
wdeg = dict(GA.degree(weight='weight'))
print('A 요소 네트워크: 노드', GA.number_of_nodes(), '링크', GA.number_of_edges(), '커뮤니티', len(commA))
for k, c in enumerate(sorted(commA, key=lambda c: -sum(GA.nodes[x]['count'] for x in c))[:8]):
    top = sorted(c, key=lambda x: -GA.nodes[x]['count'])[:7]
    print(f'  계열 {k}: ' + ', '.join(f'{x[1]}' for x in top))
print('  매개 중심성 상위:', ', '.join(f'{x[1]}({v:.2f})' for x, v in sorted(btwA.items(), key=lambda kv: -kv[1])[:8]))

# ---------------- B. effect-pattern network ----------------
by_pat = collections.defaultdict(list)
for i, u in enumerate(U): by_pat[u['pattern']].append(i)
keep = [p for p, idx in by_pat.items() if len(idx) >= 3]
pe = {p: collections.Counter(x for i in by_pat[p] for x in E[i]) for p in keep}
for p in keep:  # element profile: share of the pattern's effects having each element
    m = len(by_pat[p]); pe[p] = {x: c / m for x, c in pe[p].items() if c / m >= 0.3}
GB = nx.Graph()
for p in keep:
    idx = by_pat[p]; P = PATS[p]
    qa_n = sum(len(U[i].get('qa', [])) for i in idx)
    GB.add_node(p, size=len(idx), cards=len({U[i]['card'] for i in idx}), label=P['example'][:80], types=' / '.join(P['types'][:3]),
                sub=P.get('sub', ''), qa=qa_n)
# (1) shared elements: weighted Jaccard, keep each pattern's 4 nearest
keys = sorted({x for p in keep for x in pe[p]}); kidx = {x: i for i, x in enumerate(keys)}
M = np.zeros((len(keep), len(keys)), np.float32)
for r, p in enumerate(keep):
    for x, v in pe[p].items(): M[r, kidx[x]] = v
mins = None
for r in range(len(keep)):
    num = np.minimum(M[r], M).sum(1); den = np.maximum(M[r], M).sum(1) + 1e-9; jw = num / den; jw[r] = 0
    for c in np.argsort(-jw)[:4]:
        if jw[c] >= 0.5:
            a, b = keep[r], keep[c]
            d = GB.get_edge_data(a, b, {'w_elem': 0, 'w_qa': 0, 'w_card': 0})
            d['w_elem'] = max(d['w_elem'], float(round(jw[c], 3))); GB.add_edge(a, b, **d)
# (2) shared Q&A issues: a tight Q&A group whose questions are about effects of both patterns
qa_pat = {}
for k, q in enumerate(QI):
    if q['unit'] is not None: qa_pat[k] = U[q['unit']]['pattern']
grp = collections.defaultdict(set)
for k, p in qa_pat.items():
    if p in GB: grp[int(qlab[k])].add(p)
for g, ps in grp.items():
    ps = sorted(ps)
    if len(ps) < 2 or len(ps) > 8: continue
    for i, a in enumerate(ps):
        for b in ps[i + 1:]:
            d = GB.get_edge_data(a, b, {'w_elem': 0, 'w_qa': 0, 'w_card': 0}); d['w_qa'] += 1; GB.add_edge(a, b, **d)
# (3) printed together on the same card
card_pats = collections.defaultdict(set)
for u in U:
    if u['pattern'] in GB: card_pats[u['card']].add(u['pattern'])
cc = collections.Counter()
for ps in card_pats.values():
    ps = sorted(ps)
    for i, a in enumerate(ps):
        for b in ps[i + 1:]: cc[(a, b)] += 1
for (a, b), c in cc.items():
    if c >= 3:
        d = GB.get_edge_data(a, b, {'w_elem': 0, 'w_qa': 0, 'w_card': 0}); d['w_card'] = c; GB.add_edge(a, b, **d)
for a, b, d in GB.edges(data=True):
    d['weight'] = round(d['w_elem'] + 0.5 * d['w_qa'] + 0.15 * min(d['w_card'], 10), 3)
GB.remove_nodes_from([x for x in list(GB) if GB.degree(x) == 0])
commB = nx.community.louvain_communities(GB, weight='weight', resolution=1.0, seed=3)
commB = sorted(commB, key=lambda c: -sum(GB.nodes[x]['size'] for x in c))
for k, c in enumerate(commB):
    for x in c: GB.nodes[x]['comm'] = k
prB = nx.pagerank(GB, weight='weight')
for x in GB: GB.nodes[x]['pagerank'] = round(prB[x] * 1000, 3)
et = collections.Counter(('elem' if d['w_elem'] else '') + ('+qa' if d['w_qa'] else '') + ('+card' if d['w_card'] else '') for _, _, d in GB.edges(data=True))
print('B 패턴 네트워크: 노드', GB.number_of_nodes(), '링크', GB.number_of_edges(), '커뮤니티', len(commB), '링크 종류', dict(et))

# community names: most common elements among their patterns
def comm_name(c):
    z = collections.Counter()
    for p in c:
        for x, v in pe[p].items(): z[x] += v * GB.nodes[p]['size']
    return ' · '.join(x[1] for x, _ in z.most_common(3))
names = [comm_name(c) for c in commB]
for k in range(min(10, len(commB))): print(f'  계열 {k} ({len(commB[k])}패턴): {names[k]}')

# ---------------- exports ----------------
os.makedirs('net', exist_ok=True)
GA2 = nx.Graph()
for x, d in GA.nodes(data=True): GA2.add_node(f'{x[0]}:{x[1]}', **d)
for a, b, d in GA.edges(data=True): GA2.add_edge(f'{a[0]}:{a[1]}', f'{b[0]}:{b[1]}', **d)
nx.write_gexf(GA2, 'net/effect_elements.gexf')
GB2 = nx.Graph()
for x, d in GB.nodes(data=True): GB2.add_node(f'P{x}', **d, community_name=names[d['comm']])
for a, b, d in GB.edges(data=True): GB2.add_edge(f'P{a}', f'P{b}', **d)
nx.write_gexf(GB2, 'net/effect_patterns.gexf')
import csv
with open('net/patterns_nodes.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['Id', 'Label', '효과 유형', '타이밍', '효과 수', '카드 수', 'Q&A 수', '계열', '계열 이름', 'PageRank'])
    for x, d in GB.nodes(data=True): w.writerow([f'P{x}', d['label'], d['types'], d['sub'], d['size'], d['cards'], d['qa'], d['comm'], names[d['comm']], d['pagerank']])
with open('net/patterns_edges.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['Source', 'Target', 'Weight', '요소 유사도', '공유 Q&A 쟁점', '같은 카드 수록'])
    for a, b, d in GB.edges(data=True): w.writerow([f'P{a}', f'P{b}', d['weight'], d['w_elem'], d['w_qa'], d['w_card']])

# viewer bundle
cards_of = {p: sorted({U[i]['card'] for i in by_pat[p]}) for p in GB}
qa_of = {}
for p in GB:
    ids = [x for i in by_pat[p] for x in U[i].get('qa', [])][:6]
    qa_of[p] = [[q['card'], re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', q['q']).strip()[:140], re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', q['a']).strip()[:120]] for q in (next(z for z in QI if z['id'] == x) for x in ids)]
rules_of = {p: collections.Counter(n_ for i in by_pat[p] for n_ in U[i]['rules']).most_common(5) for p in GB}
bundle = {
  'A': {'nodes': [{'id': f'{x[0]}:{x[1]}', 'kind': x[0], 'name': x[1], 'count': d['count'], 'comm': d['comm'], 'btw': round(btwA[x], 4)} for x, d in GA.nodes(data=True)],
        'links': [{'s': f'{a[0]}:{a[1]}', 't': f'{b[0]}:{b[1]}', 'w': d['weight'], 'pmi': d['pmi']} for a, b, d in GA.edges(data=True)]},
  'B': {'nodes': [{'id': f'P{x}', 'p': x, 'size': d['size'], 'cards': d['cards'], 'qa': d['qa'], 'label': d['label'], 'types': d['types'], 'sub': d['sub'], 'comm': d['comm'], 'pr': d['pagerank'],
                   'cardList': [[c, cn(c)] for c in cards_of[x][:40]], 'qaList': qa_of[x], 'rules': [[n_, R.get(n_, '')[:60]] for n_, _ in rules_of[x]]} for x, d in GB.nodes(data=True)],
        'links': [{'s': f'P{a}', 't': f'P{b}', 'w': d['weight'], 'e': d['w_elem'], 'q': d['w_qa'], 'c': d['w_card']} for a, b, d in GB.edges(data=True)],
        'comms': names},
}
json.dump(bundle, open('net/bundle.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('bundle KB', os.path.getsize('net/bundle.json') // 1024)
