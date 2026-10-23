"""E52: our own 「AI 의견」 model — a small open LLM fine-tuned (QLoRA) to answer rule questions the way the official Q&A does,
from the evidence the server already finds (card text + nearest older official Q&A with their answers). No external API.

Data: train/data/{yesno,explain}_{train,valid,test}.jsonl from export_dataset.py (time split: test = newest products,
neighbours are older products only, never the item itself). Confirmed rulings (server/judge.db) can be added with --rulings.
Target = the official answer text (「네, …」 / 「아니요, …」 / explanation).

Report (train/runs/gen_<name>/metrics.json):
  * yes/no accuracy on the newest products, read from the generated first word, and coverage at 95 / 97 / 98 %
    using the first-token probability P(네) vs P(아니요) as confidence (thresholds chosen on valid, applied to test);
  * a sample of generated explanations (test_samples.json) to read by eye.
Output: train/runs/gen_<name>/gen_<name>_adapter.zip (LoRA adapter, tens of MB) + .sha256 — publish it as a GitHub release asset;
  the server PC installs it with `python server/fetch_ai_model.py <url> <sha256>` (base model comes from Hugging Face).

GPU PC (GTX 1660 SUPER 6GB):
  pip install -r train/requirements.txt peft bitsandbytes accelerate
  python train/train_gen.py                                   # Qwen/Qwen2.5-1.5B-Instruct, QLoRA 4-bit, 2 epochs
  python train/train_gen.py --model Qwen/Qwen2.5-3B-Instruct --max_len 1024 --name q3b   # better Korean, tighter on 6 GB
CPU smoke test:  python train/train_gen.py --tiny
"""
import argparse, json, os, random, re, sqlite3, time
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser()
ap.add_argument('--model', default='Qwen/Qwen2.5-1.5B-Instruct')
ap.add_argument('--epochs', type=float, default=2)
ap.add_argument('--lr', type=float, default=2e-4)
ap.add_argument('--bs', type=int, default=1)
ap.add_argument('--grad_accum', type=int, default=16)
ap.add_argument('--max_len', type=int, default=1280)
ap.add_argument('--k', type=int, default=4, help='nearest older official Q&A (with answers) in the prompt')
ap.add_argument('--lora_r', type=int, default=16)
ap.add_argument('--no_4bit', action='store_true', help='plain LoRA in fp16/fp32 (CPU, or a GPU with room)')
ap.add_argument('--rulings', action='store_true', help='add confirmed rulings from server/judge.db to train')
ap.add_argument('--eval_n', type=int, default=0, help='limit test items for a quick run (0 = all)')
ap.add_argument('--name', default=None)
ap.add_argument('--tiny', action='store_true')
ap.add_argument('--save_merged', action='store_true', help='also write full merged fp16 weights (several GB)')
a = ap.parse_args()
if a.tiny:
    a.model, a.epochs, a.max_len, a.k, a.no_4bit, a.eval_n, a.grad_accum = 'hf-internal-testing/tiny-random-LlamaForCausalLM', 0.02, 384, 2, True, 6, 1
random.seed(13); np.random.seed(13); torch.manual_seed(13)
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
NAME = a.name or ('tiny' if a.tiny else re.sub(r'[^A-Za-z0-9]+', '_', a.model.split('/')[-1]).lower())
RUN = os.path.join(HERE, 'runs', 'gen_' + NAME); os.makedirs(RUN, exist_ok=True)

import sys; sys.path.insert(0, ROOT)
from gen_prompt import SYSTEM, clean, prompt as _prompt
T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8')); QA = T['qa']
prompt = lambda x: _prompt(x, QA, a.k)


def load(split):
    out = []
    for kind in ('yesno', 'explain'):
        p = os.path.join(HERE, 'data', f'{kind}_{split}.jsonl')
        if os.path.exists(p):
            out += [dict(json.loads(l), kind=kind) for l in open(p, encoding='utf-8')]
    return out


