"""Our value function for Aegis positions: P(win | position, side to evaluate), trained on self-play outcomes.

python -X utf8 train_value.py DATA_GLOB OUT.json
Split by game (game id % 5 == 0 -> test), so no game contributes positions to both sides.
Reports log loss / accuracy / Brier against Aegis's hand-tuned evaluateSearchPosition (field b) on the same test positions.
"""
import glob, json, math, sys
import numpy as np
import torch

KEY = sys.argv[3] if len(sys.argv) > 3 else 'x'
PRIOR = sys.argv[4] if len(sys.argv) > 4 else None
rows = [json.loads(l) for f in sorted(glob.glob(sys.argv[1])) for l in open(f, encoding='utf-8') if l.strip()]
rows = [r for r in rows if KEY in r]
X = np.array([r[KEY] for r in rows], dtype=np.float32)
y = np.array([r['y'] for r in rows], dtype=np.float32)
B = np.array([r.get('b', 0.5) for r in rows], dtype=np.float64)
g = np.array([r['g'] for r in rows])
te = g % 5 == 0
print('positions', len(rows), 'games', len(set(g)), 'test positions', int(te.sum()))
mu, sd = X[~te].mean(0), X[~te].std(0) + 1e-6
Z = (X - mu) / sd


def metrics(p, t):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return dict(logloss=round(float(-(t * np.log(p) + (1 - t) * np.log(1 - p)).mean()), 4),
                acc=round(float(((p > .5) == (t > .5)).mean()), 4), brier=round(float(((p - t) ** 2).mean()), 4))


def fit(hidden, epochs=60, wd=1e-4, seed=0):
    torch.manual_seed(seed)
    d = Z.shape[1]
    layers, w = [], d
    for h in hidden:
        layers += [torch.nn.Linear(w, h), torch.nn.ReLU()]; w = h
    layers += [torch.nn.Linear(w, 1)]
    net = torch.nn.Sequential(*layers)
    opt = torch.optim.AdamW(net.parameters(), lr=3e-3, weight_decay=wd)
    xt, yt = torch.tensor(Z[~te]), torch.tensor(y[~te])
    lossf = torch.nn.BCEWithLogitsLoss()
    for ep in range(epochs):
        perm = torch.randperm(len(xt))
        for i in range(0, len(xt), 512):
            idx = perm[i:i + 512]
            opt.zero_grad(); loss = lossf(net(xt[idx]).squeeze(1), yt[idx]); loss.backward(); opt.step()
    with torch.no_grad():
        p = torch.sigmoid(net(torch.tensor(Z[te])).squeeze(1)).numpy()
    return net, p


print('aegis evaluateSearchPosition', metrics(B[te], y[te]))
print('constant 0.5', metrics(np.full(int(te.sum()), .5), y[te]))
if PRIOR:
    P = json.load(open(PRIOR))
    h = (np.array([r['x'] for r in rows], dtype=np.float64) - np.array(P['features_mean'])) / np.array(P['features_std'])
    for k, L in enumerate(P['layers']):
        h = h @ np.array(L['W']).T + np.array(L['b'])
        if k < len(P['layers']) - 1: h = np.maximum(h, 0)
    print('prior model', PRIOR.split('/')[-1], metrics(1 / (1 + np.exp(-h[te, 0])), y[te]))
best = None
for name, hidden, ep in (('logistic', [], 60), ('mlp32', [32], 15), ('mlp64', [64, 64], 8)):
    net, p = fit(hidden, epochs=ep)
    m = metrics(p, y[te]); print(name, m)
    if best is None or m['logloss'] < best[2]['logloss']: best = (name, net, m)
name, net, m = best
lin = [l for l in net if isinstance(l, torch.nn.Linear)]
json.dump({'model': name, 'key': KEY, 'features_mean': mu.tolist(), 'features_std': sd.tolist(),
           'layers': [{'W': l.weight.detach().numpy().tolist(), 'b': l.bias.detach().numpy().tolist()} for l in lin],
           'test': m, 'positions': len(rows)}, open(sys.argv[2], 'w'))
print('saved', name, '->', sys.argv[2])
turns = np.array([r['t'] for r in rows])
with torch.no_grad():
    p = torch.sigmoid(net(torch.tensor(Z[te])).squeeze(1)).numpy()
for lo, hi in ((1, 4), (5, 8), (9, 14), (15, 99)):
    k = (turns[te] >= lo) & (turns[te] <= hi)
    if k.sum(): print(f'turns {lo}-{hi}', int(k.sum()), 'ours', metrics(p[k], y[te][k]), 'aegis', metrics(B[te][k], y[te][k]))
