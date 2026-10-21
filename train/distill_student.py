"""Distil the fine-tuned retriever (teacher, E31) into a browser-sized student (E33).

Student = hashed character n-gram bag (FNV-1a of 2- and 3-grams, B buckets) -> mean of a d-dim embedding table -> linear
d -> D (teacher dim) -> L2 normalise. It maps a QUERY into the teacher's space; the official Q&A side is embedded once by the
teacher and shipped as int8 vectors. Inference in the page is plain JS (hash, sum rows, one small matmul) — no library.

Loss = (1 - cos(student(q), teacher(q))) + InfoNCE(student(colloquial q) vs teacher(original q) of the batch, tau 0.05).
Training texts: pool questions (products before BT22, minus the colloquial eval set) and colloquialized variants of them.

Eval (time split / colloquial, same items as train_retriever.py): student-query vs teacher-corpus, next to teacher-query and
the browser 2-gram. Approval: colloquial recall@3 >= 95 % of the teacher's and model files <= 15 MB.

  python train/distill_student.py --teacher train/runs/retriever_base/model            # GPU, eval run (time split honest)
  python train/distill_student.py --teacher train/runs/retriever_base/model --final    # + retrain on ALL Q&A and export for the page
  python train/distill_student.py --tiny                                               # CPU smoke (tiny teacher, few texts)
Export (train/export_qemb/): meta.json, student_emb.i8, student_scale.f32, student_lin.f32, corpus.i8, corpus_ids.json
"""
import argparse, json, os, re, random, sys, collections, time
import numpy as np
import torch, torch.nn as nn, torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument('--teacher', default=os.path.join(HERE, 'runs', 'retriever_base', 'model'))
ap.add_argument('--buckets', type=int, default=32768)
ap.add_argument('--dim', type=int, default=256)
ap.add_argument('--aug', type=int, default=8, help='colloquial variants per question')
ap.add_argument('--epochs', type=int, default=12)
ap.add_argument('--bs', type=int, default=256)
ap.add_argument('--lr', type=float, default=2e-3)
ap.add_argument('--final', action='store_true', help='after the eval run, retrain on all Q&A and export for the page')
ap.add_argument('--tiny', action='store_true')
a = ap.parse_args()
if a.tiny:
    a.teacher, a.buckets, a.dim, a.aug, a.epochs = 'sentence-transformers-testing/stsb-bert-tiny-safetensors', 4096, 32, 1, 1
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
rng = random.Random(13); torch.manual_seed(13)

NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))
QA = T['qa']; OF = {int(k): v for k, v in T['rg']['of'].items()}
pol = lambda i: (QA[i][8] ^ QA[i][9]) if QA[i][8] >= 0 else None
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
jac = lambda A, B: len(A & B) / ((len(A) + len(B) - len(A & B)) or 1)
CS = json.load(open(os.path.join(ROOT, 'paper', 'results', 'colloquial_test.json'), encoding='utf-8'))['items']
BANNED = {x['qid'] for x in CS}
DOC = [i for i, r in enumerate(QA) if r[0]]
POOL = [i for i in DOC if prod(QA[i][0]) not in NEW and i not in BANNED]
TESTQ = [i for i in DOC if prod(QA[i][0]) in NEW]

# colloquial augmentation: same substitutions as train_retriever.py
SUBS = [(r'【등장 시】', ['등장시', '등장 시', '등시']), (r'【진화 시】', ['진화시', '진화 시']), (r'【어택 시】', ['어택시', '어택 시']),
        (r'【소멸 시】', ['소멸시']), (r'【시큐리티】 ?효과', ['시큐 효과', '시큐리티 효과']), (r'시큐리티', ['시큐', '시큐리티']),
        (r'진화원 효과', ['상속', '진화원 효과', '진화원효과']), (r'《1 드로우》', ['1드로', '1드로우']), (r'배틀 에어리어', ['배틀에어리어', '필드']),
        (r'발휘할 수 있(?:나요|습니까)\?', ['쓸수있어?', '쓸 수 있음?', '발휘돼?', '발휘 가능?']), (r'되나요\?', ['돼?', '되나여', '됨?']),
        (r'있나요\?', ['있음?', '있어?', '잇나여']), (r'무엇인가요\?', ['뭐임?', '머야?']), (r'어떻게', ['어케', '어떻게']),
        (r'(?:하나요|합니까)\?', ['함?', '하냐?', '하나?']), (r'유발되나요\?', ['유발됨?', '유발돼?'])]