train, valid, test = load('train'), load('valid'), [x for x in load('test') if x['kind'] == 'yesno']
if a.rulings and os.path.exists(os.path.join(ROOT, 'server', 'judge.db')):
    c = sqlite3.connect(os.path.join(ROOT, 'server', 'judge.db'))
    for (d,) in c.execute('select doc from rulings'):
        d = json.loads(d)
        if not d.get('summary'): continue
        head = '네, ' if d.get('ans') == 1 else '아니요, ' if d.get('ans') == 0 else ''
        train.append({'card': d.get('card'), 'card_name': '', 'question': d['q'], 'effect': '', 'card_text': '',
                      'neighbours': [], 'answer': head + d['summary'], 'kind': 'ruling'})
if a.tiny: train, valid = train[:24], [x for x in valid if x['kind'] == 'yesno'][:6]
print('train', len(train), 'valid', len(valid), 'test (yes/no)', len(test), 'device', dev)

from transformers import AutoTokenizer, AutoModelForCausalLM
tok = AutoTokenizer.from_pretrained(a.model)
if tok.pad_token is None: tok.pad_token = tok.eos_token
if not getattr(tok, 'chat_template', None):   # tiny test model has none
    tok.chat_template = "{% for m in messages %}<|{{ m['role'] }}|>\n{{ m['content'] }}\n{% endfor %}{% if add_generation_prompt %}<|assistant|>\n{% endif %}"


def chat(x, with_answer):
    msgs = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt(x)}]
    p = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    return p, (clean(x['answer'])[:600] + tok.eos_token if with_answer else '')


def encode(x):
    p, ans = chat(x, True)
    pi = tok(p, add_special_tokens=False)['input_ids']; ai = tok(ans, add_special_tokens=False)['input_ids']
    pi = pi[-(a.max_len - len(ai)):] if len(pi) + len(ai) > a.max_len else pi    # keep the answer, trim the prompt's head
    ids = (pi + ai)[:a.max_len]
    return {'input_ids': ids, 'labels': ([-100] * len(pi) + ai)[:a.max_len]}


kw = {}
if dev == 'cuda' and not a.no_4bit:
    from transformers import BitsAndBytesConfig
    kw['quantization_config'] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.float16,
                                                   bnb_4bit_use_double_quant=True)
model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float16 if dev == 'cuda' else torch.float32, **kw).to(dev) \
    if not kw else AutoModelForCausalLM.from_pretrained(a.model, device_map={'': 0}, **kw)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
if kw: model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
elif dev == 'cuda': model.gradient_checkpointing_enable()
targets = [n for n in ('q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj')
           if any(m.endswith(n) for m, _ in model.named_modules())] or ['q_proj', 'v_proj']
model = get_peft_model(model, LoraConfig(r=a.lora_r, lora_alpha=2 * a.lora_r, lora_dropout=0.05, target_modules=targets, task_type='CAUSAL_LM'))
model.print_trainable_parameters()

# ---------- train (plain loop: one dependency less than Trainer/TRL) ----------
data = [encode(x) for x in train]
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr)
steps = max(1, int(len(data) * a.epochs / (a.bs * a.grad_accum)))
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / max(1, steps // 20)) * max(0.0, 1 - s / steps))
scaler = torch.cuda.amp.GradScaler(enabled=(dev == 'cuda' and not kw))
model.train(); t0 = time.time(); step = 0; it = 0; losses = []
while step < steps:
    random.shuffle(data)
    for b in range(0, len(data), a.bs):
        batch = data[b:b + a.bs]; L = max(len(x['input_ids']) for x in batch)
        ids = torch.tensor([x['input_ids'] + [tok.pad_token_id] * (L - len(x['input_ids'])) for x in batch], device=dev)
        lab = torch.tensor([x['labels'] + [-100] * (L - len(x['labels'])) for x in batch], device=dev)
        att = (torch.arange(L, device=dev)[None, :] < torch.tensor([len(x['input_ids']) for x in batch], device=dev)[:, None]).long()
        with torch.autocast(device_type='cuda', dtype=torch.float16, enabled=(dev == 'cuda')):
            loss = model(input_ids=ids, attention_mask=att, labels=lab).loss / a.grad_accum
        scaler.scale(loss).backward(); losses.append(loss.item() * a.grad_accum); it += 1
        if it % a.grad_accum == 0:
            scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt); scaler.update(); opt.zero_grad(); sched.step(); step += 1
            if step % 20 == 0 or step == steps:
                print(f'step {step}/{steps} loss {np.mean(losses[-20 * a.grad_accum:]):.3f} {time.time() - t0:.0f}s', flush=True)
            if step >= steps: break
