"""Contrastive retriever: colloquial question -> official Q&A of the same judgement (E31). Retrieval only; it never answers yes/no.

Positives (anchor, positive) from the pre-BT22 Q&A (pool):
  * same reason group (reason_groups: the official answers give the same reason) AND same polarity (answer as asked), or
  * same (asked-thing, situation slots, polarity) AND official answers with char-bigram Jaccard >= --ans_jac.
Hard negatives: very similar wording (TF-IDF char 2-gram cosine >= --hn_cos) but the OPPOSITE yes/no answer.
Colloquial augmentation: the anchor is run through colloquialize() (abbreviations, spacing, typos, dropped brackets).
Eval-set exclusion: every Q&A listed in paper/results/colloquial_test.json (and any new-product Q&A) is never trained on.
Loss: MultipleNegativesRankingLoss on (anchor, positive, hard negative) triplets (+ in-batch negatives).

Evaluation (writes train/runs/retriever_<name>/metrics.json):
  time_split : queries = newest-product (BT22..ST22) official questions, corpus = older products; gold = same group+polarity.
  colloquial : paper/results/colloquial_test.json colloquial text, corpus = older products + same-card Q&A, source removed (mode B).
  Each is compared with the browser's 2-gram Jaccard (baseline) on the same queries/corpus, and with the zero-shot base model.

Usage:
  python train/train_retriever.py --model jhgan/ko-sroberta-multitask --epochs 3 --bs 64        # GPU (GTX 1660 SUPER 6GB: bs 32-64 ok)
  python train/train_retriever.py --tiny                                                      # CPU smoke test (seconds)
"""
import argparse, json, os, re, random, sys, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument('--model', default='jhgan/ko-sroberta-multitask')
ap.add_argument('--epochs', type=int, default=3)
ap.add_argument('--bs', type=int, default=64)
ap.add_argument('--lr', type=float, default=2e-5)
ap.add_argument('--per_anchor', type=int, default=3, help='positives sampled per anchor')
ap.add_argument('--ans_jac', type=float, default=0.5)
ap.add_argument('--hn_cos', type=float, default=0.55)
ap.add_argument('--aug_p', type=float, default=0.7, help='probability an anchor is colloquialized')
ap.add_argument('--vague_p', type=float, default=0.0, help='probability an anchor is made vague (details dropped, E38)')
ap.add_argument('--ctx', action='store_true', help='prefix every question with its effect text (card context, E38)')
ap.add_argument('--eval_only', default=None, help='evaluate an existing model dir (no training)')
ap.add_argument('--norm', action='store_true', help='run qnorm.normalize on queries/corpus at train and test time')
ap.add_argument('--name', default=None)
ap.add_argument('--tiny', action='store_true')
a = ap.parse_args()
if a.tiny:
    a.model, a.epochs, a.bs = 'sentence-transformers-testing/stsb-bert-tiny-safetensors', 1, 16
sys.path.insert(0, ROOT)
import qnorm as Q

NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))
QA, CARDS = T['qa'], T['cards']
OF = {int(k): v for k, v in T['rg']['of'].items()}
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s or '').strip()
pol = lambda i: (QA[i][8] ^ QA[i][9]) if QA[i][8] >= 0 else None
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
jac = lambda A, B: len(A & B) / ((len(A) + len(B) - len(A & B)) or 1)
prep = (lambda s: Q.normalize(s)) if a.norm else (lambda s: s)

CS = json.load(open(os.path.join(ROOT, 'paper', 'results', 'colloquial_test.json'), encoding='utf-8'))['items']
BANNED = {x['qid'] for x in CS}
DOC = [i for i, r in enumerate(QA) if r[0]]
POOL = [i for i in DOC if prod(QA[i][0]) not in NEW and i not in BANNED]
assert not (set(POOL) & BANNED)
TESTQ = [i for i in DOC if prod(QA[i][0]) in NEW]
print('pool', len(POOL), '| new-product Q&A', len(TESTQ), '| banned (eval set)', len(BANNED))


# ---------------- colloquial augmentation ----------------
SUBS = [(r'【등장 시】', ['등장시', '등장 시', '등시']), (r'【진화 시】', ['진화시', '진화 시']), (r'【어택 시】', ['어택시', '어택 시']),
        (r'【소멸 시】', ['소멸시']), (r'【시큐리티】 ?효과', ['시큐 효과', '시큐리티 효과']), (r'시큐리티', ['시큐', '시큐리티']),
        (r'진화원 효과', ['상속', '진화원 효과', '진화원효과']), (r'《1 드로우》', ['1드로', '1드로우']), (r'배틀 에어리어', ['배틀에어리어', '필드']),
        (r'발휘할 수 있(?:나요|습니까)\?', ['쓸수있어?', '쓸 수 있음?', '발휘돼?', '발휘 가능?']), (r'되나요\?', ['돼?', '되나여', '됨?']),
        (r'있나요\?', ['있음?', '있어?', '잇나여']), (r'무엇인가요\?', ['뭐임?', '머야?']), (r'어떻게', ['어케', '어떻게']),
        (r'(?:하나요|합니까)\?', ['함?', '하냐?', '하나?']), (r'유발되나요\?', ['유발됨?', '유발돼?'])]


