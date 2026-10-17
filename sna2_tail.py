# ---------------- two-level clustering ----------------
fine = sorted(nx.community.louvain_communities(G, weight='weight', resolution=1.4, seed=5), key=len, reverse=True)
comm = np.zeros(N, int)
for c_, mem in enumerate(fine):
    for k in mem: comm[k] = c_
F = len(fine)
CG = nx.Graph(); CG.add_nodes_from(range(F))
for a, b, d in G.edges(data=True):
    ca, cb = comm[a], comm[b]
    if ca == cb: continue
    w = CG[ca][cb]['w'] + d['weight'] if CG.has_edge(ca, cb) else d['weight']
    CG.add_edge(ca, cb, w=w)
for a, b, d in CG.edges(data=True): d['weight'] = d['w'] / math.sqrt(len(fine[a]) * len(fine[b]))   # normalise by cluster sizes
coarse = sorted(nx.community.louvain_communities(CG, weight='weight', resolution=1.0, seed=5), key=lambda c: -sum(len(fine[x]) for x in c))
ccomm = np.zeros(F, int)
for c_, mem in enumerate(coarse):
    for f in mem: ccomm[f] = c_
pr = nx.pagerank(G, weight='weight'); deg = dict(G.degree())
def describe(members, n_parts=3):
    z = collections.Counter()
    for k in members:
        s = nodes[k]; z[s['분류']] += 1
        if s.get('유발 키'): z['유발: ' + s['유발 키']] += 1.2
        for t_ in s.get('타이밍', []): z['【' + t_ + '】'] += 1
        for p in s.get('처리', [])[:2]:
            for a in p['acts'][:1]: z[a + ((' · ' + p['target']) if p.get('target') else '')] += 1.1
        if s['분류'] == '키워드 효과': z['《' + s.get('세부', '') + '》'] += 1.5
    return ' · '.join(k for k, _ in z.most_common(n_parts))
fname = [describe(m) for m in fine]
cname = [describe([k for f in mem for k in fine[f]], 2) for mem in coarse]
print('소분류(클러스터)', F, ' 대분류', len(coarse))
for c_ in range(min(12, len(coarse))): print(f'  대{c_ + 1}. {sum(len(fine[f]) for f in coarse[c_])}효과 · 소분류 {len(coarse[c_])}개 · {cname[c_]}')

# ---------------- cluster-aware layout ----------------
# 1) cluster positions: spring on the cluster graph; 2) members: spring inside each cluster, scaled to a disc of radius ~ sqrt(size);
# 3) push overlapping discs apart so clusters read as separate bubbles
cpos = nx.spring_layout(CG, weight='weight', iterations=200, seed=7, k=1.6 / math.sqrt(F))
R = {c_: 0.012 * math.sqrt(len(fine[c_])) + 0.006 for c_ in range(F)}
P = {c_: np.array(cpos[c_], float) for c_ in range(F)}
for it in range(300):
    moved = 0
    for a in range(F):
        for b in range(a + 1, F):
            d = P[b] - P[a]; dist = float(np.hypot(*d)) or 1e-6; need = R[a] + R[b] + 0.01
            if dist < need:
                push = (need - dist) / 2 * d / dist; P[a] -= push; P[b] += push; moved += 1
    if not moved: break
pos = {}
for c_, mem in enumerate(fine):
    mem = list(mem)
    if len(mem) == 1: pos[mem[0]] = P[c_]; continue
    sub = G.subgraph(mem)
    lp = nx.spring_layout(sub, weight='weight', iterations=50, seed=3)
    arr = np.array([lp[k] for k in mem]); arr -= arr.mean(0); sc = np.abs(arr).max() or 1
    for k, xy in zip(mem, arr / sc * R[c_] * 0.95): pos[k] = P[c_] + xy
qa_by_node = collections.defaultdict(list)
for k, q in enumerate(QI):
    if q['unit'] is not None and q['unit'] in idx: qa_by_node[idx[q['unit']]].append(k)
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
clusters = []
for c_, mem in enumerate(fine):
    mem = list(mem); top = sorted(mem, key=lambda k: -pr[k])[:6]
    grp = collections.Counter(nodes[k]['group'] for k in mem).most_common(3)
    clusters.append({'id': c_, 'cc': int(ccomm[c_]), 'x': round(float(P[c_][0]), 4), 'y': round(float(P[c_][1]), 4), 'r': round(R[c_], 4), 'n': len(mem),
                     'name': fname[c_], 'top': top, 'groups': [[g, n] for g, n in grp], 'nqa': sum(len(qa_by_node[k]) for k in mem),
                     'cards': len({nodes[k]['card'] for k in mem})})
clinks = sorted(([int(a), int(b), round(d['w'] * 100)] for a, b, d in CG.edges(data=True)), key=lambda x: -x[2])[:600]
out = {
  'nodes': [{'k': k, 'card': s['card'], 'name': cn(s['card']), 'cls': s['분류'], 'src': s['출처'], 'tm': s.get('타이밍', []), 'trig': s.get('유발 키', ''),
             'grp': s['group'], 'text': s['text'], 'x': round(float(pos[k][0]), 5), 'y': round(float(pos[k][1]), 5), 'c': int(comm[k]), 'cc': int(ccomm[comm[k]]),
             'pr': round(pr[k] * N, 3), 'deg': deg[k], 'qa': [[cq(QI[j]['q'])[:160], cq(QI[j]['a'])[:120]] for j in qa_by_node[k][:4]], 'nqa': len(qa_by_node[k])}
            for k, s in enumerate(nodes)],
  'links': [[a, b, d['types'], d['strength'], ','.join(f'{k}{round(v * 100)}' for k, v in sorted(d['comp'].items()))] for a, b, d in G.edges(data=True)],
  'clusters': clusters, 'clinks': clinks, 'coarse': [{'id': c_, 'name': cname[c_], 'n': sum(len(fine[f]) for f in mem), 'fine': sorted(int(f) for f in mem)} for c_, mem in enumerate(coarse)],
}
json.dump(out, open('net/effect_sna.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
import os; print('json KB', os.path.getsize('net/effect_sna.json') // 1024)
g2 = nx.Graph()
for k, s in enumerate(nodes): g2.add_node(k, label=f"{s['card']} {cn(s['card'])}", cls=s['분류'], group=s['group'], trigger=s.get('유발 키', ''), cluster=int(comm[k]), coarse=int(ccomm[comm[k]]), pagerank=float(pr[k] * N))
for a, b, d in G.edges(data=True): g2.add_edge(a, b, types=d['types'], weight=d['weight'], strength=d['strength'])
nx.write_gexf(g2, 'net/effects_as_nodes.gexf')
# check the user's example pair
ka = [k for k, s in enumerate(nodes) if s['i'] == 8279][0]; kb = [k for k, s in enumerate(nodes) if s['i'] == 6564][0]
print('EX10-010 ↔ BT19-063 링크:', G.get_edge_data(ka, kb), ' 클러스터', comm[ka], comm[kb])
