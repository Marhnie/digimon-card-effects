"""E53: run a translator adapter (train_gen.py --task translate) on this CPU PC over the colloquial test set,
then judge the translations with tests/tdec.js (TDEC_SET=<out>).
  python train/translate_local.py <adapter.zip or folder> [out.json]"""
import json, os, sys, tempfile, zipfile, re, time
import torch
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from gen_prompt import TSYSTEM, tprompt
src = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'net', 'translations_local.json')
d = src
if src.endswith('.zip'):
    d = tempfile.mkdtemp(); zipfile.ZipFile(src).extractall(d)
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
info = json.load(open(os.path.join(d, 'gen_info.json'), encoding='utf-8'))
tok = AutoTokenizer.from_pretrained(d)
model = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(info['base_model'], torch_dtype=torch.bfloat16), d).merge_and_unload().eval()
test = [json.loads(l) for l in open(os.path.join(ROOT, 'train', 'data', 'translate_test.jsonl'), encoding='utf-8')]
res = []; t0 = time.time()
for k, x in enumerate(test):
    p = tok.apply_chat_template([{'role': 'system', 'content': TSYSTEM}, {'role': 'user', 'content': tprompt(x)}], tokenize=False, add_generation_prompt=True)
    ids = tok(p, add_special_tokens=False, return_tensors='pt')['input_ids']
    with torch.no_grad():
        g = model.generate(input_ids=ids, max_new_tokens=160, do_sample=False, pad_token_id=tok.pad_token_id or tok.eos_token_id)
    t = tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True).strip().split('\n')[0]
    res.append({'id': x['id'], 'card': x['card'], 'source': x['source'], 'official': x['target'], 'translated': t})
    if k % 25 == 0: print(k, len(test), f'{time.time() - t0:.0f}s', flush=True)
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved', out, f'{time.time() - t0:.0f}s')
