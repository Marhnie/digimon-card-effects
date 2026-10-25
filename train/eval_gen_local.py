"""E52: measure an installed AI-opinion model (server/ai_local_model) on the time split, on this CPU PC.
Same prompt and evidence as training (gen_prompt.py + export_dataset neighbours). Confidence = P(네) vs P(아니요) at the first token.
  python train/eval_gen_local.py [N]  -> paper/results/gen_local_eval.json"""
import json, os, sys, time, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'server'))
import ai_opinion as A
from gen_prompt import SYSTEM, prompt
T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8')); QA = T['qa']
L = A.LOCAL; L.load(); torch = L.torch
N = int(sys.argv[1]) if len(sys.argv) > 1 else 0
test = [json.loads(l) for l in open(os.path.join(ROOT, 'train', 'data', 'yesno_test.jsonl'), encoding='utf-8')]
valid = [json.loads(l) for l in open(os.path.join(ROOT, 'train', 'data', 'yesno_valid.jsonl'), encoding='utf-8')]
if N: test, valid = test[:N], valid[:N]


@torch.no_grad()
def p_yes(x):
    p = L.tok.apply_chat_template([{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt(x, QA, L.k)}], tokenize=False, add_generation_prompt=True)
    ids = L.tok(p, add_special_tokens=False, return_tensors='pt')['input_ids'][:, -L.max_len:]
    pr = L.model(input_ids=ids).logits[0, -1].float().softmax(-1)
    py, pn = float(pr[L.yes].sum()), float(pr[L.no].sum())
    return py / ((py + pn) or 1)


def rows(items):
    out = []
    for k, x in enumerate(items):
        p = p_yes(x); out.append({'p': p, 'conf': max(p, 1 - p), 'ok': int((p >= .5) == bool(x['label']))})
        if k % 100 == 0: print(k, len(items), flush=True)
    return out


t0 = time.time(); V = rows(valid); R = rows(test)
res = {'model': os.path.basename(os.path.normpath(A.LOCAL_DIR)), 'n_test': len(R), 'acc_all': round(np.mean([r['ok'] for r in R]), 4),
       'majority_baseline': round(max(np.mean([x['label'] for x in test]), 1 - np.mean([x['label'] for x in test])), 4), 'at': {}, 'sec': round(time.time() - t0)}
for target in (0.9, 0.95, 0.97):
    thr = 1.01
    for t in sorted({r['conf'] for r in V}, reverse=True):
        s = [r for r in V if r['conf'] >= t]
        if len(s) >= 10 and np.mean([r['ok'] for r in s]) >= target: thr = t
    s = [r for r in R if r['conf'] >= thr]
    res['at'][str(target)] = {'thr': round(thr, 4), 'answered': len(s), 'acc': round(np.mean([r['ok'] for r in s]), 4) if s else None}
print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open(os.path.join(ROOT, 'paper', 'results', 'gen_local_eval.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
