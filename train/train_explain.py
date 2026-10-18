"""Retrieval model for explanation (non-yes/no) questions: find an older official Q&A whose answer can be reused.

Positives = pairs of older questions whose official answers are near-identical (char-bigram Jaccard >= 0.7) —
"the same question asked about another card". Bi-encoder fine-tuned with in-batch negatives
(sentence-transformers MultipleNegativesRankingLoss).

Report on the newest products (test): answer the top-1 retrieved Q&A only when its cosine >= t; coverage and
agreement (true official answer vs reused answer, Jaccard >= 0.5) per t, next to the browser's bigram rule
(E26: 42.1 % coverage, 117/118 agreement).

Usage:
  python train/train_explain.py --model jhgan/ko-sroberta-multitask --epochs 3 --bs 64
  python train/train_explain.py --tiny        # CPU smoke test
"""
import argparse, json, os, re, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--model', default='jhgan/ko-sroberta-multitask')
ap.add_argument('--epochs', type=int, default=3)
ap.add_argument('--bs', type=int, default=64)
ap.add_argument('--lr', type=float, default=2e-5)
ap.add_argument('--name', default=None)
ap.add_argument('--tiny', action='store_true')
a = ap.parse_args()
if a.tiny:
    a.model, a.epochs, a.bs = 'sentence-transformers-testing/stsb-bert-tiny-safetensors', 1, 16
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

name = a.name or (a.model.split('/')[-1] + ('_tiny' if a.tiny else ''))
RUN = os.path.join(HERE, 'runs', 'explain_' + name); os.makedirs(RUN, exist_ok=True)
load = lambda s: [json.loads(l) for l in open(os.path.join(HERE, 'data', f'explain_{s}.jsonl'), encoding='utf-8')]
tr, va, te = load('train'), load('valid'), load('test')
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
jac = lambda A, B: len(A & B) / ((len(A) + len(B) - len(A & B)) or 1)
SPEC = re.compile(r'이 (?:카드|테이머|디지몬|옵션)')
terms = lambda q: set(re.findall(r'「[^「」]{2,40}」', q))

pool = tr + va
AB = [bg(r['answer']) for r in tr]
pairs = []
for i in range(len(tr)):
    for j in range(i + 1, len(tr)):
        if jac(AB[i], AB[j]) >= 0.7:
            pairs.append((tr[i]['question'], tr[j]['question']))
random.Random(13).shuffle(pairs)
if a.tiny: pairs = pairs[:64]
print('positive pairs', len(pairs), '| pool', len(pool), 'test', len(te))

model = SentenceTransformer(a.model)
if pairs:
    ex = [InputExample(texts=[p, q]) for p, q in pairs] + [InputExample(texts=[q, p]) for p, q in pairs]
    dl = DataLoader(ex, shuffle=True, batch_size=a.bs)
    model.fit(train_objectives=[(dl, losses.MultipleNegativesRankingLoss(model))], epochs=a.epochs, warmup_steps=int(0.1 * len(dl) * a.epochs),
              optimizer_params={'lr': a.lr}, show_progress_bar=True)
model.save(RUN)

P = model.encode([r['question'] for r in pool], normalize_embeddings=True, batch_size=128)
Q = model.encode([r['question'] for r in te], normalize_embeddings=True, batch_size=128)
S = Q @ P.T
rows = []
for k, r in enumerate(te):
    order = np.argsort(-S[k])
    for j in order[:20]:
        c = pool[j]
        # same rule as the page: a question about "this card" only reuses an answer that shares the quoted term
        if SPEC.search(r['question']) and not (terms(r['question']) & terms(c['question'])) and c['card'] != r['card']:
            continue
        rows.append((float(S[k, j]), jac(bg(r['answer']), bg(c['answer'])), r['id'], c['id'])); break
curve = []
for t in (0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.6):
    sel = [x for x in rows if x[0] >= t]
    curve.append({'cos>=': t, 'coverage': round(len(sel) / len(te), 4), 'agree': round(sum(x[1] >= 0.5 for x in sel) / len(sel), 4) if sel else None})
print(json.dumps(curve, indent=1))
json.dump({'args': vars(a), 'pairs': len(pairs), 'curve': curve, 'baseline_browser_bigram': {'coverage': 0.421, 'agree_on_reuse': '117/118'}},
          open(os.path.join(RUN, 'metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(rows, open(os.path.join(RUN, 'test_retrieval.json'), 'w'))
