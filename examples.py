"""Same verdict rules as the page (exact intent + exact situation slots; tier A/B/C; A+unanimous = 확정)."""
import json, re, random
exec(open('q_slots.py', encoding='utf-8').read().split("for d in D: d['sl']")[0])   # intent(), slots(), D
U = json.load(open('units3.json', encoding='utf-8')); QI = json.load(open('qa_items.json', encoding='utf-8'))
CARDS = {c['no']: c for c in json.load(open('cards.json', encoding='utf-8'))}
for q, d in zip(QI, D):
    d['sl'] = frozenset(slots(d['q'])); d['unit'] = q['unit']; d['neg'] = 1 if '부정:부정 질문' in d['sl'] else 0
def bg(s):
    s = re.sub(r'\s+', '', s); return {s[i:i+2] for i in range(len(s)-1)}
def sim(a, b):
    A, B = bg(a), bg(b); x = len(A & B); return x / ((len(A) + len(B) - x) or 1)
pool_by = {}
for d in D:
    if d['y'] is not None: pool_by.setdefault((d['it'], d['sl']), []).append(d)
def verdict(unit, q):
    it, sl = intent(q), frozenset(slots(q)); neg = 1 if '부정:부정 질문' in sl else 0
    pool = pool_by.get((it, sl), [])
    def tier(d):
        v = U[d['unit']] if d['unit'] is not None else None
        if not v: return 2
        if v['pattern'] == unit['pattern']: return 0
        if set(v['types']) & set(unit['types']): return 1
        return 2
    for t in range(3):
        c = [d for d in pool if tier(d) == t]
        if not c: continue
        yes = no = 0; ys = []
        for d in c:
            w = 0.05 + sim(q, d['q']); y = d['y'] ^ (d['neg'] ^ neg); ys.append(y)
            if y: yes += w
            else: no += w
        ans = 1 if yes >= no else 0; una = all(y == ans for y in ys)
        return ('확정' if t == 0 and una else '참고'), t, ans, len(c)
    return '선례 없음', -1, None, 0
by_pat = {}
for i, u in enumerate(U): by_pat.setdefault(u['pattern'], []).append(i)
qa_cards = {q['card'] for q in QI}
random.seed(11)
idx = list(range(len(D))); random.shuffle(idx)
out = {'확정': [], '참고': [], '선례 없음': []}
for k in idx:
    d = D[k]; q = QI[k]
    if d['y'] is None or q['unit'] is None or len(d['q']) > 110 or not q['card']: continue
    u = U[q['unit']]
    others = [j for j in by_pat[u['pattern']] if U[j]['card'] != q['card'] and U[j]['card'] not in qa_cards and U[j]['tpl'] == u['tpl']]
    if not others: continue
    t = U[others[0]]
    lvl, tier, ans, n = verdict(t, d['q'])
    if len(out[lvl]) < 4:
        out[lvl].append({'ask_card': t['card'], 'ask_name': re.sub(r'^\S+\s*', '', CARDS[t['card']]['name']), 'effect': t['text'],
                         'q': d['q'], 'tier': tier, 'engine': None if ans is None else ('네' if ans else '아니요'), 'n': n,
                         'src': q['card'], 'src_name': q['cardname'], 'official': cq(q['a'])})
    if all(len(v) >= 4 for v in out.values()): break
json.dump(out, open('examples.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for lvl, xs in out.items():
    print('=====', lvl)
    for x in xs:
        print(f"- [{x['ask_card']} {x['ask_name']}] {x['q']}\n    엔진: {x['engine']} (선례 {x['n']}, 단계 {'ABC'[x['tier']] if x['tier']>=0 else '-'}) | 공식({x['src']}): {x['official'][:70]}")