model.eval()

# ---------- evaluate: yes/no from the first generated word, confidence from P(네) vs P(아니요) ----------
YES = [t for t in {tok('네', add_special_tokens=False)['input_ids'][0], tok('예', add_special_tokens=False)['input_ids'][0]}]
NO = [tok('아니요', add_special_tokens=False)['input_ids'][0], tok('아니', add_special_tokens=False)['input_ids'][0]]


@torch.no_grad()
def judge(x, gen=False):
    p, _ = chat(x, False)
    ids = tok(p, add_special_tokens=False, return_tensors='pt')['input_ids'][:, -a.max_len:].to(dev)
    logits = model(input_ids=ids).logits[0, -1].float().softmax(-1)
    py, pn = float(logits[YES].sum()), float(logits[NO].sum())
    out = None
    if gen:
        g = model.generate(input_ids=ids, max_new_tokens=160, do_sample=False, pad_token_id=tok.pad_token_id)
        out = tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True)
    return py / ((py + pn) or 1), out


def scored(items):
    rows = []
    for x in items:
        p, _ = judge(x)
        ans = int(p >= 0.5); rows.append({'p': p, 'conf': max(p, 1 - p), 'ok': int(ans == x['label']), 'product': x.get('product')})
    return rows


def coverage(rows, thr):
    s = [r for r in rows if r['conf'] >= thr]
    return {'thr': round(thr, 4), 'answered': len(s), 'share': round(len(s) / max(1, len(rows)), 4), 'acc': round(np.mean([r['ok'] for r in s]), 4) if s else None}


vrows = scored([x for x in valid if x['kind'] == 'yesno'])
trows = scored(test[:a.eval_n] if a.eval_n else test)
res = {'model': a.model, 'name': NAME, 'train': len(train), 'test': len(trows), 'acc_all': round(np.mean([r['ok'] for r in trows]), 4), 'at': {}}
for target in (0.95, 0.97, 0.98):
    cand = sorted({r['conf'] for r in vrows}, reverse=True); thr = 1.01
    for t in cand:
        s = [r for r in vrows if r['conf'] >= t]
        if len(s) >= 10 and np.mean([r['ok'] for r in s]) >= target: thr = t
    res['at'][str(target)] = coverage(trows, thr)       # threshold from valid, measured on test
print(json.dumps(res, ensure_ascii=False, indent=1))
samples = []
for x in random.sample(test, min(12, len(test))):
    p, out = judge(x, gen=True)
    samples.append({'card': x['card'], 'q': x['question'], 'official': clean(x['answer'])[:300], 'generated': out, 'p_yes': round(p, 3)})
json.dump(res, open(os.path.join(RUN, 'metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(samples, open(os.path.join(RUN, 'test_samples.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- save: the LoRA adapter (tens of MB) — the server downloads the public base model itself and merges (E52) ----------
import hashlib, shutil, zipfile
AD = os.path.join(RUN, 'adapter')
model.save_pretrained(AD); tok.save_pretrained(AD)
json.dump({'base_model': a.model, 'name': NAME, 'k': a.k, 'max_len': a.max_len, 'metrics': res, 'trained_at': time.strftime('%Y-%m-%d %H:%M')},
          open(os.path.join(AD, 'gen_info.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ZIP = os.path.join(RUN, f'gen_{NAME}_adapter.zip')
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir(AD): z.write(os.path.join(AD, f), f)
h = hashlib.sha256(open(ZIP, 'rb').read()).hexdigest().upper()
open(ZIP + '.sha256', 'w').write(h + chr(10))
print('adapter zip', ZIP, f'{os.path.getsize(ZIP) / 1e6:.1f} MB', 'sha256', h)
if a.save_merged and not a.tiny:   # optional: full fp16 weights (GBs) for a machine without internet
    from peft import PeftModel
    base = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float16)
    merged = PeftModel.from_pretrained(base, AD).merge_and_unload()
    merged.save_pretrained(os.path.join(RUN, 'merged'), safe_serialization=True); tok.save_pretrained(os.path.join(RUN, 'merged'))
    print('saved', os.path.join(RUN, 'merged'))
print('done')
