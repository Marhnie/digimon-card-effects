"""E18 second held-out yes/no test: 200 NEW card Q&A items (100 네 / 100 아니요), disjoint from the E3 100.
S2 Claude alone, S3 Claude + 2-gram retrieval, S5 Claude + v4 judge-helper evidence (rulebook structure + same effect cluster).
(derived from eval_build.py)
Builds: S1 classification-only predictions (no LLM) and prompt batches for
S2 Claude alone, S3 Claude + current bot retrieval, S4 Claude + classification evidence."""
import json, re, math, random, collections, os

U = json.load(open('units3.json', encoding='utf-8'))
QI = json.load(open('qa_items.json', encoding='utf-8'))
CARDS = {c['no']: c for c in json.load(open('cards.json', encoding='utf-8'))}
RQ = json.load(open('qa.json', encoding='utf-8'))['rqa']
RULES = [r for r in json.load(open('rules2.json', encoding='utf-8'))['rules'] if r['l'] >= 0]
RT = {r['n']: r['t'] for r in RULES}
GEN = json.load(open('general_by_rule.json', encoding='utf-8'))
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
for q in QI: q['q'], q['a'] = cq(q['q']), cq(q['a'])
lab = lambda a: 'Y' if re.match(r'^\s*(네|예)[,，.\s]', a) else ('N' if re.match(r'^\s*(아니요|아니오|아뇨)[,，.\s]', a) else None)
for q in QI: q['lab'] = lab(q['a'])

def bigr(s):
    s = re.sub(r'\s+', '', s); return {s[i:i + 2] for i in range(len(s) - 1)}
for q in QI: q['bg'] = bigr(q['q'])
jac = lambda a, b: len(a & b) / (len(a | b) or 1)

random.seed(20261017)
pool = [q for q in QI if q['card'] in CARDS and q['lab']]
ys = [q for q in pool if q['lab'] == 'Y']; ns = [q for q in pool if q['lab'] == 'N']
FIRST = random.sample(ys, 50) + random.sample(ns, 50)          # the E3 draw, reproduced to exclude it
first_ids = {q['id'] for q in FIRST}
random.seed(20261018)
ys2 = [q for q in ys if q['id'] not in first_ids]; ns2 = [q for q in ns if q['id'] not in first_ids]
TEST = random.sample(ys2, 100) + random.sample(ns2, 100)
random.shuffle(TEST)
for k, t in enumerate(TEST): t['tid'] = f'U{k + 1:03d}'

def leak(t, q):  # the item itself or a near-identical restatement of it
    return q['id'] == t['id'] or (q['card'] == t['card'] and jac(q['bg'], t['bg']) > 0.6) or jac(q['bg'], t['bg']) > 0.85

def card_text(no):
    c = CARDS[no]; s = c['상단 텍스트']
    if c['하단 텍스트'] not in ('', '-'): s += '\n[하단] ' + c['하단 텍스트']
    return s

# ---------- S3: the current bot's retrieval (char-bigram idf over rules + rule Q&A + card Q&A) ----------
ITEMS = []
for r in RULES:
    ITEMS.append({'id': 'R' + r['n'], 'label': '종합 룰 ' + r['n'], 'text': r['t'], 'src': 'rule'})
for ci, c in enumerate(RQ):
    for ti, t in enumerate(c['topics']):
        for qi, (q, a) in enumerate(t['qa']):
            ITEMS.append({'id': f'H{ci}-{ti}-{qi}', 'label': f'규칙 해설 · {t["name"]} Q{qi + 1}', 'text': f'Q. {q}\nA. {a}', 'src': 'rqa'})
QBYID = {}
for q in QI:
    it = {'id': q['id'], 'label': f'카드 Q&A · {q["cardname"]}', 'text': f'Q. {q["q"]}\nA. {q["a"]}', 'src': 'cqa', 'qa': q, 'card': q['card']}
    ITEMS.append(it); QBYID[q['id']] = it
