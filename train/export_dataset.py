"""Export the GPU-training datasets from test_data4.json (stdlib only).

Time split, same as engine_lite.py / E19: products BT22/BT23/BT24/EX9/EX10/ST21/ST22 = test, everything older = pool.
The pool is split into train / valid by card (10 % of cards, fixed seed) so valid has no card overlap with train.

Every item carries its k nearest *pool* Q&A (character-bigram Jaccard over the question, like the judge helper),
with their official answers, so a model can learn "answer from precedents" the way the page does. Neighbours never
include the item itself or near-duplicates of it (Jaccard > 0.8, or > 0.55 on the same card), so train items do not
see their own answer.

Outputs (train/data/):
  yesno_{train,valid,test}.jsonl   label 1 = 네, 0 = 아니요 (official answer)
  explain_{train,valid,test}.jsonl  non-yes/no questions with the official answer text (retrieval / reranking)
  engine_test.json                 the browser engine's test predictions (net/engine_py_test.json) for comparison
"""
import json, os, re, random, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('EXPORT_OUT') or os.path.join(ROOT, 'train', 'data')
K = int(os.environ.get('K', 8))
# EXPORT_NEW=BT25 (comma list): the pre-registered test (paper/results/preregistered_rules.json R2) — that set is the test, everything older the pool
NEW = set(os.environ['EXPORT_NEW'].split(',')) if os.environ.get('EXPORT_NEW') else {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}

T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))
QA, UN, CARDS = T['qa'], T['units'], T['cards']
# English card text from the DCGO card scripts (MIT) — fills the newest products, which have no Korean card data here
EN = json.load(open(os.path.join(ROOT, 'train', 'ref', 'dcgo_cards_en.json'), encoding='utf-8'))
F = T['form']
INTENTS = [(n, re.compile(p) if p else None) for n, p in F['intents']]
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
clean = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s or '').strip()
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))


def intent(q):
    for n, r in INTENTS:
        if r and r.search(q):
            return n
    return '기타'


def jac(a, b):
    x = len(a & b)
    return x / ((len(a) + len(b) - x) or 1)


by_card = collections.defaultdict(list)
for k, u in enumerate(UN):
    by_card[u[0]].append(k)

items = []
for i, r in enumerate(QA):
    if not r[0]:
        continue
    u = r[3] if r[3] is not None else -1
    items.append({
        'id': i, 'card': r[0], 'card_name': (CARDS.get(r[0]) or [''])[0], 'product': prod(r[0]),
        'effect': UN[u][3] if u >= 0 else '',
        'card_text': ' / '.join(UN[k][3] for k in by_card.get(r[0], []))[:1500],
        'card_text_en': ((EN.get(r[0]) or {}).get('text') or '').replace('\n', ' ')[:1500],
        'card_name_en': (EN.get(r[0]) or {}).get('name', ''),
        'question': r[1], 'answer': clean(r[2]), 'label': r[8], 'neg': r[9], 'intent': intent(r[1]),
        'pattern': UN[u][10] if u >= 0 else None,
    })

pool = [x for x in items if x['product'] not in NEW]
test = [x for x in items if x['product'] in NEW]
cards = sorted({x['card'] for x in pool})
random.Random(13).shuffle(cards)
valid_cards = set(cards[:len(cards) // 10])
for x in pool:
    x['split'] = 'valid' if x['card'] in valid_cards else 'train'
for x in test:
    x['split'] = 'test'

BG = {x['id']: bg(x['question']) for x in items}
# neighbours: from pool items of the training side only (valid/test never borrow valid answers either)
cand = [x for x in pool if x['split'] == 'train']


def neighbours(x, want_yesno):
    A = BG[x['id']]
    sc = []
    for y in cand:
        if y['id'] == x['id'] or (want_yesno and y['label'] < 0) or (not want_yesno and y['label'] >= 0):
            continue
        s = jac(A, BG[y['id']])
        if s > 0.8 or (y['card'] == x['card'] and s > 0.55 and x['split'] == 'train'):
            continue  # near-duplicate of a training item → would leak its own answer
        if s < 0.1:
            continue
        sc.append((s, y))
    sc.sort(key=lambda t: -t[0])
    out = []
    for s, y in sc[:K]:
        n = {'id': y['id'], 'card': y['card'], 'sim': round(s, 3), 'question': y['question'], 'same_card': y['card'] == x['card'],
             'same_pattern': x['pattern'] is not None and y['pattern'] == x['pattern']}
        if want_yesno:
            # align polarity: a precedent asked the opposite way ("…할 수 없나요") flips
            n['label'] = y['label'] ^ (y['neg'] ^ x['neg'])
        else:
            n['answer'] = y['answer']
        out.append(n)
    return out


os.makedirs(OUT, exist_ok=True)
stats = collections.Counter()
files = {}
for x in items:
    yesno = x['label'] >= 0
    rec = dict(x)
    rec['neighbours'] = neighbours(x, yesno)
    name = f"{'yesno' if yesno else 'explain'}_{x['split']}.jsonl"
    files.setdefault(name, []).append(rec)
    stats[name] += 1
for name, recs in files.items():
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
eng = os.path.join(ROOT, 'net', 'engine_py_test.json')
if os.path.exists(eng):
    json.dump(json.load(open(eng)), open(os.path.join(OUT, 'engine_test.json'), 'w'))
print(dict(stats))