def colloquialize(q, rng):
    s = re.sub(r'^이 카드의 ', '' if rng.random() < .5 else '이 카드 ', q)
    for pat, opts in SUBS:
        if rng.random() < .8:
            s = re.sub(pat, lambda m: rng.choice(opts), s)
    s = re.sub(r'[「」【】《》]', lambda m: '' if rng.random() < .8 else m.group(0), s)
    s = re.sub(r'(?:BT|EX|ST|P)\d*-\d+ ', '', s)
    if rng.random() < .4:
        s = re.sub(r'\s+', lambda m: '' if rng.random() < .4 else ' ', s)
    if rng.random() < .3 and len(s) > 8:
        k = rng.randrange(2, len(s) - 2)
        s = s[:k] + s[k + 1:] if rng.random() < .5 else s[:k] + s[k + 1] + s[k] + s[k + 2:]
    return s


def vague(q, rng):
    """E38: an under-specified version — keep the asking clause and at most one short detail; drop names and numbers."""
    s = re.sub(r'「[^「」]*」|(?:BT|EX|ST|P|LM|RB|AD)\d*-\d+', '', q)
    parts = [x.strip() for x in re.split(r'[,，]|(?<=때)|(?<=후)|(?<=서)\s', s) if x.strip()]
    if not parts: return q
    keep = [parts[-1]]
    if len(parts) > 1 and rng.random() < .6:
        det = rng.choice(parts[:-1]); keep.insert(0, det[:14])
    out = ' '.join(keep)
    out = re.sub(r'이 카드의 |이 카드는 |이 카드가 ', '' if rng.random() < .5 else '이거 ', out)
    return colloquialize(out, rng) if rng.random() < .5 else out


CTX = {}
def ctx(i):
    if not a.ctx: return ''
    if i not in CTX:
        u = QA[i][3]; t_ = T['units'][u][3] if u is not None and u >= 0 else (CARDS.get(QA[i][0]) or [''])[0]
        CTX[i] = re.sub(r'\s+', ' ', t_)[:100] + ' | '
    return CTX[i]


# ---------------- pair mining ----------------
def mine(rng):
    ans_bg = {i: bg(cq(QA[i][2])) for i in POOL}
    by_grp = collections.defaultdict(list)
    for i in POOL:
        if i in OF:
            by_grp[(OF[i], pol(i))].append(i)
    key = lambda i: (QA[i][6], tuple(QA[i][7]) if isinstance(QA[i][7], list) else QA[i][7], pol(i))
    by_key = collections.defaultdict(list)
    for i in POOL:
        if pol(i) is not None:
            by_key[key(i)].append(i)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize
    X = normalize(TfidfVectorizer(analyzer='char', ngram_range=(2, 2), sublinear_tf=True).fit_transform([QA[i][1] for i in POOL]))
    S = (X @ X.T).tocsr()
    idx = {i: k for k, i in enumerate(POOL)}
    trip = []
    for i in POOL:
        cands = [j for j in by_grp.get((OF.get(i), pol(i)), []) if j != i]
        cands += [j for j in by_key.get(key(i), []) if j != i and jac(ans_bg[i], ans_bg[j]) >= a.ans_jac]
        cands = sorted(set(cands))
        if not cands:
            continue
        rng.shuffle(cands)
        row = S[idx[i]]
        hn = [POOL[c] for c, v in zip(row.indices, row.data) if v >= a.hn_cos and POOL[c] != i and pol(POOL[c]) is not None
              and pol(i) is not None and pol(POOL[c]) != pol(i)]
        for j in cands[:a.per_anchor]:
            n = rng.choice(hn) if hn else rng.choice(POOL)
            trip.append((i, j, n, bool(hn)))
    return trip


rng = random.Random(13)
trip = mine(rng)
if a.tiny:
    trip = trip[:64]
print('triplets', len(trip), '| with real hard negative', sum(t[3] for t in trip))

from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

name = a.name or (a.model.split('/')[-1] + ('_tiny' if a.tiny else ''))
RUN = os.path.join(HERE, 'runs', 'retriever_' + name)
os.makedirs(RUN, exist_ok=True)