def colloquialize(q):
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


# ---- the student's tokenizer: MUST match v3_qemb.js exactly ----
def prep(s):
    return '\u0002' + re.sub(r'\s+', ' ', s.strip()).lower() + '\u0003'


def fnv1a(s):
    h = 0x811c9dc5
    for b in s.encode('utf-8'):
        h ^= b; h = (h * 0x01000193) & 0xffffffff
    return h


def grams(s, B):
    t = prep(s)
    return [fnv1a(t[i:i + n]) % B for n in (2, 3) for i in range(len(t) - n + 1)]


class Student(nn.Module):
    def __init__(s, B, d, D):
        super().__init__(); s.emb = nn.EmbeddingBag(B, d, mode='mean'); s.lin = nn.Linear(d, D)
        nn.init.normal_(s.emb.weight, std=0.1)
    def forward(s, idx, off):
        return F.normalize(s.lin(s.emb(idx, off)), dim=-1)


def batchify(texts, B):
    ids, off = [], []
    for t in texts:
        off.append(len(ids)); g = grams(t, B); ids.extend(g if g else [0])
    return torch.tensor(ids, device=dev), torch.tensor(off, device=dev)


from sentence_transformers import SentenceTransformer
teacher = SentenceTransformer(a.teacher, device=dev)
tenc = lambda xs: teacher.encode(xs, normalize_embeddings=True, batch_size=128, show_progress_bar=False, convert_to_numpy=True)
D = teacher.get_sentence_embedding_dimension()


def train(qids):
    qids = qids[:200] if a.tiny else qids
    orig = [QA[i][1] for i in qids]
    texts, src = [], []
    for k, q in enumerate(orig):
        texts.append(q); src.append(k)
        for _ in range(a.aug):
            texts.append(colloquialize(q)); src.append(k)
    t0 = time.time()
    TQ = torch.tensor(tenc(texts), device=dev)        # teacher(each text): what the student must reproduce
    TO = torch.tensor(tenc(orig), device=dev)         # teacher(original question): the corpus side
    print(f'teacher encoded {len(texts)} texts in {time.time() - t0:.0f}s')
    st = Student(a.buckets, a.dim, D).to(dev)
    opt = torch.optim.Adam(st.parameters(), lr=a.lr)
    src_t = torch.tensor(src, device=dev)
    for ep in range(a.epochs):
        perm = list(range(len(texts))); rng.shuffle(perm); tot = 0
        for b0 in range(0, len(perm), a.bs):
            bi = perm[b0:b0 + a.bs]
            idx, off = batchify([texts[i] for i in bi], a.buckets)
            out = st(idx, off); bi_t = torch.tensor(bi, device=dev)
            l_mse = (1 - (out * TQ[bi_t]).sum(-1)).mean()
            uniq, inv = torch.unique(src_t[bi_t], return_inverse=True)
            logits = out @ TO[uniq].T / 0.05
            l_nce = F.cross_entropy(logits, inv)
            loss = l_mse + 0.5 * l_nce
            opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item() * len(bi)
        print(f'epoch {ep + 1} loss {tot / len(texts):.4f}')
    return st


@torch.no_grad()
def senc(st, xs):
    out = []
    for b0 in range(0, len(xs), 512):
        idx, off = batchify(xs[b0:b0 + 512], a.buckets); out.append(st(idx, off).cpu().numpy())
    return np.concatenate(out)


def build_eval():
    GRP = collections.defaultdict(set)
    for i, g in OF.items(): GRP[g].add(i)
    poolset = set(POOL); ts, co = [], []
    for i in TESTQ:
        g = {j for j in GRP.get(OF.get(i), ()) if j in poolset and (pol(j) == pol(i) or pol(i) is None or pol(j) is None)} if i in OF else set()
        if g: ts.append((QA[i][1], poolset, g))
    bycard = collections.defaultdict(set)
    for i in DOC: bycard[QA[i][0]].add(i)
    for x in CS:
        i = x['qid']; c = (poolset | bycard[x['card']]) - {i}
        g = {j for j in GRP.get(OF.get(i), ()) if j in c and (pol(j) == pol(i) or pol(i) is None or pol(j) is None)} if i in OF else set()
        if g: co.append((x['colloquial'], c, g))
    return {'time_split': ts, 'colloquial': co}


