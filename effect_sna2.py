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

TRIG_TM = {'등장 시', '진화 시', '소멸 시', '어택 시', '링크 시', '시큐리티', '자신의 턴 개시 시', '상대의 턴 개시 시', '자신의 턴 종료 시',
           '상대의 턴 종료 시', '서로의 턴 종료 시', '자신의 메인 페이즈 개시 시', '상대의 메인 페이즈 개시 시', '어택 종료 시', '이동 시'}
def trig_keys(s):
    """trigger condition (15-5) and trigger-timing icon (15-16) on one axis: 【진화 시】 counts the same as 「~했을 때」"""
    ks = ['【' + x + '】' for x in s.get('타이밍', []) if x in TRIG_TM]   # any class: 【진화 시】【메인】 effects (기동형) also trigger on evolution
    return ks + ([s['유발 키']] if s.get('유발 키') else [])
def toks(s):
    t = ['C_' + s['분류'], 'O_' + s['출처']] + ['T_' + x for x in s.get('타이밍', [])] + ['I_' + x for x in s.get('아이콘', [])]
    for g in trig_keys(s): t += ['G_' + g] * 2 + ['E_' + g.split(' · ')[-1]]
    if s.get('처리 조건'): t.append('COND')
    for c in s.get('임의 처리 조건', []): t += ['COST'] + ['CA_' + a for a in c['acts']]
    for k, p in enumerate(s.get('처리', [])):
        t += ['A_' + a for a in p['acts']] + (['A1_' + a for a in p['acts']] if k == 0 else [])
        t += ['SC_' + p['scope']] if p['scope'] else []; t += ['OPT'] if p['임의'] else ['FORCE']
        t += ['DUR_' + p['dur']] if p['dur'] else []
        t += (['TG_' + p.get('target', '')] if p.get('target') else []) + (['SD_' + p.get('side', '')] if p.get('side') else []) + ['F_' + f for f in p.get('filters', [])]
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
# (s') identical wording: hundreds of copies of one text (《블로커》, 「【시큐리티】이 카드의 【메인】 효과를 발휘한다」 …) all tie at
#      cosine 1, so top-K alone splits them into disconnected cliques; chain every copy to the next two copies (ring) so they stay one block
def norm_text(x):
    x = re.sub(r'\([^()]*\)', '', x); x = x.replace('〔', '[').replace('〕', ']').replace('S 어택', '시큐리티 어택')
    return re.sub(r'[\s.・]', '', x)
same_text = collections.defaultdict(list)
for k, s in enumerate(nodes): same_text[(s['group'], norm_text(s['text']))].append(k)
n_dup = 0
for ks in same_text.values():
    if len(ks) < 3: continue
    n_dup += len(ks)
    for i in range(len(ks)):
        link(ks[i], ks[(i + 1) % len(ks)], 's', 0.9); link(ks[i], ks[(i + 2) % len(ks)], 's', 0.9)
print('같은 문구 묶음', sum(len(v) >= 3 for v in same_text.values()), '개 ·', n_dup, '효과')
# (p) same processing step — an effect links to others that perform the same action on the same kind of target with the same
#     kind of filter in ANY of their steps; within a step key every effect gets its 10 closest step texts (others on other cards)
step_rows = []
for k, s in enumerate(nodes):
    for p in s.get('처리', []):
        for a in p['acts']:
            if a in ('공개', '덱 위 확인') or not p.get('target'): continue
            step_rows.append((k, (a, p['target'], tuple(sorted(p.get('filters', [])))), p.get('side', ''), p['text']))