post = collections.defaultdict(list)
for k, it in enumerate(ITEMS):
    it['bg'] = bigr(it['label'] + ' ' + it['text'])
    for g in it['bg']: post[g].append(k)
N = len(ITEMS); idf = {g: math.log(1 + N / len(a)) for g, a in post.items()}

def retrieve(query, card, limit, exclude):
    sc = collections.Counter()
    for g in bigr(query):
        a = post.get(g)
        if not a or len(a) > N * 0.25: continue
        for k in a: sc[k] += idf[g]
    for k in list(sc):
        it = ITEMS[k]
        if it.get('card') == card: sc[k] += 40
        if it['src'] == 'rule' and len(it['text']) < 25: sc[k] *= 0.55
    for k, it in enumerate(ITEMS):
        if it.get('card') == card: sc[k] = max(sc[k], 40)
    out = []
    for k, _ in sc.most_common():
        it = ITEMS[k]
        if it['src'] == 'cqa' and exclude(it['qa']): continue
        out.append(it)
        if len(out) >= limit: break
    return out

# ---------- classification helpers ----------
by_card = collections.defaultdict(list)
for i, u in enumerate(U): by_card[u['card']].append(i)
by_pat = collections.defaultdict(list)
for i, u in enumerate(U): by_pat[u['pattern']].append(i)
unit_of_q = {q['id']: q['unit'] for q in QI}

def find_unit(t):
    """which effect of the card the question is about (same scoring as the linking step, question text only)"""
    idx = by_card.get(t['card'], [])
    if not idx: return None
    best, bs = None, -1
    for i in idx:
        u = U[i]; sc = 3 * sum(1 for x in u['timing'] if f'【{x}】' in t['q']) + 3 * sum(1 for k in u['keywords'] if k in t['q'])
        ub = bigr(u['text']); sc += 4 * len(t['bg'] & ub) / (len(ub) + 1)
        if sc > bs: best, bs = i, sc
    return best

def qa_units(q):
    return U[q['unit']] if q['unit'] is not None else None

def evidence_s4(t, limit=28):
    ex = lambda q: leak(t, q)
    ui = find_unit(t); u = U[ui] if ui is not None else None
    out, seen = [], set()
    def add(it, why):
        if it['id'] in seen or len(out) >= limit: return
        seen.add(it['id']); out.append(dict(it, why=why))
    # a. other Q&A of the same card
    for q in QI:
        if q['card'] == t['card'] and not ex(q): add(QBYID[q['id']], '같은 카드')
    if u:
        # b. same pattern, other cards, most similar question first
        cands = []
        for i in by_pat[u['pattern']]:
            if U[i]['card'] == t['card']: continue
            for qid in U[i].get('qa', []):
                q = next(x for x in [QBYID[qid]['qa']])
                if not ex(q): cands.append((jac(q['bg'], t['bg']), q))
        for s, q in sorted(cands, key=lambda x: -x[0])[:9]: add(QBYID[q['id']], f'같은 패턴 #{u["pattern"]}')
        # c. same effect type and timing, other patterns
        cands = []
        for i, v in enumerate(U):
            if v['pattern'] == u['pattern'] or v['card'] == t['card'] or not v.get('qa'): continue
            if not (set(v['types']) & set(u['types'])) or (u['timing'] and not set(v['timing']) & set(u['timing'])): continue
            for qid in v['qa']:
                q = QBYID[qid]['qa']
                if not ex(q): cands.append((jac(q['bg'], t['bg']), q))
        for s, q in sorted(cands, key=lambda x: -x[0])[:5]: add(QBYID[q['id']], '같은 유형·타이밍')
        # d. rule clauses of the effect's tags (+ up to 3 sub-clauses)
        for n in u['rules'][:8]:
            kids = [k for k in RT if k.startswith(n + '-') and k.count('-') == n.count('-') + 1][:3]
            txt = RT[n] + ''.join(f'\n  {k} {RT[k][:140]}' for k in kids)
            add({'id': 'R' + n, 'label': '종합 룰 ' + n, 'text': txt, 'src': 'rule'}, '효과 태그의 룰 조항')
        # e. general rulings attached to those clauses
        cands = []
        for n in u['rules']:
            for k, ids in GEN.items():
                if k == n or k.startswith(n + '-'):
                    for qid in ids:
                        q = QBYID[qid]['qa']
                        if not ex(q) and q['card'] != t['card']: cands.append((jac(q['bg'], t['bg']), q))
        for s, q in sorted(cands, key=lambda x: -x[0])[:3]: add(QBYID[q['id']], '일반 판정')
    # f. fill with plain retrieval
    for it in retrieve(t['card'] + ' ' + t['q'], t['card'], 40, ex):
        add(it, '문구 검색')
    return out, u

