"""E43: 「같은 효과」 판단 개선 — 공식 선례(precedents) 단계를 페이지와 같은 규칙으로 재현해 시간 분할로 잰다.
기존: 같은 묻는 것·같은 상황 슬롯의 이전 Q&A 중 ① 같은 효과 패턴(문구 틀) → ② 같은 효과 유형 → ③ 나머지, ①이고 답이 전부 같으면 확정.
추가 후보: ①과 ② 사이에 「같은 룰북 구조」(분류·유발 조건·처리 단계의 행동·편·대상·필터가 같음, 문구는 달라도 됨).
  python same_effect_eval.py  -> paper/results/same_effect_eval.json
"""
import json, re, collections
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']; U = T['units']; ST = T['st']
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}; HALF = [{'BT22', 'EX9', 'ST21'}, {'BT23', 'BT24', 'EX10', 'ST22'}]
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
simQ = lambda a, b: (lambda A, B: len(A & B) / (len(A | B) or 1))(bg(a), bg(b))
def sig(u, level):
    s = ST[u]
    if not s: return None
    steps = [tuple(x[:4]) if level == 'loose' else tuple(x[:7]) for x in s[4]]
    if not steps: return None
    return (s[0], tuple(sorted(s[1])), tuple(s[2]) if level == 'strict' else len(s[2]) > 0, tuple(steps))
YN = [i for i, r in enumerate(QA) if r[0] and r[8] >= 0 and r[3] is not None and r[3] >= 0]
slk = lambda i: ','.join(map(str, sorted(QA[i][7])))
pool = [i for i in YN if prod(QA[i][0]) not in NEW]; test = [i for i in YN if prod(QA[i][0]) in NEW]
by = collections.defaultdict(list)
for j in pool: by[(QA[j][6], slk(j))].append(j)


def judge(i, mode):
    u = QA[i][3]; c = by.get((QA[i][6], slk(i)), [])
    if not c: return None
    tiers = [lambda j: U[QA[j][3]][10] == U[u][10]]
    if mode != 'base':
        su = sig(u, mode)
        tiers.append(lambda j: su is not None and sig(QA[j][3], mode) == su)
    tiers += [lambda j: bool(set(U[QA[j][3]][8]) & set(U[u][8])), lambda j: True]
    for t, f in enumerate(tiers):
        cc = [j for j in c if f(j)]
        if not cc: continue
        yes = no = 0; ys = []
        for j in cc:
            w = 0.05 + simQ(QA[i][1], QA[j][1]); y = QA[j][8] ^ (QA[j][9] ^ QA[i][9]); ys.append(y)
            if y: yes += w
            else: no += w
        ans = 1 if yes >= no else 0
        sure = (t == 0 or (mode != 'base' and t == 1)) and all(y == ans for y in ys)
        return {'tier': t, 'ans': ans, 'sure': sure, 'n': len(cc), 'ok': int(ans == QA[i][8])}
    return None


out = {'n_test': len(test)}
for mode in ('base', 'loose', 'strict'):
    rows = [r for r in (judge(i, mode) for i in test) if r]
    s = [r for r in rows if r['sure']]
    new_tier = [r for r in s if mode != 'base' and r['tier'] == 1]
    out[mode] = {'answered': len(rows), 'acc_all': round(sum(r['ok'] for r in rows) / len(rows), 4), 'sure': len(s), 'sure_acc': round(sum(r['ok'] for r in s) / max(1, len(s)), 4),
                 'sure_from_structure': len(new_tier), 'structure_acc': round(sum(r['ok'] for r in new_tier) / max(1, len(new_tier)), 4) if new_tier else None,
                 'by_tier': {t: [sum(1 for r in rows if r['tier'] == t), sum(r['ok'] for r in rows if r['tier'] == t)] for t in range(4)}}
    print(mode, json.dumps(out[mode], ensure_ascii=False))
json.dump(out, open('paper/results/same_effect_eval.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- E43b: relax the situation match for questions with no exact-situation pool ----
by_it = collections.defaultdict(list)
for j in pool: by_it[QA[j][6]].append(j)
jac = lambda a, b: len(set(a) & set(b)) / (len(set(a) | set(b)) or 1)
covered = {i for i in test if by.get((QA[i][6], slk(i)))}
rows = []
for i in test:
    if i in covered: continue
    u = QA[i][3]; su = sig(u, 'loose')
    c = [j for j in by_it.get(QA[i][6], []) if U[QA[j][3]][10] == U[u][10] or (su is not None and sig(QA[j][3], 'loose') == su)]
    if not c: continue
    sc = sorted(((jac(QA[i][7], QA[j][7]), simQ(QA[i][1], QA[j][1]), j) for j in c), reverse=True)
    best_sl = sc[0][0]; top = [x for x in sc if x[0] == best_sl]
    ys = [QA[j][8] ^ (QA[j][9] ^ QA[i][9]) for _, _, j in top]; ans = int(sum(ys) * 2 >= len(ys))
    rows.append({'i': i, 'sl': best_sl, 'sim': max(x[1] for x in top), 'n': len(top), 'unan': all(y == ans for y in ys), 'ok': int(ans == QA[i][8]),
                 'half': 0 if prod(QA[i][0]) in HALF[0] else 1})
print('not covered by exact situation:', len(test) - len(covered), '| same effect (pattern/structure) any situation:', len(rows))
for sl in (0.0, 0.34, 0.5, 0.67):
    for sm in (0.0, 0.3, 0.45):
        s = [r for r in rows if r['sl'] >= sl and r['sim'] >= sm and r['unan']]
        if s: print(f'  slot>={sl} sim>={sm} unanimous: {len(s)} acc {sum(r["ok"] for r in s) / len(s):.3f}')
# honest: pick (sl, sim) on one half (acc >= 0.95, n >= 8), measure on the other
res_h = []
for a, b in ((0, 1), (1, 0)):
    best = None
    for sl in (0.0, 0.34, 0.5, 0.67, 1.0):
        for sm in (0.0, 0.2, 0.3, 0.4, 0.5, 0.6):
            s = [r for r in rows if r['half'] == a and r['sl'] >= sl and r['sim'] >= sm and r['unan']]
            if len(s) >= 8 and sum(r['ok'] for r in s) / len(s) >= 0.95 and (best is None or len(s) > best[2]): best = (sl, sm, len(s))
    ev = [r for r in rows if best and r['half'] == b and r['sl'] >= best[0] and r['sim'] >= best[1] and r['unan']]
    res_h.append({'tuned_on': a, 'rule': best, 'eval_n': len(ev), 'eval_acc': round(sum(r['ok'] for r in ev) / len(ev), 4) if ev else None})
print('honest', res_h)
out['relaxed'] = {'uncovered': len(test) - len(covered), 'candidates': len(rows), 'honest': res_h}
json.dump(out, open('paper/results/same_effect_eval.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