from sklearn.feature_extraction.text import TfidfVectorizer as _TV
SV = normalize(_TV(analyzer='char_wb', ngram_range=(2, 3), min_df=2, sublinear_tf=True).fit_transform([re.sub(r'\d+', 'N', r[3]) for r in step_rows]))
bykey = collections.defaultdict(list)
for j, r in enumerate(step_rows): bykey[r[1]].append(j)
for key, js in bykey.items():
    if len(js) < 2: continue
    sub = (SV[js] @ SV[js].T).toarray(); np.fill_diagonal(sub, -1)
    for a_, ja in enumerate(js):
        order = np.argsort(-sub[a_])
        got = 0
        for c_ in order:
            jb = js[c_]; ka, kb = step_rows[ja][0], step_rows[jb][0]
            if nodes[ka]['card'] == nodes[kb]['card']: continue
            same_side = step_rows[ja][2] == step_rows[jb][2] or '' in (step_rows[ja][2], step_rows[jb][2])
            link(ka, kb, 'p', 0.35 + 0.35 * max(0.0, float(sub[a_, c_])) + (0.1 if same_side else 0) + (0.05 if key[2] else 0))
            got += 1
            if got >= 10: break

# (t) same trigger condition: chain each node to its 3 most similar effects with the same trigger
bytrig = collections.defaultdict(list)
for k, s in enumerate(nodes):
    for g in trig_keys(s): bytrig[g].append(k)
print('유발 조건 축(아이콘 타이밍 포함):', len(bytrig), '종류,', sum(1 for s in nodes if trig_keys(s)), '효과', sorted(((k, len(v)) for k, v in bytrig.items()), key=lambda x: -x[1])[:6])
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
print('같은 처리 키', len(bykey), '처리 단계', len(step_rows)); print('노드', G.number_of_nodes(), '링크', G.number_of_edges(), '링크 종류', collections.Counter(t for _, _, d in G.edges(data=True) for t in d['types']))
print('강도 분포: 25/50/75/90%', np.percentile(st, [25, 50, 75, 90]).round(), ' 강도≥70', int((st >= 70).sum()), ' ≥50', int((st >= 50).sum()))

# ---------------- two-level clustering ----------------
import os, pickle
RES_F = float(os.environ.get('RES_F', '1.6')); RES_C = float(os.environ.get('RES_C', '0.4'))   # chosen by cluster_check.py (E15)
pickle.dump({'G': G, 'cls': [s['분류'] for s in nodes], 'grp': [s['group'] for s in nodes], 'card': [s['card'] for s in nodes]}, open('net/G.pkl', 'wb'))
if os.environ.get('ONLY_GRAPH'): raise SystemExit
fine = sorted(nx.community.louvain_communities(G, weight='weight', resolution=RES_F, seed=5), key=len, reverse=True)
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
# coarse level: Louvain on the effect graph itself at a low resolution (cluster-graph Louvain had Q below its null — see cluster_check.py),
# each fine cluster joins the coarse community holding most of its effects (nesting purity ~0.90 at RES_C 0.4)
_cl = np.zeros(N, int)
for c_, mem in enumerate(nx.community.louvain_communities(G, weight='weight', resolution=RES_C, seed=5)):
    for k in mem: _cl[k] = c_
_maj = [collections.Counter(_cl[k] for k in fine[f]).most_common(1)[0][0] for f in range(F)]
_grp = collections.defaultdict(set)
for f, m in enumerate(_maj): _grp[m].add(f)
coarse = sorted(_grp.values(), key=lambda c: -sum(len(fine[x]) for x in c))
print('대분류 포함 순도', round(sum(sum(_cl[k] == _maj[f] for k in fine[f]) for f in range(F)) / N, 3))
ccomm = np.zeros(F, int)
for c_, mem in enumerate(coarse):
    for f in mem: ccomm[f] = c_
pr = nx.pagerank(G, weight='weight'); deg = dict(G.degree())
def describe(members, n_parts=3):
    z = collections.Counter()
    for k in members:
        s = nodes[k]; z[s['분류']] += 1
        for g in trig_keys(s): z[g if g.startswith('【') else '유발: ' + g] += 1.2
        for t_ in s.get('타이밍', []):
            if t_ not in TRIG_TM: z['【' + t_ + '】'] += 1
        for p in s.get('처리', [])[:2]:
            for a in p['acts'][:1]: z[a + ((' · ' + p['target']) if p.get('target') else '')] += 1.1
        if s['분류'] == '키워드 효과': z['《' + s.get('세부', '') + '》'] += 1.5
    return ' · '.join(k for k, _ in z.most_common(n_parts))
