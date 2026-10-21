"""Distil the fine-tuned retriever (teacher, ko-sroberta, 110M) into a tiny browser-ready student.

Student = hashed char 2/3-gram bag -> EmbeddingBag(mean, dim D) -> Linear(D, D) -> L2 normalise.
Hashing is FNV-1a over code points (identical in the browser JS), so the student runs with no tokenizer or ONNX.
Trained with cosine loss to the teacher's embeddings of the SAME texts, including colloquial variants of the pool.

Eval items (colloquial_test.json, newest-product queries) are never in the training pool (same rule as train_retriever.py).
Writes train/runs/distill_<name>/metrics.json and student.npz (int8 weights for export).

Usage:
  python train/distill_retriever.py --teacher train/runs/retriever_base/model --name d128
  python train/distill_retriever.py --tiny
"""
import argparse, json, os, re, random, sys, collections
import numpy as np
import torch, torch.nn as nn, torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument('--teacher', default=os.path.join(HERE, 'runs', 'retriever_base', 'model'))
ap.add_argument('--dim', type=int, default=128)
ap.add_argument('--buckets', type=int, default=16384)
ap.add_argument('--aug', type=int, default=6, help='colloquial variants per pool Q&A')
ap.add_argument('--epochs', type=int, default=30)
ap.add_argument('--bs', type=int, default=256)
ap.add_argument('--lr', type=float, default=2e-3)
ap.add_argument('--seed', type=int, default=13)
ap.add_argument('--name', default='d128')
ap.add_argument('--tiny', action='store_true')
a = ap.parse_args()
random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
if a.tiny:
    a.epochs, a.aug = 1, 1

# ---------------- data (same construction as train_retriever.py) ----------------
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))
QA = T['qa']
OF = {int(k): v for k, v in T['rg']['of'].items()}
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s or '').strip()
pol = lambda i: (QA[i][8] ^ QA[i][9]) if QA[i][8] >= 0 else None
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
jac = lambda A, B: len(A & B) / ((len(A) + len(B) - len(A & B)) or 1)
CS = json.load(open(os.path.join(ROOT, 'paper', 'results', 'colloquial_test.json'), encoding='utf-8'))['items']
BANNED = {x['qid'] for x in CS}
DOC = [i for i, r in enumerate(QA) if r[0]]
POOL = [i for i in DOC if prod(QA[i][0]) not in NEW and i not in BANNED]
assert not (set(POOL) & BANNED)
TESTQ = [i for i in DOC if prod(QA[i][0]) in NEW]

SUBS = [(r'【등장 시】', ['등장시', '등장 시', '등시']), (r'【진화 시】', ['진화시', '진화 시']), (r'【어택 시】', ['어택시', '어택 시']),
        (r'【소멸 시】', ['소멸시']), (r'【시큐리티】 ?효과', ['시큐 효과', '시큐리티 효과']), (r'시큐리티', ['시큐', '시큐리티']),
        (r'진화원 효과', ['상속', '진화원 효과', '진화원효과']), (r'《1 드로우》', ['1드로', '1드로우']), (r'배틀 에어리어', ['배틀에어리어', '필드']),
        (r'발휘할 수 있(?:나요|습니까)\?', ['쓸수있어?', '쓸 수 있음?', '발휘돼?', '발휘 가능?']), (r'되나요\?', ['돼?', '되나여', '됨?']),
        (r'있나요\?', ['있음?', '있어?', '잇나여']), (r'무엇인가요\?', ['뭐임?', '머야?']), (r'어떻게', ['어케', '어떻게']),
        (r'(?:하나요|합니까)\?', ['함?', '하냐?', '하나?']), (r'유발되나요\?', ['유발됨?', '유발돼?'])]


def colloquialize(q, rng):  # copied from train_retriever.py
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


# ---------------- hashed n-gram features (must match the browser JS) ----------------
def fnv(s):
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def grams(text):
    t = '^' + re.sub(r'\s+', '', text.lower()) + '$'
    out = []
    for n in (2, 3):
        out += [t[i:i + n] for i in range(len(t) - n + 1)]
    return out


def feats(texts):
    ids, offs = [], []
    for t in texts:
        offs.append(len(ids))
        ids += [fnv(g) % a.buckets for g in grams(t)] or [0]
    return torch.tensor(ids), torch.tensor(offs)


class Student(nn.Module):
    def __init__(self, out_dim):
        super().__init__()
        self.emb = nn.EmbeddingBag(a.buckets, a.dim, mode='mean')
        self.proj = nn.Linear(a.dim, out_dim)  # out_dim = teacher dim, so cosine loss is well defined

    def forward(self, texts):
        ids, offs = feats(texts)
        d = self.emb.weight.device
        x = self.emb(ids.to(d), offs.to(d))
        return F.normalize(self.proj(x), dim=-1)


