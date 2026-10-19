"""Cross-encoder yes/no judge with precedents in the input, for a GPU machine.

Input  = [효과] effect text (Korean, or English DCGO text when missing) [질문] question
         [선례] up to K nearest older official Q&A, each "질문 → 네/아니요"
Label  = official answer (1 = 네, 0 = 아니요). Time split from export_dataset.py (test = newest products).

The goal is the same as the browser engine: answer WITHOUT an LLM and only when confident, so the report is
coverage at a fixed precision (95 / 97 / 98 / 99 %) on the newest products, next to the current engine.

Usage:
  python train/train_yesno.py --model klue/roberta-large --epochs 4 --bs 16 --lr 1.5e-5
  python train/train_yesno.py --model klue/roberta-base --max_len 384            # lighter
  python train/train_yesno.py --model monologg/koelectra-base-v3-discriminator
  python train/train_yesno.py --tiny                                             # CPU smoke test (few steps)
Outputs (train/runs/<name>/): metrics.json, test_pred.json {id: [p_yes, conf, label]}, the fine-tuned model.
"""
import argparse, json, os, random, time
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoConfig, AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--model', default='klue/roberta-large')
ap.add_argument('--epochs', type=int, default=4)
ap.add_argument('--bs', type=int, default=16)
ap.add_argument('--grad_accum', type=int, default=1)
ap.add_argument('--lr', type=float, default=1.5e-5)
ap.add_argument('--max_len', type=int, default=512)
ap.add_argument('--k', type=int, default=5, help='precedents in the input (0 = question only)')
ap.add_argument('--seed', type=int, default=13)
ap.add_argument('--fp16', action='store_true', help='mixed precision (default on when CUDA is available)')
ap.add_argument('--name', default=None)
ap.add_argument('--tiny', action='store_true', help='CPU smoke test: tiny model, 64 examples, 1 epoch')
a = ap.parse_args()
if a.tiny:
    a.model, a.epochs, a.bs, a.max_len, a.k = 'hf-internal-testing/tiny-random-bert', 1, 8, 128, 2
random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
use_amp = dev == 'cuda'
name = a.name or (a.model.split('/')[-1] + f'_k{a.k}' + ('_tiny' if a.tiny else ''))
RUN = os.path.join(HERE, 'runs', name); os.makedirs(RUN, exist_ok=True)


def load(split):
    p = os.path.join(HERE, 'data', f'yesno_{split}.jsonl')
    rows = [json.loads(l) for l in open(p, encoding='utf-8')]
    return rows[:64] if a.tiny else rows


def text(r):
    eff = r['effect'] or r.get('card_text') or r.get('card_text_en') or ''
    prec = ' '.join(f"[선례{'·같은카드' if n['same_card'] else ''}] {n['question']} → {'네' if n['label'] else '아니요'}" for n in r['neighbours'][:a.k])
    return f"[효과] {eff}", f"[질문] {r['question']} {prec}".strip()


class DS(Dataset):
    def __init__(self, rows): self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, i): return self.rows[i]


tok = AutoTokenizer.from_pretrained(a.model)
# RoBERTa-family models (e.g. klue/roberta-*) have type_vocab_size=1, but the tokenizer still emits token_type_ids=1
# for the second segment → CUDA index-out-of-range. Drop them when the model has no segment embeddings to use.
USE_TT = getattr(AutoConfig.from_pretrained(a.model), 'type_vocab_size', 2) > 1


def collate(rows):
    e, q = zip(*[text(r) for r in rows])
    # truncate the effect first: the question + precedents carry most of the signal
    enc = tok(list(e), list(q), truncation='only_first' if not a.tiny else True, max_length=a.max_len, padding=True, return_tensors='pt')
    if not USE_TT: enc.pop('token_type_ids', None)
    enc['labels'] = torch.tensor([r['label'] for r in rows])
    return enc


def safe_collate(rows):
    try:
        return collate(rows)
    except Exception:  # question+precedents alone longer than max_len → truncate both sides
        e, q = zip(*[text(r) for r in rows])
        enc = tok(list(e), list(q), truncation=True, max_length=a.max_len, padding=True, return_tensors='pt')
        if not USE_TT: enc.pop('token_type_ids', None)
        enc['labels'] = torch.tensor([r['label'] for r in rows]); return enc


