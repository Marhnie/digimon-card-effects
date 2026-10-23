"""E50: how much of the newest products' yes/no questions can a 「쟁점」 (issue) definition even reach?  (time split)
Issue = a key shared by older Q&A. For each newest-product yes/no Q&A: members = older yes/no Q&A with the same key.
Reach = members >= --min and unanimous (answer-as-if-positive agrees >= 0.9); then predict the answer from the members.
Reports reach (of 597) and accuracy on the reached ones. Retrieval quality is a separate question: this is the inventory ceiling."""
import json, re, collections, sys
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
OF = {int(k): v for k, v in T['rg']['of'].items()}
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
yn = lambda i: QA[i][8] >= 0
pos = lambda i: QA[i][8] ^ QA[i][9]
old = [i for i, r in enumerate(QA) if r[0] and prod(r[0]) not in NEW and yn(i)]
new = [i for i, r in enumerate(QA) if r[0] and prod(r[0]) in NEW and yn(i)]
sl = lambda i: tuple(QA[i][7]) if isinstance(QA[i][7], list) else QA[i][7]
KEYS = {
    'reason group (now)': lambda i: OF.get(i),
    'rule clause': lambda i: QA[i][4] or None,
    'clause + asked-thing': lambda i: (QA[i][4], QA[i][6]) if QA[i][4] else None,
    'unit pattern': lambda i: QA[i][3] if False else T['units'][QA[i][3]][10] if QA[i][3] is not None and QA[i][3] >= 0 and len(T['units'][QA[i][3]]) > 10 else None,
    'asked-thing + situation (precedent rule)': lambda i: (QA[i][6], sl(i)),
    'Q&A cluster (qa_group)': lambda i: QA[i][10],
}
def run(keyf, mn=2, cons=0.9):
    by = collections.defaultdict(list)
    for i in old:
        k = keyf(i)
        if k is not None: by[k].append(i)
    n = hit = ok = anym = 0
    for i in new:
        k = keyf(i)
        m = by.get(k, []) if k is not None else []
        anym += bool(m)
        if len(m) >= mn:
            p = sum(pos(j) for j in m) / len(m)
            if max(p, 1 - p) >= cons:
                hit += 1; pr = (1 if p >= .5 else 0) ^ QA[i][9]; ok += pr == QA[i][8]
    return {'any_member': anym, 'reach': hit, 'acc': round(ok / hit, 3) if hit else None}
print('new yes/no', len(new), 'old yes/no', len(old))
out = {}
for name, f in KEYS.items():
    for mn in (2, 3):
        out[f'{name} min{mn}'] = run(f, mn); print(f'{name:45s} min{mn}', out[f'{name} min{mn}'])
json.dump(out, open('paper/results/e50_issue_reach.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
