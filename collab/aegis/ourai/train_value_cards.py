"""Card-aware value: summary features x + card-count features per zone (own board tops, opp board tops, own/opp sources, own hand, own/opp trash).

python -X utf8 train_value_cards.py DATA_GLOB OUT.json [PRIOR.json]
Rows without the `c` field are skipped. Split by game id % 5 == 0 -> test (same rule as train_value.py).
"""
import collections, glob, json, sys
import numpy as np
import torch

GROUPS = ['mb', 'ob', 'ms', 'os', 'mh', 'mt', 'ot']
rows = [json.loads(l) for f in sorted(glob.glob(sys.argv[1])) for l in open(f, encoding='utf-8') if l.strip()]
rows = [r for r in rows if 'c' in r]
g = np.array([r['g'] for r in rows]); te = g % 5 == 0
freq = collections.Counter(c for r, t in zip(rows, te) if not t for k in GROUPS for c in set(r['c'][k]))
vocab = sorted(c for c, n in freq.items() if n >= 30)
ix = {c: i for i, c in enumerate(vocab)}
V = len(vocab)
print('positions', len(rows), 'games', len(set(g)), 'test', int(te.sum()), 'vocab', V)
X = np.array([r['x'] for r in rows], dtype=np.float32)
C = np.zeros((len(rows), len(GROUPS) * V), dtype=np.float32)
for n, r in enumerate(rows):
    for k, grp in enumerate(GROUPS):
        for c in r['c'][grp]:
            if c in ix: C[n, k * V + ix[c]] += 1
y = np.array([r['y'] for r in rows], dtype=np.float32)
B = np.array([r['b'] for r in rows])
mu, sd = X[~te].mean(0), X[~te].std(0) + 1e-6
Z = np.concatenate([(X - mu) / sd, C], 1)


def metrics(p, t):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return dict(logloss=round(float(-(t * np.log(p) + (1 - t) * np.log(1 - p)).mean()), 4), acc=round(float(((p > .5) == (t > .5)).mean()), 4))


def fit(hidden, epochs, wd, seed=0):
    torch.manual_seed(seed)
    layers, w = [], Z.shape[1]
    for h in hidden: layers += [torch.nn.Linear(w, h), torch.nn.ReLU()]; w = h
    net = torch.nn.Sequential(*layers, torch.nn.Linear(w, 1))
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=wd)
    xt, yt = torch.tensor(Z[~te]), torch.tensor(y[~te]); lossf = torch.nn.BCEWithLogitsLoss()
    for _ in range(epochs):
        perm = torch.randperm(len(xt))
        for i in range(0, len(xt), 512):
            idx = perm[i:i + 512]; opt.zero_grad(); lossf(net(xt[idx]).squeeze(1), yt[idx]).backward(); opt.step()
    with torch.no_grad(): p = torch.sigmoid(net(torch.tensor(Z[te])).squeeze(1)).numpy()
    return net, p


print('aegis', metrics(B[te], y[te]))
if len(sys.argv) > 3:
    P = json.load(open(sys.argv[3]))
    h = (X.astype(np.float64) - np.array(P['features_mean'])) / np.array(P['features_std'])
    for k, L in enumerate(P['layers']):
        h = h @ np.array(L['W']).T + np.array(L['b'])
        if k < len(P['layers']) - 1: h = np.maximum(h, 0)
    print('prior', metrics(1 / (1 + np.exp(-h[te, 0])), y[te]))
best = None
for name, hidden, ep, wd in (('logistic', [], 20, 1e-2), ('mlp32', [32], 10, 1e-2), ('mlp64', [64], 8, 3e-2)):
    net, p = fit(hidden, ep, wd); m = metrics(p, y[te]); print(name, m)
    if best is None or m['logloss'] < best[2]['logloss']: best = (name, net, m)
name, net, m = best
lin = [l for l in net if isinstance(l, torch.nn.Linear)]
json.dump({'model': name, 'key': 'xc', 'groups': GROUPS, 'vocab': vocab, 'features_mean': mu.tolist(), 'features_std': sd.tolist(),
           'layers': [{'W': l.weight.detach().numpy().tolist(), 'b': l.bias.detach().numpy().tolist()} for l in lin], 'test': m}, open(sys.argv[2], 'w'))
print('saved', name, sys.argv[2])