# ---------------- evaluation ----------------
def encode(model, pairs):
    """pairs: (text, qa_index) — the index gives the card context when --ctx"""
    return model.encode([ctx(i) + prep(t) for t, i in pairs], normalize_embeddings=True, batch_size=128, show_progress_bar=False)


def recall(rankfn, items):
    hit = {1: 0, 3: 0, 10: 0}
    for q, cand, gold in items:
        rk = rankfn(q, cand)
        for k in hit:
            hit[k] += bool(gold & set(rk[:k]))
    n = len(items)
    return {'n': n, **{f'recall@{k}': round(v / n, 3) if n else None for k, v in hit.items()}}


def build_eval():
    GRP = collections.defaultdict(set)
    for i, g in OF.items():
        GRP[g].add(i)
    poolset = set(POOL)
    ts, co = [], []
    for i in TESTQ:                                   # time split: official newest-product question -> older corpus
        g = {j for j in GRP.get(OF.get(i), ()) if j in poolset and (pol(j) == pol(i) or pol(i) is None or pol(j) is None)} if i in OF else set()
        if g:
            ts.append((i, poolset, g))
    bycard = collections.defaultdict(set)
    for i in DOC:
        bycard[QA[i][0]].add(i)
    for x in CS:                                      # colloquial set: corpus = older + same card, source removed
        i = x['qid']
        c = (poolset | bycard[x['card']]) - {i}
        g = {j for j in GRP.get(OF.get(i), ()) if j in c and (pol(j) == pol(i) or pol(i) is None or pol(j) is None)} if i in OF else set()
        if g:
            co.append((x['colloquial'], c, g, i))
    vr = random.Random(7)
    vg = [(vague(QA[i][1], vr), c, g, i) for _, c, g, i in co]   # E38: under-specified versions of the same questions
    return ts, co, vg


def evaluate(model, tag):
    ts, co, vg = build_eval()
    E = dict(zip(DOC, encode(model, [(QA[i][1], i) for i in DOC])))
    BG = {i: bg(QA[i][1]) for i in DOC}
    res = {}
    def run(name, items):
        qv = encode(model, [(t_, i) for t_, _, _, i in items])
        hit = {1: 0, 3: 0, 10: 0}; base = {1: 0, 3: 0, 10: 0}
        for (t_, cand, g, i), v in zip(items, qv):
            cand = list(cand); s = np.stack([E[j] for j in cand]) @ v
            rk = [cand[k] for k in np.argsort(-s)]; bq = bg(t_)
            bk = sorted(cand, key=lambda j: -jac(bq, BG[j]))
            for k in hit:
                hit[k] += bool(g & set(rk[:k])); base[k] += bool(g & set(bk[:k]))
        n = len(items)
        res[name] = {'n': n, 'model': {f'recall@{k}': round(v / n, 3) for k, v in hit.items()},
                     'browser_2gram': {f'recall@{k}': round(v / n, 3) for k, v in base.items()}}
    run('time_split', [(QA[i][1], c, g, i) for i, c, g in ts])
    run('colloquial', co)
    run('vague', vg)
    print(tag, json.dumps(res, ensure_ascii=False))
    return res


if a.eval_only:
    res = evaluate(SentenceTransformer(a.eval_only), 'eval-only')
    json.dump({'args': vars(a), 'eval': res}, open(os.path.join(RUN, 'metrics_eval.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sys.exit(0)
model = SentenceTransformer(a.model)
zero = evaluate(model, 'zero-shot')
ex = []
for i, j, n, _ in trip:
    r_ = rng.random()
    anc = vague(QA[i][1], rng) if r_ < a.vague_p else (colloquialize(QA[i][1], rng) if rng.random() < a.aug_p else QA[i][1])
    ex.append(InputExample(texts=[ctx(i) + prep(anc), ctx(j) + prep(QA[j][1]), ctx(n) + prep(QA[n][1])]))
dl = DataLoader(ex, shuffle=True, batch_size=a.bs)
model.fit(train_objectives=[(dl, losses.MultipleNegativesRankingLoss(model))], epochs=a.epochs, warmup_steps=int(0.1 * len(dl) * a.epochs),
          optimizer_params={'lr': a.lr}, show_progress_bar=True)
model.save(os.path.join(RUN, 'model'))
tuned = evaluate(model, 'fine-tuned')
json.dump({'args': vars(a), 'triplets': len(trip), 'zero_shot': zero, 'fine_tuned': tuned,
           'note': 'eval items are never in the training pool; browser_2gram = judge helper baseline on the same queries/corpus'},
          open(os.path.join(RUN, 'metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
