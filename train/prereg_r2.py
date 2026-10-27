"""Pre-registered rule R2 (paper/results/preregistered_rules.json): score the frozen own model on the questions the page holds,
on a product set that did not exist when the rule was fixed (BT25 or the next set). Nothing here may be tuned on that set.
Steps once the set's official Q&A are in test_data4.json:
  1. EXPORT_NEW=BT25 EXPORT_OUT=train/data_bt25 python train/export_dataset.py
  2. TDEC_NEW=BT25 TDEC_FULL=1 TDEC_DUMP=net/tdec_bt25.json node tests/tdec.js
  3. python train/prereg_r2.py <gen_q15_v2_adapter.zip> train/data_bt25 net/tdec_bt25.json  -> paper/results/prereg_r2_<set>.json
The model runs on CPU (about 40 s per question on the server PC); only held questions are scored."""
import hashlib, json, os, sys, tempfile, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHA, THR = '8C0894D6B363119A9078C7C9F215043CA7F577A19BCC11EFCE4605BC70FCE6BC', 0.9873
zp, data, dump = sys.argv[1], sys.argv[2], sys.argv[3]
h = hashlib.sha256(open(zp, 'rb').read()).hexdigest().upper()
assert h == SHA, f'not the registered model: {h}'
d = tempfile.mkdtemp(); zipfile.ZipFile(zp).extractall(d)
os.environ['AI_LOCAL_MODEL'] = d
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'server'))
import ai_opinion as A
from gen_prompt import SYSTEM, prompt
QA = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))['qa']
L = A.LOCAL; L.load()
assert (L.k, L.max_len, L.layout) == (2, 1024, 2), (L.k, L.max_len, L.layout)
DEC = {x['i']: x for x in json.load(open(dump, encoding='utf-8'))}
items = [json.loads(l) for l in open(os.path.join(data, 'yesno_test.jsonl'), encoding='utf-8')]
held = [x for x in items if x['id'] in DEC and not DEC[x['id']]['by']]
rows = []
for n, x in enumerate(held):
    _, p = L.answer(SYSTEM, prompt(x, QA, L.k, L.layout), min_conf=1.1)   # first-token probability only
    rows.append({'id': x['id'], 'card': x['card'], 'p': round(p, 4), 'ok': int((p >= .5) == bool(x['label']))})
    if n % 20 == 0: print(n, len(held), flush=True)
ans = [r for r in rows if max(r['p'], 1 - r['p']) >= THR]
acc = sum(r['ok'] for r in ans) / len(ans) if ans else None
res = {'rule': 'R2-own-model-held', 'set': sorted({x['product'] for x in items}), 'test_yesno': len(items), 'held': len(held),
       'answered': len(ans), 'acc': round(acc, 4) if acc is not None else None,
       'success': bool(acc is not None and acc >= 0.97 and len(ans) >= 10), 'rows': rows}
print({k: v for k, v in res.items() if k != 'rows'})
json.dump(res, open(os.path.join(ROOT, 'paper', 'results', f"prereg_r2_{'_'.join(res['set'])}.json"), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
