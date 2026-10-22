"""E39: community rule questions (collected by the user, kept local) vs the server — text only, no card picked.

  python train/community_eval.py [train/data/community_q.txt]  ->  train/data/community_eval.json (local, gitignored)
Measures (no gold answers exist yet): card names the page can resolve, unresolved nicknames,
nearest official Q&A by the server's fused search (cos of the top hit), and how many reach the semantic-decide threshold.
"""
import json, os, re, sys, urllib.request, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'train', 'data', 'community_q.txt')
T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8')); QA = T['qa']
nrm = lambda s: re.sub(r'[\s:：・·\-–—「」『』()（）\[\].,!?~]', '', s or '')
NAMES = collections.defaultdict(list)
for no, c in T['cards'].items():
    k = nrm(c[0])
    if len(k) >= 3: NAMES[k].append(no)
KEYS = sorted(NAMES, key=len, reverse=True)
CODE = re.compile(r'\b(?:BT|EX|ST|P|LM|RB|AD)\d*-?\d+\b')
SEM_THR = 0.885


def cards_in(q):
    s = nrm(q); used = [False] * len(s); out = []
    for k in KEYS:
        i = s.find(k)
        while i >= 0:
            if not any(used[i:i + len(k)]):
                for j in range(i, i + len(k)): used[j] = True
                out.append(k); break
            i = s.find(k, i + 1)
    return out


def search(q):
    r = urllib.request.Request('http://127.0.0.1:8787/api/search', json.dumps({'q': q, 'k': 3}).encode(), {'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(r, timeout=60))['hits'][:3]


qs = [l.strip() for l in open(SRC, encoding='utf-8') if l.strip()]
rows = []
for q in qs:
    names = cards_in(q)
    # words ending in 몬/몬X that are not card names -> nickname candidates (also 2-4 syllable slang before particles)
    mons = [w for w in re.findall(r'[가-힣]{2,}몬[A-Z]?', q) if not any(nrm(w) in k or k in nrm(w) for k in names)]
    h = search(q)
    rows.append({'q': q, 'asks': bool(re.search(r'[?？]|나$|냐$|임$|함$|됨$|맞지$|맞음$|가능$', q)), 'cards': names, 'unknown_mon': mons,
                 'top': [{'card': QA[x['i']][0], 'q': QA[x['i']][1], 'cos': x['cos'], 'y': QA[x['i']][8]} for x in h]})
n = len(rows)
cos1 = [r['top'][0]['cos'] for r in rows if r['top']]
summ = {'n': n, 'asks_question': sum(r['asks'] for r in rows), 'title_only': sum(not r['asks'] for r in rows),
        'with_card_name': sum(bool(r['cards']) for r in rows), 'unknown_mon_words': collections.Counter(w for r in rows for w in r['unknown_mon']).most_common(60),
        'top1_cos_ge_thr': sum(c >= SEM_THR for c in cos1), 'top1_cos_ge_0.8': sum(c >= 0.8 for c in cos1), 'top1_cos_ge_0.7': sum(c >= 0.7 for c in cos1),
        'top1_cos_median': sorted(cos1)[len(cos1) // 2]}
json.dump({'summary': summ, 'rows': rows}, open(os.path.join(ROOT, 'train', 'data', 'community_eval.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1))
