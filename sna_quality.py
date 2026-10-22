"""E42: cluster quality of an effect-network file, measured with criteria the clustering does not optimise.
  python sna_quality.py net/effect_sna.json [more files]
 - rg_pair: pairs of effects whose official Q&As fall in the same consistent reason group (answers explained the same way)
   -> share placed in the same fine cluster (higher = clusters follow rule issues)
 - modularity of the fine partition on that file's own graph (q links left out, as in sna_eval)
 - number of fine clusters, largest cluster share"""
import json, sys, collections, itertools, math, re
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
import networkx as nx
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']; U3 = json.load(open('units3.json', encoding='utf-8'))
OF = {int(k): v for k, v in T['rg']['of'].items()}; RG = T['rg']['g']
for f in sys.argv[1:]:
    N = json.load(open(f, encoding='utf-8'))
    byct = {(n['card'], n['text']): n['k'] for n in N['nodes']}; C = {n['k']: n['c'] for n in N['nodes']}
    NEWK = {n['k']: (re.match(r'([A-Z]+\d*)-', n['card']) or [0, ''])[1] in NEW for n in N['nodes']}
    eff = collections.defaultdict(set)
    for i, r in enumerate(QA):
        g = OF.get(i); u = r[3]
        if g is None or u is None or not (0 <= u < len(U3)) or not RG[g][2]: continue      # consistent groups only
        k = byct.get((U3[u]['card'], U3[u]['text']))
        if k is not None: eff[g].add(k)
    same = tot = 0; so = to = sn = tn = 0
    for g, ks in eff.items():
        ks = sorted(ks)
        if len(ks) < 2 or len(ks) > 40: continue
        for a, b in itertools.combinations(ks, 2):
            tot += 1; same += C[a] == C[b]
            if NEWK[a] or NEWK[b]: tn += 1; sn += C[a] == C[b]
            else: to += 1; so += C[a] == C[b]
    G = nx.Graph()
    for a, b, _, _, why in N['links']:
        sc = [int(w[1:]) / 100 for w in why.split(',') if w and w[0] != 'q']
        if sc: G.add_edge(a, b, weight=1 - math.prod(1 - v for v in sc))
    part = collections.defaultdict(set)
    for k, c in C.items():
        if k in G: part[c].add(k)
    Q = nx.community.modularity(G, list(part.values()), weight='weight')
    sizes = collections.Counter(C.values())
    print(f, {'rg_pairs': tot, 'rg_same_cluster': round(same / tot, 4), 'rg_old': round(so / max(1, to), 4), 'rg_new': round(sn / max(1, tn), 4), 'n_new_pairs': tn, 'modularity': round(Q, 4), 'fine': len(sizes), 'largest': round(max(sizes.values()) / len(C), 3)})