# ---------- S5: v4 judge-helper evidence ----------
ST = {s['i']: s for s in json.load(open('struct2.json', encoding='utf-8'))}
NET = json.load(open('net/effect_sna.json', encoding='utf-8'))
_nodes = [s for s in json.load(open('struct2.json', encoding='utf-8')) if s['분류'] != '카드 정보(효과 아님)']
CLU = {s['i']: NET['nodes'][k]['c'] for k, s in enumerate(_nodes)}
CNAME = {c['id']: c['name'] for c in NET['clusters']}
by_clu = collections.defaultdict(list)
for i, c in CLU.items(): by_clu[c].append(i)
TRIG_TM = {'등장 시', '진화 시', '소멸 시', '어택 시', '링크 시', '시큐리티', '자신의 턴 개시 시', '상대의 턴 개시 시', '자신의 턴 종료 시', '상대의 턴 종료 시',
           '서로의 턴 종료 시', '자신의 메인 페이즈 개시 시', '상대의 메인 페이즈 개시 시', '어택 종료 시', '이동 시'}
def trig_keys(s): return ['【' + x + '】' for x in s.get('타이밍', []) if x in TRIG_TM] + ([s['유발 키']] if s.get('유발 키') else [])
by_trig = collections.defaultdict(list)
for i, s in ST.items():
    for g in trig_keys(s): by_trig[g].append(i)
def struct_text(i):
    s = ST[i]; c = CLU.get(i)
    st = ' '.join(f"{k + 1}) {'임의' if p['임의'] else '강제'} {'/'.join(p['acts']) or '?'}{' → ' + (p.get('side', '') + '의 ' if p.get('side') else '') + p.get('target', '') if p.get('target') else ''}" for k, p in enumerate(s['처리']))
    return (f"분류(15-8): {s['분류']} / 타이밍: {''.join('【' + x + '】' for x in s['타이밍']) or '없음'} / 유발 조건(15-5): {', '.join(trig_keys(s)) or '없음'} / "
            f"처리 조건(15-6): {', '.join(s['처리 조건']) or '없음'} / 임의 처리 조건(15-7): {', '.join(c_['text'] for c_ in s['임의 처리 조건']) or '없음'} / 처리 단계: {st or '없음'}"
            + (f" / 같은 효과 무리: {CNAME[c]}" if c is not None else ''))
