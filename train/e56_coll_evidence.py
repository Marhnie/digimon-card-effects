"""E56: E55's colloquial R2 run took its two evidence Q&A from export_dataset, which picks them with the OFFICIAL question wording.
Here the evidence comes the way the server gets it: the colloquial question itself goes to the server's search (running main, so no
BT25 Q&A in its corpus). Same frozen model and threshold; exploratory (unofficial BT25 translation), not the pre-registered test.
  python train/e56_coll_evidence.py <copy data dir> <r2_coll.json>  -> paper/results/e56_coll_server_evidence.json"""
import json, os, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THR = 0.9873
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'server'))
import ai_opinion as A
from gen_prompt import SYSTEM, prompt
data, r2 = sys.argv[1], sys.argv[2]
QA = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))['qa']
L = A.LOCAL; L.load()
assert (L.k, L.max_len, L.layout) == (2, 1024, 2), (L.k, L.max_len, L.layout)


def search(q):
    r = urllib.request.Request('http://127.0.0.1:8787/api/search', json.dumps({'q': q, 'k': 3}).encode(), {'content-type': 'application/json'})
    return [h['i'] for h in json.load(urllib.request.urlopen(r, timeout=300))['hits']][:8]   # k*3 = 9 hits; the server asks for 8


items = {}
for l in open(os.path.join(data, 'yesno_test.jsonl'), encoding='utf-8'):
    x = json.loads(l); items[x['id']] = x
old = {r['id']: r for r in json.load(open(r2, encoding='utf-8'))['rows']}
rows = []
for n, i in enumerate(old):
    x = dict(items[i]); ids = [j for j in search(x['question']) if QA[j][0]][:L.k]
    x['neighbours'] = [{'id': j, 'card': QA[j][0], 'question': QA[j][1]} for j in ids]
    _, p = L.answer(SYSTEM, prompt(x, QA, L.k, L.layout), min_conf=1.1)
    rows.append({'id': i, 'card': x['card'], 'p': round(p, 4), 'ok': int((p >= .5) == bool(x['label'])), 'old_p': old[i]['p'], 'evidence': ids})
    if n % 10 == 0:
        print(n, len(old), flush=True)
        json.dump(rows, open(os.path.join(ROOT, 'net', 'e56_partial.json'), 'w'))
ans = [r for r in rows if max(r['p'], 1 - r['p']) >= THR]
res = {'held': len(rows), 'answered': len(ans), 'correct': sum(r['ok'] for r in ans), 'all_acc': round(sum(r['ok'] for r in rows) / len(rows), 4),
       'old_answered': sum(max(r['old_p'], 1 - r['old_p']) >= THR for r in rows), 'rows': rows}
print({k: v for k, v in res.items() if k != 'rows'})
json.dump(res, open(os.path.join(ROOT, 'paper', 'results', 'e56_coll_server_evidence.json'), 'w', encoding='utf-8'), indent=1)