dev = 'cuda' if torch.cuda.is_available() else 'cpu'
if a.tiny:
    from sentence_transformers import SentenceTransformer
    teacher = SentenceTransformer('sentence-transformers-testing/stsb-bert-tiny-safetensors', device=dev)
else:
    from sentence_transformers import SentenceTransformer
    teacher = SentenceTransformer(a.teacher, device=dev)
tenc = lambda texts: teacher.encode(texts, normalize_embeddings=True, batch_size=128, show_progress_bar=False)

# ---------------- training set: pool Q&A (canonical + colloquial variants) ----------------
rng = random.Random(a.seed)
pool_txt = [QA[i][1] for i in POOL]
aug_txt = []
for i in POOL:
    for _ in range(a.aug):
        aug_txt.append(colloquialize(QA[i][1], rng))
train_txt = pool_txt + aug_txt
if a.tiny:
    train_txt = train_txt[:128]
print('train texts', len(train_txt), '(pool', len(pool_txt), '+ aug', len(aug_txt), ')')
Ytr = torch.tensor(tenc(train_txt), dtype=torch.float32)

stu = Student(teacher.get_sentence_embedding_dimension()).to(dev)
opt = torch.optim.Adam(stu.parameters(), lr=a.lr)
N = len(train_txt)
for ep in range(a.epochs):
    perm = torch.randperm(N)
    tot = 0.0
    stu.train()
    for k in range(0, N, a.bs):
        b = perm[k:k + a.bs].tolist()
        p = stu([train_txt[j] for j in b])
        loss = (1 - (p * Ytr[b].to(dev)).sum(-1)).mean()
        opt.zero_grad(); loss.backward(); opt.step()
        tot += loss.item() * len(b)
    if ep % 5 == 0 or ep == a.epochs - 1:
        print(f'epoch {ep + 1} loss {tot / N:.4f}')


# ---------------- evaluation (same construction as train_retriever.py) ----------------
def build_eval():
    GRP = collections.defaultdict(set)
    for i, g in OF.items():
        GRP[g].add(i)
    poolset = set(POOL)
    ts, co = [], []
    for i in TESTQ:
        g = {j for j in GRP.get(OF.get(i), ()) if j in poolset and (pol(j) == pol(i) or pol(i) is None or pol(j) is None)} if i in OF else set()
        if g:
            ts.append((i, poolset, g))
    bycard = collections.defaultdict(set)
    for i in DOC:
        bycard[QA[i][0]].add(i)
    for x in CS:
        i = x['qid']
        c = (poolset | bycard[x['card']]) - {i}
        g = {j for j in GRP.get(OF.get(i), ()) if j in c and (pol(j) == pol(i) or pol(i) is None or pol(j) is None)} if i in OF else set()
        if g:
            co.append((x['colloquial'], c, g))
    return ts, co


def recall_at(qv, cands_list, golds, E, ks=(1, 3, 10)):
    hit = {k: 0 for k in ks}
    for v, cand, g in zip(qv, cands_list, golds):
        cand = list(cand)
        s = E[cand] @ v
        rk = [cand[k] for k in np.argsort(-s)]
        for k in ks:
            hit[k] += bool(g & set(rk[:k]))
    n = len(golds)
    return {'n': n, **{f'recall@{k}': round(hit[k] / n, 3) for k in ks}}


stu.eval()
with torch.no_grad():
    ts, co = build_eval()
    ALL = [QA[i][1] for i in DOC]
    E_stu = np.concatenate([stu(ALL[k:k + 512]).cpu().numpy() for k in range(0, len(ALL), 512)])
    idx = {i: k for k, i in enumerate(DOC)}
    Ec = E_stu
    res = {}
    qv = stu([QA[i][1] for i, _, _ in ts]).cpu().numpy()
    res['time_split'] = recall_at(qv, [[idx[j] for j in c] for _, c, _ in ts], [{idx[j] for j in g} for _, _, g in ts], Ec)
    qv = stu([t for t, _, _ in co]).cpu().numpy()
    res['colloquial'] = recall_at(qv, [[idx[j] for j in c] for _, c, _ in co], [{idx[j] for j in g} for _, _, g in co], Ec)
print(json.dumps(res, ensure_ascii=False, indent=1))

if not a.tiny:
    RUN = os.path.join(HERE, 'runs', 'distill_' + a.name)
    os.makedirs(RUN, exist_ok=True)
    W = stu.emb.weight.detach().cpu().numpy()
    Pw = stu.proj.weight.detach().cpu().numpy(); Pb = stu.proj.bias.detach().cpu().numpy()
    np.savez(os.path.join(RUN, 'student.npz'), emb=W, pw=Pw, pb=Pb, corpus=E_stu.astype(np.float32),
             corpus_ids=np.array(DOC), buckets=np.array([a.buckets]), dim=np.array([a.dim]))
    json.dump({'args': vars(a), 'result': res, 'teacher': a.teacher, 'n_train': N},
              open(os.path.join(RUN, 'metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('saved', RUN)
