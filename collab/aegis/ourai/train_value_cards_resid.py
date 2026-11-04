"""Residual card model: logit = prior_logit(x) + a*prior_logit + C.w + b, trained with strong L2 on card weights only.
python -X utf8 train_value_cards_resid.py DATA_GLOB OUT.json PRIOR.json"""
import collections, glob, json, sys
import numpy as np, torch
GROUPS = ['mb', 'ob', 'ms', 'os', 'mh', 'mt', 'ot']
rows = [json.loads(l) for f in sorted(glob.glob(sys.argv[1])) for l in open(f, encoding='utf-8') if l.strip()]
rows = [r for r in rows if 'c' in r]
g = np.array([r['g'] for r in rows]); te = g % 5 == 0
P = json.load(open(sys.argv[3]))
X = np.array([r['x'] for r in rows], dtype=np.float64)
h = (X - np.array(P['features_mean'])) / np.array(P['features_std'])
for k, L in enumerate(P['layers']):
    h = h @ np.array(L['W']).T + np.array(L['b'])
    if k < len(P['layers']) - 1: h = np.maximum(h, 0)
prior = h[:, 0].astype(np.float32)
y = np.array([r['y'] for r in rows], dtype=np.float32)
def metrics(p, t):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return dict(logloss=round(float(-(t * np.log(p) + (1 - t) * np.log(1 - p)).mean()), 4), acc=round(float(((p > .5) == (t > .5)).mean()), 4))
print('prior', metrics(1 / (1 + np.exp(-prior[te])), y[te]))
best = None
for minc in (30, 80):
    freq = collections.Counter(c for r, t in zip(rows, te) if not t for k in GROUPS for c in set(r['c'][k]))
    vocab = sorted(c for c, n in freq.items() if n >= minc); ix = {c: i for i, c in enumerate(vocab)}; V = len(vocab)
    C = np.zeros((len(rows), len(GROUPS) * V), dtype=np.float32)
    for n, r in enumerate(rows):
        for k, grp in enumerate(GROUPS):
            for c in r['c'][grp]:
                if c in ix: C[n, k * V + ix[c]] += 1
    for lam in (1e-3, 3e-3, 1e-2, 3e-2):
        torch.manual_seed(0)
        w = torch.zeros(C.shape[1], requires_grad=True); a = torch.zeros(1, requires_grad=True); b = torch.zeros(1, requires_grad=True)
        Ct, pt, yt = torch.tensor(C[~te]), torch.tensor(prior[~te]), torch.tensor(y[~te])
        opt = torch.optim.LBFGS([w, a, b], max_iter=200, line_search_fn='strong_wolfe')
        lossf = torch.nn.BCEWithLogitsLoss()
        def closure():
            opt.zero_grad(); l = lossf(pt * (1 + a) + Ct @ w + b, yt) + lam * (w ** 2).sum(); l.backward(); return l
        opt.step(closure)
        with torch.no_grad(): p = torch.sigmoid(torch.tensor(prior[te]) * (1 + a) + torch.tensor(C[te]) @ w + b).numpy()
        m = metrics(p, y[te]); print('minc', minc, 'V', V, 'lam', lam, m)
        if best is None or m['logloss'] < best[0]['logloss']: best = (m, vocab, w.detach().numpy().copy(), float(a), float(b), minc, lam)
m, vocab, w, a, b, minc, lam = best
json.dump({'model': 'resid', 'key': 'xr', 'prior': P, 'groups': GROUPS, 'vocab': vocab, 'scale': 1 + a, 'bias': b,
           'card_w': w.tolist(), 'test': m, 'minc': minc, 'lam': lam}, open(sys.argv[2], 'w'))
print('saved', m, minc, lam)