fname = [describe(m) for m in fine]
cname = [describe([k for f in mem for k in fine[f]], 2) for mem in coarse]
# human names (cluster_names.json) replace the automatic ones when the cluster size still matches; auto name kept as 'auto'
fauto, cauto = list(fname), list(cname)
if os.path.exists('cluster_names.json'):
    HN = json.load(open('cluster_names.json', encoding='utf-8')); hit = [0, 0]
    for c_, mem in enumerate(fine):
        v = HN['fine'].get(str(c_ + 1))
        if v and v[1] == len(mem): fname[c_] = v[0]; hit[0] += 1
    for c_, mem in enumerate(coarse):
        v = HN['coarse'].get(str(c_ + 1))
        if v and v[1] == sum(len(fine[f]) for f in mem): cname[c_] = v[0]; hit[1] += 1
    print('사람 이름 적용: 세부', hit[0], '/', F, '· 대분류', hit[1], '/', len(coarse))
print('소분류(클러스터)', F, ' 대분류', len(coarse))
for c_ in range(min(12, len(coarse))): print(f'  대{c_ + 1}. {sum(len(fine[f]) for f in coarse[c_])}효과 · 소분류 {len(coarse[c_])}개 · {cname[c_]}')

# ---------------- cluster-aware layout (hierarchical) ----------------
# 1) coarse groups placed by spring on the coarse graph; 2) each group's fine clusters packed around its centre;
# 3) overlap removal with a pull back toward the group centre, so same-colour bubbles stay together;
# 4) members fill their disc (angle from a spring layout, radius by rank -> compact, no stray outliers)
R = {c_: 0.012 * math.sqrt(len(fine[c_])) + 0.006 for c_ in range(F)}
C2 = len(coarse); KG = nx.Graph(); KG.add_nodes_from(range(C2))
for a, b, d in CG.edges(data=True):
    ga, gb = ccomm[a], ccomm[b]
    if ga != gb: KG.add_edge(ga, gb, weight=(KG[ga][gb]['weight'] if KG.has_edge(ga, gb) else 0) + d['w'])
for a, b, d in KG.edges(data=True):
    d['weight'] /= math.sqrt(sum(len(fine[f]) for f in coarse[a]) * sum(len(fine[f]) for f in coarse[b]))
RG = {g: 1.25 * math.sqrt(sum(R[f] ** 2 for f in coarse[g])) + 0.01 for g in range(C2)}
gpos = nx.spring_layout(KG, weight='weight', iterations=300, seed=7)
GP = {g: np.array(gpos[g], float) for g in range(C2)}
def separate(pts, rad, gap, iters=400, anchor=None, pull=0.0):
    keys = list(pts)
    for _ in range(iters):
        moved = 0
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                d = pts[b] - pts[a]; dist = float(np.hypot(*d)) or 1e-6; need = rad[a] + rad[b] + gap
                if dist < need:
                    push = (need - dist) / 2 * d / dist; pts[a] -= push; pts[b] += push; moved += 1
        if anchor is not None:
            for k in keys: pts[k] += pull * (anchor[k] - pts[k])
        if not moved: break
scale = sum(RG.values()) / max(1e-6, np.mean([np.hypot(*GP[g]) for g in GP]) * C2) * 1.5
for g in GP: GP[g] *= scale
separate(GP, RG, 0.02)
P = {}
for g in range(C2):
    fs = sorted(coarse[g], key=lambda f: -len(fine[f]))
    if len(fs) == 1: P[fs[0]] = GP[g].copy(); continue
    sub = CG.subgraph(fs); lp = nx.spring_layout(sub, weight='weight', iterations=100, seed=7)
    arr = np.array([lp[f] for f in fs]); arr -= arr.mean(0); sc = np.abs(arr).max() or 1
    for f, xy in zip(fs, arr / sc * RG[g] * 0.6): P[f] = GP[g] + xy
