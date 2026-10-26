"""E52: confirmed rulings (server/judge.db) -> jsonl for train_gen.py --rulings_file on the GPU PC (which has no judge.db).
Rulings on the newest products (the time-split test set) are left out by default so the test stays honest; --all keeps them
(for a serving-only model whose test numbers are then not comparable).
  python train/export_rulings.py <out.jsonl> [--all]
The file holds community wording: keep it in the private model repo, never the public one."""
import json, os, re, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
out, keep_all = sys.argv[1], '--all' in sys.argv
cards = {c['no']: c for c in json.load(open(os.path.join(ROOT, 'cards.json'), encoding='utf-8'))}
rows, skipped = [], 0
for (d,) in sqlite3.connect(os.path.join(ROOT, 'server', 'judge.db')).execute('select doc from rulings'):
    d = json.loads(d)
    if not d.get('summary') or not d.get('q'): continue
    nos = [d.get('card') or ''] + [x for x in (d.get('others') or '').split(',') if x]
    if not keep_all and any(prod(n) in NEW for n in nos): skipped += 1; continue
    c = cards.get(nos[0]) or {}
    head = '네, ' if d.get('ans') == 1 else '아니요, ' if d.get('ans') == 0 else ''
    rows.append({'card': nos[0], 'card_name': c.get('name', ''), 'question': d['q'], 'effect': '',
                 'card_text': (c.get('상단 텍스트', '') + ' / 진화원: ' + (c.get('하단 텍스트', '') or '-')) if c else '',
                 'neighbours': [], 'answer': head + d['summary']})
with open(out, 'w', encoding='utf-8') as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('rulings', len(rows), '| left out (newest products)', skipped, '->', out)