def evaluate(st):
    E = dict(zip(DOC, tenc([QA[i][1] for i in DOC]))); BG = {i: bg(QA[i][1]) for i in DOC}; res = {}
    for name, items in build_eval().items():
        if a.tiny: items = items[:40]
        qs = [t for t, _, _ in items]; SV = senc(st, qs); TV = tenc(qs)
        hit = {m: {1: 0, 3: 0, 10: 0} for m in ('student', 'teacher', 'browser_2gram')}
        for (t, cand, g), sv, tv in zip(items, SV, TV):
            cand = list(cand); M = np.stack([E[j] for j in cand])
            rk = {'student': [cand[k] for k in np.argsort(-(M @ sv))], 'teacher': [cand[k] for k in np.argsort(-(M @ tv))],
                  'browser_2gram': sorted(cand, key=lambda j: -jac(bg(t), BG[j]))}
            for m in hit:
                for k in hit[m]: hit[m][k] += bool(g & set(rk[m][:k]))
        n = len(items)
        res[name] = {'n': n, **{m: {f'recall@{k}': round(v / n, 3) for k, v in h.items()} for m, h in hit.items()}}
    print(json.dumps(res, ensure_ascii=False)); return res


def export(st, out):
    os.makedirs(out, exist_ok=True)
    W = st.emb.weight.detach().cpu().numpy(); sc = np.abs(W).max(1) / 127 + 1e-12
    (np.round(W / sc[:, None]).astype(np.int8)).tofile(os.path.join(out, 'student_emb.i8'))
    sc.astype(np.float32).tofile(os.path.join(out, 'student_scale.f32'))
    lw = st.lin.weight.detach().cpu().numpy().astype(np.float32); lb = st.lin.bias.detach().cpu().numpy().astype(np.float32)
    np.concatenate([lw.T.ravel(), lb]).astype(np.float32).tofile(os.path.join(out, 'student_lin.f32'))   # [d x D] row-major, then bias[D]
    C = tenc([QA[i][1] for i in DOC]); (np.round(np.clip(C, -1, 1) * 127).astype(np.int8)).tofile(os.path.join(out, 'corpus.i8'))
    json.dump(DOC, open(os.path.join(out, 'corpus_ids.json'), 'w'))
    json.dump({'buckets': a.buckets, 'dim': a.dim, 'D': D, 'grams': [2, 3], 'hash': 'fnv1a32-utf8', 'prep': 'lower, collapse spaces, \\u0002..\\u0003',
               'n_corpus': len(DOC), 'teacher': a.teacher}, open(os.path.join(out, 'meta.json'), 'w', encoding='utf-8'))
    # golden vectors so the JS port can be checked bit-for-bit (within int8 rounding)
    probe = ['파피몬 등장시 1드로 쓸수있어?', QA[DOC[0]][1]]
    json.dump({'texts': probe, 'vec': senc(st, probe).round(5).tolist()}, open(os.path.join(out, 'probe.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)) / 1e6
    print('exported', out, f'{size:.1f} MB')
    return size


RUNS = os.path.join(HERE, 'runs', 'distill' + ('_tiny' if a.tiny else '')); os.makedirs(RUNS, exist_ok=True)
st = train(POOL)
res = evaluate(st)
tq = res['colloquial']['teacher']['recall@3'] or 1e-9
ok = res['colloquial']['student']['recall@3'] / tq
out = os.path.join(HERE, 'export_qemb' + ('_tiny' if a.tiny else ''))
size = None
if a.final or a.tiny:
    st_all = train(DOC) if a.final else st     # the page may use every Q&A; the eval above stays the honest number
    size = export(st_all, out)
json.dump({'args': vars(a), 'eval': res, 'student_vs_teacher_colloquial_r3': round(ok, 3), 'export_mb': size,
           'approved': bool(ok >= 0.95 and (size is None or size <= 15))}, open(os.path.join(RUNS, 'metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('student/teacher colloquial recall@3 =', round(ok, 3))