anchor = {f: GP[ccomm[f]] for f in range(F)}
separate(P, R, 0.006, iters=600, anchor=anchor, pull=0.04)
separate(P, R, 0.006, iters=300)          # final pass without pull: no overlaps left
pos = {}
for c_, mem in enumerate(fine):
    mem = list(mem)
    if len(mem) == 1: pos[mem[0]] = P[c_]; continue
    lp = nx.spring_layout(G.subgraph(mem), weight='weight', iterations=50, seed=3)
    arr = np.array([lp[k] for k in mem]); arr -= arr.mean(0)
    ang = np.arctan2(arr[:, 1], arr[:, 0]); rr = np.hypot(arr[:, 0], arr[:, 1])
    rad = np.sqrt((np.argsort(np.argsort(rr)) + 0.5) / len(mem)) * R[c_] * 0.92
    for k, a_, r_ in zip(mem, ang, rad): pos[k] = P[c_] + np.array([math.cos(a_), math.sin(a_)]) * r_
qa_by_node = collections.defaultdict(list)
for k, q in enumerate(QI):
    if q['unit'] is not None and q['unit'] in idx: qa_by_node[idx[q['unit']]].append(k)
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
clusters = []
for c_, mem in enumerate(fine):
    mem = list(mem); top = sorted(mem, key=lambda k: -pr[k])[:6]
    grp = collections.Counter(nodes[k]['group'] for k in mem).most_common(3)
    clusters.append({'id': c_, 'cc': int(ccomm[c_]), 'x': round(float(P[c_][0]), 4), 'y': round(float(P[c_][1]), 4), 'r': round(R[c_], 4), 'n': len(mem),
                     'name': fname[c_], 'auto': fauto[c_], 'top': top, 'groups': [[g, n] for g, n in grp], 'nqa': sum(len(qa_by_node[k]) for k in mem),
                     'cards': len({nodes[k]['card'] for k in mem})})
clinks = sorted(([int(a), int(b), round(d['w'] * 100)] for a, b, d in CG.edges(data=True)), key=lambda x: -x[2])[:600]
out = {
  'nodes': [{'k': k, 'card': s['card'], 'name': cn(s['card']), 'cls': s['분류'], 'src': s['출처'], 'tm': s.get('타이밍', []), 'trig': ' / '.join(trig_keys(s)),
             'grp': s['group'], 'text': s['text'], 'x': round(float(pos[k][0]), 5), 'y': round(float(pos[k][1]), 5), 'c': int(comm[k]), 'cc': int(ccomm[comm[k]]),
             'pr': round(pr[k] * N, 3), 'deg': deg[k], 'qa': [[cq(QI[j]['q'])[:160], cq(QI[j]['a'])[:120]] for j in qa_by_node[k][:4]], 'nqa': len(qa_by_node[k])}
            for k, s in enumerate(nodes)],
  'links': [[a, b, d['types'], d['strength'], ','.join(f'{k}{round(v * 100)}' for k, v in sorted(d['comp'].items()))] for a, b, d in G.edges(data=True)],
  'clusters': clusters, 'clinks': clinks, 'coarse': [{'id': c_, 'name': cname[c_], 'auto': cauto[c_], 'n': sum(len(fine[f]) for f in mem), 'fine': sorted(int(f) for f in mem)} for c_, mem in enumerate(coarse)],
}
json.dump(out, open('net/effect_sna.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
import os; print('json KB', os.path.getsize('net/effect_sna.json') // 1024)
g2 = nx.Graph()
for k, s in enumerate(nodes): g2.add_node(k, label=f"{s['card']} {cn(s['card'])}", cls=s['분류'], group=s['group'], trigger=' / '.join(trig_keys(s)), cluster=int(comm[k]), coarse=int(ccomm[comm[k]]), pagerank=float(pr[k] * N))
for a, b, d in G.edges(data=True): g2.add_edge(a, b, types=d['types'], weight=d['weight'], strength=d['strength'])
nx.write_gexf(g2, 'net/effects_as_nodes.gexf')
# check the user's example pair
ka = [k for k, s in enumerate(nodes) if s['i'] == 8279][0]; kb = [k for k, s in enumerate(nodes) if s['i'] == 6564][0]
print('EX10-010 ↔ BT19-063 링크:', G.get_edge_data(ka, kb), ' 클러스터', comm[ka], comm[kb])
