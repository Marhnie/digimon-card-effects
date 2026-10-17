"""SNA approach.
(1) Q&A similarity network + Louvain communities = issue groups (compared with the agglomerative groups).
(2) Heterogeneous network (Q&A, card, effect pattern, situation slot, intent, rule clause) + personalized PageRank
    from a new question's card/effect/situation/text neighbours = evidence ranking; scored on held-out yes/no Q&A."""
import json, random, collections, numpy as np, networkx as nx
exec(open('qa_group.py', encoding='utf-8').read().split("if __name__ == '__main__':")[0])  # rows, S, Y, NEG, cards, evaluate()
GEN = json.load(open('general_by_rule.json', encoding='utf-8'))
id2i = {r['id']: i for i, r in enumerate(rows)}
qa_rule = collections.defaultdict(set)
for n_, ids in GEN.items():
    for x in ids:
        if x in id2i: qa_rule[id2i[x]].add(n_)
for i, r in enumerate(rows):
    q = QI[i]
    if q['unit'] is not None:
        for n_ in U[q['unit']]['rules'][:6]: qa_rule[i].add(n_)

# ---------- (1) Q&A network + Louvain ----------
K = 10
Gq = nx.Graph(); Gq.add_nodes_from(range(n))
pats = np.array([r['pat'] for r in rows])
for i in range(n):
    s = S[i].copy(); s[i] = -1
    for j in np.argpartition(-s, K)[:K]:
        w = float(s[j])
        if w < 0.45: continue
        if pats[i] >= 0 and pats[i] == pats[j]: w += 0.15
        if cards[i] == cards[j]: w += 0.1
        if Gq.has_edge(i, j): Gq[i][j]['weight'] = max(Gq[i][j]['weight'], w)
        else: Gq.add_edge(i, j, weight=w)
print('Q&A 네트워크: 노드', Gq.number_of_nodes(), '엣지', Gq.number_of_edges())
for res in (1.0, 3.0, 8.0, 20.0):
    comms = nx.community.louvain_communities(Gq, weight='weight', resolution=res, seed=7)
    lab = np.zeros(n, int)
    for k, c in enumerate(comms):
        for i in c: lab[i] = k
    g, single, avg, pur, cov, acc = evaluate(lab)
    print(f'Louvain 해상도 {res:>4}: 그룹 {g:5}  단독 {single:5}  여럿 그룹 평균 {avg:4.1f}개  답 일관성 {pur:.1%}  새 질문 커버 {cov:.1%}  정확도 {acc:.1%}')
    np.save(f'qa_louvain_{res}.npy', lab)

# ---------- (2) heterogeneous network + personalized PageRank ----------
H = nx.Graph()
for i, r in enumerate(rows):
    qn = ('q', i); H.add_node(qn)
    if r['card']: H.add_edge(qn, ('c', r['card']), weight=1.0)
    if r['pat'] >= 0: H.add_edge(qn, ('p', r['pat']), weight=1.0)
    for s_ in r['sl']: H.add_edge(qn, ('s', s_), weight=0.3)
    H.add_edge(qn, ('i', r['it']), weight=0.3)
    for n_ in qa_rule[i]: H.add_edge(qn, ('r', n_), weight=0.6)
for i, j, d in Gq.edges(data=True):
    H.add_edge(('q', i), ('q', j), weight=2.0 * d['weight'])
for u in U:  # cards connect to the effect patterns they contain
    H.add_edge(('c', u['card']), ('p', u['pattern']), weight=0.5)
print('이종 네트워크: 노드', H.number_of_nodes(), '엣지', H.number_of_edges())

L = [i for i in range(n) if Y[i] >= 0]
random.seed(9); test = random.sample(L, 300)
def leak_set(t):
    return {j for j in np.where((S[t] > 0.95) | ((S[t] > 0.55) & (cards == cards[t])))[0]} | {t}
res_sim = res_ppr = res_mix = 0
for t in test:
    lk = leak_set(t)
    s = S[t].copy(); s[list(lk)] = -1
    top = np.argsort(-s)[:5]
    w = s[top] ** 3; yy = Y[top] ^ NEG[top] ^ NEG[t]; ok_mask = Y[top] >= 0
    pred_sim = int((w * ok_mask * (yy == 1)).sum() >= (w * ok_mask * (yy == 0)).sum())
    # personalization: the new question's card, effect pattern, slots, intent, and its closest worded Q&A
    r = rows[t]; pers = collections.Counter()
    if r['card']: pers[('c', r['card'])] += 1.0
    if r['pat'] >= 0: pers[('p', r['pat'])] += 1.0
    for s_ in r['sl']: pers[('s', s_)] += 0.15
    pers[('i', r['it'])] += 0.2
    for j in np.argsort(-s)[:10]:
        if s[j] > 0.2: pers[('q', int(j))] += float(s[j]) * 2
    view = nx.restricted_view(H, [('q', j) for j in lk], [])
    pr = nx.pagerank(view, alpha=0.75, personalization={k: v for k, v in pers.items() if k in view}, weight='weight', max_iter=60, tol=1e-5)
    qs = sorted(((v, k[1]) for k, v in pr.items() if k[0] == 'q' and Y[k[1]] >= 0), reverse=True)[:7]
    yes = sum(v for v, j in qs if (Y[j] ^ NEG[j] ^ NEG[t]) == 1); no = sum(v for v, j in qs if (Y[j] ^ NEG[j] ^ NEG[t]) == 0)
    pred_ppr = int(yes >= no)
    # mixture: PageRank mass and text similarity together
    mix = collections.Counter()
    for v, j in qs: mix[j] += v / (qs[0][0] or 1)
    for j in top:
        if Y[j] >= 0: mix[int(j)] += float(s[j])
    yes = sum(v for j, v in mix.items() if (Y[j] ^ NEG[j] ^ NEG[t]) == 1); no = sum(v for j, v in mix.items() if (Y[j] ^ NEG[j] ^ NEG[t]) == 0)
    pred_mix = int(yes >= no)
    res_sim += pred_sim == Y[t]; res_ppr += pred_ppr == Y[t]; res_mix += pred_mix == Y[t]
print(f'\n새 질문 300개 네/아니요 정확도 — 비슷한 질문(지금): {res_sim/3:.1f}%  개인화 PageRank: {res_ppr/3:.1f}%  둘 결합: {res_mix/3:.1f}%')
