"""E53: parallel corpus for the question translator — colloquial / community wording (source) -> official Q&A wording (target).
Targets are official questions of OLDER products only; sources are made from them by rules (no LLM):
  * 「이 카드」 → the card's name, sometimes a community nickname from aliases.json (reverse), card numbers dropped
  * colloquialize() and vague() from train_retriever (slang, dropped brackets, typos, under-specified questions)
Test = paper/results/colloquial_test.json (newest products, written separately; never used for training).
  python train/export_translate.py  -> train/data/translate_{train,valid,test}.jsonl"""
import json, os, random, re, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'train', 'data')
src = open(os.path.join(ROOT, 'train', 'train_retriever.py'), encoding='utf-8').read()
exec(src[src.index('SUBS = '):src.index('CTX = {}')])          # SUBS, colloquialize, vague (same generators as the retriever)
T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8')); QA, CARDS = T['qa'], T['cards']
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
AL = json.load(open(os.path.join(ROOT, 'aliases.json'), encoding='utf-8'))['alias']
NICK = collections.defaultdict(list)                               # official name -> nicknames
for x in AL:
    if not x.get('deck'): NICK[re.sub(r'^바이러스종 ', '', x['to'])].append(x['a'])
rng = random.Random(53)
name = lambda no: (CARDS.get(no) or [''])[0]


def namify(q, card):
    n = name(card)
    nick = NICK.get(n) or []
    who = rng.choice(nick) if nick and rng.random() < .5 else n
    s = re.sub(r'이 (?:카드|디지몬|테이머)(?=[의은는이가을를로에도])', who, q) if who and rng.random() < .85 else q
    s = re.sub(r'「(?:BT|EX|ST|P|LM|RB|AD)\d*-\d+ ([^」]+)」', lambda m: m.group(1) if rng.random() < .7 else m.group(0), s)
    return s


def variants(q, card):
    out = set()
    for _ in range(3):
        s = namify(q, card)
        s = vague(s, rng) if rng.random() < .25 else colloquialize(s, rng)
        if s.strip() and s != q: out.add(s.strip())
    return sorted(out)[:2]


rows = [(i, r) for i, r in enumerate(QA) if r[0] and prod(r[0]) not in NEW and 12 <= len(r[1]) <= 220]
cards = sorted({r[0] for _, r in rows}); rng.shuffle(cards); vcards = set(cards[:len(cards) // 10])
os.makedirs(OUT, exist_ok=True)
n = collections.Counter()
with open(os.path.join(OUT, 'translate_train.jsonl'), 'w', encoding='utf-8') as ft, open(os.path.join(OUT, 'translate_valid.jsonl'), 'w', encoding='utf-8') as fv:
    for i, r in rows:
        f = fv if r[0] in vcards else ft
        for s in variants(r[1], r[0]):
            f.write(json.dumps({'id': i, 'card': r[0], 'card_name': name(r[0]), 'source': s, 'target': r[1]}, ensure_ascii=False) + '\n')
            n['valid' if f is fv else 'train'] += 1
CS = json.load(open(os.path.join(ROOT, 'paper', 'results', 'colloquial_test.json'), encoding='utf-8'))['items']
with open(os.path.join(OUT, 'translate_test.jsonl'), 'w', encoding='utf-8') as f:
    for x in CS:
        f.write(json.dumps({'id': x['qid'], 'card': x['card'], 'card_name': x['card_name'], 'source': x['colloquial'], 'target': x['official'], 'style': x['style']}, ensure_ascii=False) + '\n')
        n['test'] += 1
print(dict(n))
