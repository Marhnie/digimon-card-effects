"""E39: turn real questions people asked the server into training/test pairs (no scraping — our own service only).

  python train/export_logs.py [server/judge.db]  ->  train/data/log_pairs.jsonl
Each row: q (as typed), cards, label source, answer (0/1 or None), the official Q&A the page matched (top hits).
Label quality: 'ruling' (judge-confirmed) > 'report' (user report, agreed with a judge answer) > 'decided' (page decided, unconfirmed).
Only 'ruling' and agreed 'report' rows are safe as gold labels; 'decided' rows are for hard-negative mining / eval of coverage.
"""
import json, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'server', 'judge.db'))
out = []
for (d,) in db.execute('select doc from rulings'):
    d = json.loads(d); out.append({'q': d.get('q'), 'cards': [d.get('card'), d.get('others')], 'label': 'ruling', 'ans': d.get('ans'), 'unit': d.get('unit')})
for (d,) in db.execute('select doc from reports'):
    d = json.loads(d); out.append({'q': d.get('q'), 'cards': [d.get('card'), d.get('others')], 'label': 'report' if d.get('agreed') else 'report_disputed',
                                   'ans': d.get('ans'), 'unit': d.get('unit'), 'src': d.get('src')})
for (d,) in db.execute('select doc from verdicts'):
    d = json.loads(d); out.append({'q': d.get('q'), 'cards': d.get('cards'), 'label': 'decided' if d.get('level') not in ('pending', None) else 'pending',
                                   'by': d.get('level'), 'ans': d.get('ans'), 'top': d.get('top')})
os.makedirs(os.path.join(ROOT, 'train', 'data'), exist_ok=True)
p = os.path.join(ROOT, 'train', 'data', 'log_pairs.jsonl')
with open(p, 'w', encoding='utf-8') as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + '\n')
from collections import Counter
print(len(out), 'rows ->', p, dict(Counter(r['label'] for r in out)))