tr, va, te = load('train'), load('valid'), load('test')
print(f'train {len(tr)} valid {len(va)} test {len(te)} | model {a.model} | device {dev}')
model = AutoModelForSequenceClassification.from_pretrained(a.model, num_labels=2).to(dev)
dl = DataLoader(DS(tr), batch_size=a.bs, shuffle=True, collate_fn=safe_collate)
opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
steps = max(1, len(dl) * a.epochs // a.grad_accum)
sch = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
scaler = torch.amp.GradScaler('cuda', enabled=use_amp)


@torch.no_grad()
def predict(rows):
    model.eval(); out = []
    for b in DataLoader(DS(rows), batch_size=a.bs * 2, collate_fn=safe_collate):
        b = {k: v.to(dev) for k, v in b.items()}; b.pop('labels')
        with torch.autocast(device_type='cuda', enabled=use_amp):
            lo = model(**b).logits.float()
        out.extend(torch.softmax(lo, -1)[:, 1].cpu().tolist())
    model.train(); return np.array(out)


def selective(p, y):
    """coverage at fixed precision when answering the most confident first"""
    pred = (p > 0.5).astype(int); conf = np.maximum(p, 1 - p); o = np.argsort(-conf)
    ok = (pred[o] == y[o]).astype(float); cum = np.cumsum(ok) / np.arange(1, len(ok) + 1)
    res = {'acc_all': round(float(ok.mean()), 4)}
    for t in (0.95, 0.97, 0.98, 0.99):
        ks = [k for k in range(20, len(o) + 1) if cum[k - 1] >= t]
        res[f'cov@{int(t * 100)}'] = round(max(ks) / len(o), 4) if ks else 0.0
        res[f'thr@{int(t * 100)}'] = round(float(conf[o[max(ks) - 1]]), 4) if ks else None
    return res


best, hist = -1, []
for ep in range(a.epochs):
    t0 = time.time(); tot = 0
    for i, b in enumerate(dl):
        b = {k: v.to(dev) for k, v in b.items()}
        with torch.autocast(device_type='cuda', enabled=use_amp):
            loss = model(**b).loss / a.grad_accum
        scaler.scale(loss).backward(); tot += loss.item()
        if (i + 1) % a.grad_accum == 0:
            scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt); scaler.update(); opt.zero_grad(); sch.step()
    pv = predict(va); yv = np.array([r['label'] for r in va]); m = selective(pv, yv)
    hist.append({'epoch': ep + 1, 'loss': round(tot / len(dl), 4), 'valid': m, 'sec': round(time.time() - t0)})
    print(hist[-1])
    score = m['cov@95'] + m['acc_all']
    if score > best:
        best = score; model.save_pretrained(RUN); tok.save_pretrained(RUN)

model = AutoModelForSequenceClassification.from_pretrained(RUN).to(dev)
pt = predict(te); yt = np.array([r['label'] for r in te])
mt = selective(pt, yt)
# threshold chosen on VALID (honest), applied to test
pv = predict(va); yv = np.array([r['label'] for r in va]); mv = selective(pv, yv)
fixed = {}
for t in (95, 97, 98):
    thr = mv.get(f'thr@{t}')
    if thr is None: continue
    conf = np.maximum(pt, 1 - pt); s = conf >= thr
    fixed[f'valid_thr@{t}'] = {'thr': thr, 'test_coverage': round(float(s.mean()), 4),
                               'test_acc': round(float(((pt > .5).astype(int)[s] == yt[s]).mean()), 4) if s.any() else None}
# comparison with the browser engine on the same test ids (and the union: engine-sure OR model-sure)
eng = {}
ep = os.path.join(HERE, 'data', 'engine_test.json')
if os.path.exists(ep):
    E = json.load(open(ep)); ids = [r['id'] for r in te]
    have = [k for k, i in enumerate(ids) if str(i) in E]
    ep_ = np.array([E[str(ids[k])][0] for k in have]); ec = np.array([E[str(ids[k])][1] for k in have]); ey = yt[have]
    es = ec >= 0.80
    eng = {'engine_cov@thr0.80': round(float(es.mean()), 4), 'engine_acc@thr0.80': round(float((ep_[es] == ey[es]).mean()), 4)}
    thr = mv.get('thr@97')
    if thr is not None:
        mc = np.maximum(pt[have], 1 - pt[have]) >= thr; mp = (pt[have] > .5).astype(int)
        union = es | mc; ans = np.where(es, ep_, mp)
        eng['union_cov'] = round(float(union.mean()), 4); eng['union_acc'] = round(float((ans[union] == ey[union]).mean()), 4)
res = {'args': vars(a), 'history': hist, 'test': mt, 'test_with_valid_threshold': fixed, 'vs_engine': eng}
json.dump(res, open(os.path.join(RUN, 'metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({str(r['id']): [round(float(p), 4), round(float(max(p, 1 - p)), 4), int(r['label'])] for r, p in zip(te, pt)},
          open(os.path.join(RUN, 'test_pred.json'), 'w'))
print(json.dumps({'test': mt, 'fixed': fixed, 'vs_engine': eng}, ensure_ascii=False, indent=1))