def evidence_s5(t, limit=28):
    ex = lambda q: leak(t, q)
    ui = find_unit(t)
    out, seen = [], set()
    def add(it, why):
        if it['id'] in seen or len(out) >= limit: return
        seen.add(it['id']); out.append(dict(it, why=why))
    if ui is not None:
        out.append({'id': 'S' + str(ui), 'label': '질문 대상 효과의 구조(종합 룰 15장)', 'text': struct_text(ui), 'why': ''}); seen.add('S' + str(ui))
    # a. similar questions anywhere (2-gram), b. this card's Q&A
    for it in retrieve(t['card'] + ' ' + t['q'], t['card'], 12, ex): add(it, '비슷한 질문')
    for q in QI:
        if q['card'] == t['card'] and not ex(q): add(QBYID[q['id']], '같은 카드')
    if ui is not None:
        def ranked(idx):
            c = []
            for i in idx:
                if U[i]['card'] == t['card']: continue
                for qid in U[i].get('qa', []):
                    q = QBYID[qid]['qa']
                    if not ex(q): c.append((jac(q['bg'], t['bg']), q))
            return [q for _, q in sorted(c, key=lambda x: -x[0])]
        # c. same effect cluster (network), d. same trigger condition
        if CLU.get(ui) is not None:
            for q in ranked(by_clu[CLU[ui]])[:6]: add(QBYID[q['id']], '같은 효과 무리: ' + CNAME[CLU[ui]])
        for g in trig_keys(ST[ui])[:2]:
            for q in ranked(by_trig[g])[:3]: add(QBYID[q['id']], '같은 유발 조건 ' + g)
        # e. rule clauses
        for n in U[ui]['rules'][:6]:
            kids = [k for k in RT if k.startswith(n + '-') and k.count('-') == n.count('-') + 1][:3]
            add({'id': 'R' + n, 'label': '종합 룰 ' + n, 'text': RT[n] + ''.join(f'\n  {k} {RT[k][:140]}' for k in kids), 'src': 'rule'}, '효과의 룰 조항')
    for it in retrieve(t['card'] + ' ' + t['q'], t['card'], 40, ex): add(it, '문구 검색')
    return out

# ---------- S1: classification only, no LLM: weighted vote of the nearest labelled Q&A ----------
def s1(t):
    ui = find_unit(t); u = U[ui] if ui is not None else None
    scored = []
    for q in QI:
        if not q['lab'] or leak(t, q): continue
        s = jac(q['bg'], t['bg'])
        if s < 0.12: continue
        v = qa_units(q); w = 1.0
        if u and v is not None:
            if v['pattern'] == u['pattern']: w = 3.0
            elif set(v['types']) & set(u['types']): w = 1.6
        if q['card'] == t['card']: w = max(w, 2.0)
        scored.append((s * w, q))
    scored.sort(key=lambda x: -x[0])
    top = scored[:7]
    vote = collections.Counter()
    for s, q in top: vote[q['lab']] += s
    pred = vote.most_common(1)[0][0] if vote else 'Y'
    return pred, [q['id'] for _, q in top[:3]]

# ---------- write everything ----------
os.makedirs('eval2', exist_ok=True)
gold = {t['tid']: {'card': t['card'], 'q': t['q'], 'a': t['a'], 'lab': t['lab'], 'qa_id': t['id']} for t in TEST}
json.dump(gold, open('eval2/gold.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
s1p = {}
for t in TEST:
    p, why = s1(t); s1p[t['tid']] = {'pred': p, 'nearest': why}
json.dump(s1p, open('eval2/S1_pred.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def block(t, ev):
    nm = re.sub(r'^\S+\s*', '', CARDS[t['card']]['name'])
    s = f'### {t["tid"]}\n카드: {t["card"]} {nm} ({CARDS[t["card"]]["type"]})\n카드 텍스트: {card_text(t["card"])}\n질문: {t["q"]}\n'
    if ev is not None:
        s += '자료:\n' + '\n'.join(f'- [{it["label"]}{" · " + it["why"] if it.get("why") else ""}] {it["text"]}' for it in ev) + '\n'
    return s

def batches(name, items, size):
    for b in range(0, len(items), size):
        open(f'eval2/{name}_b{b // size + 1}.md', 'w', encoding='utf-8').write('\n'.join(items[b:b + size]))

S2 = [block(t, None) for t in TEST]
S3 = [block(t, retrieve(t['card'] + ' ' + t['q'], t['card'], 28, lambda q, t=t: leak(t, q))) for t in TEST]
S5 = [block(t, evidence_s5(t)) for t in TEST]
batches('S2', S2, 50); batches('S3', S3, 25); batches('S5', S5, 25)
acc = sum(1 for t in TEST if s1p[t['tid']]['pred'] == t['lab'])
print('test', len(TEST), 'S1 accuracy', acc, '/', len(TEST), ' avg chars S3', sum(map(len, S3)) // len(S3), ' S5', sum(map(len, S5)) // len(S5))
