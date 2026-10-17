"""Is the effect-network clustering natural? Resolution sweep, seed stability, null-model modularity, agreement with rulebook structure.
usage: python cluster_check.py fine            -> net/cc_fine.json
       python cluster_check.py coarse <RES_F>  -> net/cc_coarse.json"""
import sys, json, math, pickle, random, itertools, collections, time
import numpy as np, networkx as nx
from sklearn.metrics import adjusted_mutual_info_score as AMI, adjusted_rand_score as ARI, normalized_mutual_info_score as NMI

D = pickle.load(open('net/G.pkl', 'rb')); G = D['G']; N = G.number_of_nodes()
SEEDS = list(range(10))

def labels(parts, n):
    lab = np.zeros(n, int)
    for c, mem in enumerate(parts):
        for k in mem: lab[k] = c
    return lab

def stab(labs):
    pr = list(itertools.combinations(range(len(labs)), 2))
    return float(np.mean([AMI(labs[i], labs[j]) for i, j in pr])), float(np.mean([ARI(labs[i], labs[j]) for i, j in pr]))

def null_graph(g, seed):
    """degree-preserving rewire + weight shuffle (configuration-model null)"""
    h = nx.Graph(); h.add_nodes_from(g); h.add_edges_from(g.edges())
    try: nx.double_edge_swap(h, nswap=2 * h.number_of_edges(), max_tries=20 * h.number_of_edges(), seed=seed)
    except nx.NetworkXAlgorithmError: pass   # near-complete graph (cluster level): topology fixed, weights shuffled only
    w = [d['weight'] for _, _, d in g.edges(data=True)]; random.Random(seed).shuffle(w)
    for (a, b), x in zip(h.edges(), w): h[a][b]['weight'] = x
    return h

def sweep(g, grid, n, refs, null=None):
    rows, prev = [], None
    for gm in grid:
        t0 = time.time(); labs, qs, cnt, cnt20 = [], [], [], []
        for s in SEEDS:
            p = nx.community.louvain_communities(g, weight='weight', resolution=gm, seed=s)
            labs.append(labels(p, n)); qs.append(nx.community.modularity(g, p, weight='weight', resolution=1))
            cnt.append(len(p)); cnt20.append(sum(len(c) >= 20 for c in p))
        a, r = stab(labs)
        row = {'res': gm, 'k_mean': float(np.mean(cnt)), 'k_min': min(cnt), 'k_max': max(cnt), 'k20': float(np.mean(cnt20)),
               'Q': float(np.mean(qs)), 'seed_AMI': a, 'seed_ARI': r,
               'adj_AMI': float(AMI(prev, labs[0])) if prev is not None else None}
        for nm, ref in refs.items(): row['AMI_' + nm] = float(np.mean([AMI(ref, l) for l in labs]))
        if null is not None:
            qn = [nx.community.modularity(h, nx.community.louvain_communities(h, weight='weight', resolution=gm, seed=0), weight='weight', resolution=1) for h in null]
            row['Q_null'] = float(np.mean(qn)); row['Q_null_sd'] = float(np.std(qn))
        prev = labs[0]; rows.append(row)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, f'{time.time() - t0:.0f}s', flush=True)
    return rows

if sys.argv[1] == 'fine':
    enc = lambda xs: np.unique(xs, return_inverse=True)[1]
    refs = {'cls': enc(D['cls']), 'grp': enc(D['grp'])}
    print('null graphs…', flush=True); null = [null_graph(G, s) for s in range(3)]
    grid = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.5, 3.0, 4.0, 5.0]
    rows = sweep(G, grid, N, refs, null)
    json.dump({'N': N, 'E': G.number_of_edges(), 'rows': rows}, open('net/cc_fine.json', 'w'), indent=1)
elif sys.argv[1] == 'coarse_node':
    # coarse level taken from the effect graph itself at low resolution; purity = share of effects whose fine cluster's majority coarse group is their own
    rf = float(sys.argv[2])
    fine = labels(nx.community.louvain_communities(G, weight='weight', resolution=rf, seed=5), N); rows = []
    for gc in [0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.8]:
        labs = [labels(nx.community.louvain_communities(G, weight='weight', resolution=gc, seed=s), N) for s in SEEDS[:6]]
        c = labs[0]; pur = sum(collections.Counter(c[fine == f]).most_common(1)[0][1] for f in range(fine.max() + 1)) / N
        Q = nx.community.modularity(G, [set(np.where(c == i)[0]) for i in range(c.max() + 1)], weight='weight')
        row = {'res': gc, 'k': int(c.max() + 1), 'Q': float(Q), 'seed_AMI': stab(labs)[0], 'purity': float(pur)}
        rows.append(row); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    json.dump({'RES_F': rf, 'rows': rows}, open('net/cc_coarse_node.json', 'w'), indent=1)
else:
    rf = float(sys.argv[2])
    fine = sorted(nx.community.louvain_communities(G, weight='weight', resolution=rf, seed=5), key=len, reverse=True)
    comm = labels(fine, N); F = len(fine)
    CG = nx.Graph(); CG.add_nodes_from(range(F))
    for a, b, d in G.edges(data=True):
        ca, cb = comm[a], comm[b]
        if ca != cb: CG.add_edge(ca, cb, w=(CG[ca][cb]['w'] if CG.has_edge(ca, cb) else 0) + d['weight'])
    for a, b, d in CG.edges(data=True): d['weight'] = d['w'] / math.sqrt(len(fine[a]) * len(fine[b]))
    # cluster-level majority class as reference
    maj = [collections.Counter(D['cls'][k] for k in m).most_common(1)[0][0] for m in fine]
    refs = {'cls': np.unique(maj, return_inverse=True)[1]}
    null = [null_graph(CG, s) for s in range(5)]
    grid = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.5, 3.0, 3.5]
    rows = sweep(CG, grid, F, refs, null)
    json.dump({'RES_F': rf, 'F': F, 'rows': rows}, open('net/cc_coarse.json', 'w'), indent=1)
