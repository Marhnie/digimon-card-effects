"""Attach evidence to every effect unit / pattern / type:
 - comprehensive-rule clauses, mapped from each element tag (timing, keyword, action, form, kind)
 - card Q&A pairs, assigned to the unit of their card that the question is about
 - rule-explanation Q&A topics, matched to keyword / kind names."""
import json, re, collections

R = [x for x in json.load(open('rules2.json', encoding='utf-8'))['rules'] if x['l'] >= 0]
QA = json.load(open('qa.json', encoding='utf-8'))
U = json.load(open('units2.json', encoding='utf-8'))
PATS = json.load(open('patterns.json', encoding='utf-8'))
CARDS = {c['no']: c for c in json.load(open('cards.json', encoding='utf-8'))}

TITLE = {r['n']: r['t'] for r in R}
def head(pattern, under=None):
    rx = re.compile(pattern)
    for r in R:
        if (under is None or r['n'] == under or r['n'].startswith(under + '-')) and len(r['t']) < 40 and rx.search(r['t']):
            return r['n']
    return None

TIMING_RULE = {}
for r in R:
    if r['n'].startswith('15-16-') and r['n'].count('-') == 2:
        for t in re.findall(r'【([^】]+)】', r['t']):
            TIMING_RULE[t] = r['n']
def timing_rule(t):
    if t in TIMING_RULE: return TIMING_RULE[t]
    if '턴 종료 시' in t: return head(r'턴 종료 시', '15-16')
    if '메인 페이즈 개시 시' in t: return head(r'메인 페이즈 개시 시', '15-16')
    if '개시 시' in t: return TIMING_RULE.get('자신의 턴 개시 시')
    return None

KW_RULE = {}
for r in R:
    if r['n'].startswith('16-') and r['n'].count('-') == 1:
        m = re.match(r'《([^》]+)》', r['t'])
        if m: KW_RULE[re.sub(r'\s*\+$', '', m.group(1)).strip()] = r['n']
KW_RULE.setdefault('시큐리티 어택', KW_RULE.get('S 어택'))
KW_RULE['오버플로우'] = head(r'^오버플로우$', '4')

A = lambda *ns: [n for n in ns if n]
ACTION_RULE = {
    '소멸': A(head(r'^소멸$', '4')), '소멸 내성': A(head(r'^소멸$', '4')), '파기': A(head(r'^파기$', '4')),
    '드로우': A(head(r'^드로우$', '4')), '이동': A(head(r'^이동$', '4')), '부화': A(head(r'^부화$', '4')),
    '토큰': A(head(r'^토큰$', '4')), '등장': A('7-1'), '진화': A('8-1'), '옵션 사용': A('9-1'),
    '진화원에 놓기': A(head(r'^진화원$', '4'), head(r'^겹쳐져 있는 카드$', '4')), '진화원 제거': A(head(r'^진화원$', '4')),
    '링크': A('10'), '효과 부여': A('15-13', head(r'얻는다・준다', '15-15')), '키워드 부여': A('15-13', head(r'얻는다・준다', '15-15')),
    '카드 효과 획득': A(head(r'얻는다・준다', '15-15')), '다른 효과 발휘': A(head(r'다른 효과를 발휘', '15-15')),
    '효과 무시·내성': A(head(r'효과를 받지 않는', '15-15')), '공개': A(head(r'공개하는 효과', '15-15')),
    '덱 위 확인': A(head(r'공개하는 효과', '15-15')), '시큐리티 공개·확인': A(head(r'공개하는 효과', '15-15')),
    '코스트 감소': A(head(r'^코스트$', '4')), '코스트 무료': A(head(r'^코스트$', '4')),
    '메모리 증가': A(head(r'^메모리$', '4')), '메모리 감소': A(head(r'^메모리$', '4')), '메모리 설정': A(head(r'^메모리$', '4')),
    '레스트': A(head(r'^표시 형식$', '4')), '액티브': A(head(r'^표시 형식$', '4')), '액티브 금지': A(head(r'^표시 형식$', '4')),
    'DP 증가': A(head(r'^DP', '2'), head(r'수치를 플러스', '15-15')), 'DP 감소': A(head(r'^DP', '2'), head(r'수치를 플러스', '15-15')),
    '상한·수치 변경': A(head(r'수치를 플러스', '15-15')), '퇴화': A(KW_RULE.get('퇴화')),
    '시큐리티 추가': A(KW_RULE.get('리커버리'), head(r'^시큐리티', '3')), '시큐리티 제거': A(head(r'^시큐리티', '3')),
    '추가 어택': A('11'), '어택 대상 변경': A('11'), '어택 금지': A('11'), '블록 금지': A('12'), '배틀시킴': A('14'),
    '색 조건 무시': A(head(r'^색 조건$', '4')), '취급 변경': A(head(r'정보 변경 효과', '15-12')),
    '배틀 에어리어에 놓기': A(head(r'^배틀 에어리어', '3')), '등장 금지': A('7-1'),
    '진화 조건 무시': A(head(r'^진화 조건', '2')), '되돌림·이탈 내성': A('3-1'),
    '치환(대신)': A(head(r'^치환', None) or head(r'대신', '18')), '셔플': A('1-3-10'),
    # Q5 (2026-10-17): actions that had no clause or a loose one
    '패로 회수': A(head(r'^패$', '3'), '3-1-3'), '덱으로 되돌림': A(head(r'^덱$', '3'), '3-1-3'),
    '효과 발휘 금지': A('15-4'), '트래시로 보냄': A(head(r'^트래시$', '3'), head(r'^파기$', '4')),
}
FORM_RULE = {'선택(임의)': A(head(r'^임의 처리$', '15-9')), '조건(~라면)': A('15-6'), '개수 비례(마다)': A(head(r'^「마다」$', '4')),
             '트리거(~했을 때)': A('15-5', head(r'유발형 효과', '15-8')), '횟수 제한': A(head(r'\[턴 X회\]', '15-14'))}
KIND_RULE = {'특수 진화 조건:진화': A('8-1', head(r'^진화 조건$', '2')), '특수 진화 조건:조그레스': A('8-2'), '특수 진화 조건:어플 합체': A('8-4'),
             '특수 진화 조건:버스트 진화': A('8-3'), '디지크로스': A('7-2'), '어셈블리': A('7-3'), '링크': A('10'),
             '카드 고유 룰': A(head(r'〈룰〉', '2')), '키워드 능력': A('16')}
WHERE_RULE = {'진화원 효과': A('15-3'), '시큐리티 효과': A(TIMING_RULE.get('시큐리티'), '13-1')}

def unit_rules(u):
    out = []
    out += KIND_RULE.get(u['kind'], [])
    out += WHERE_RULE.get(u['where'], [])
    out += [x for t in u['timing'] for x in [timing_rule(t)] if x]
    out += [KW_RULE[k] for k in u['keywords'] if KW_RULE.get(k)]
    for a in u['actions']: out += ACTION_RULE.get(a, [])
    for f in u['forms']: out += FORM_RULE.get(f, [])
    if u.get('trigger'):
        ev = u['trigger'].split(' · ')[-1]
        out += ACTION_RULE.get({'파기됨': '파기', '소멸함': '소멸', '등장함': '등장', '진화함': '진화', '레스트함': '레스트', '액티브가 됨': '액티브', '링크함': '링크',
                                '퇴화함': '퇴화', '드로우함': '드로우', '사용함': '옵션 사용', '되돌아감': '패로 회수', '어택함': '추가 어택', '블록함': '블록 금지'}.get(ev, ''), [])
        if '진화원' in u['trigger']: out += ACTION_RULE.get('진화원 제거', [])
        out += FORM_RULE.get('트리거(~했을 때)', [])
    seen, res = set(), []
    for x in out:
        if x and x not in seen: seen.add(x); res.append(x)
    return res

for u in U:
    u['rules'] = unit_rules(u)

# ---- card Q&A → unit ----
def bigr(s):
    s = re.sub(r'\s+', '', s); return {s[i:i + 2] for i in range(len(s) - 1)}
by_card = collections.defaultdict(list)
for i, u in enumerate(U): by_card[u['card']].append(i)
qa_items = []
for si, s in enumerate(QA['cqa']):
    for cj, c in enumerate(s['cards']):
        m = re.match(r'^([A-Z]+\d*-\d+|P-\d+)', c['name'])
        no = m.group(1) if m else None
        for qi, (q, a) in enumerate(c['qa']):
            item = {'id': f'C{si}-{cj}-{qi}', 'card': no, 'cardname': c['name'], 'set': s['set'], 'q': q, 'a': a, 'unit': None}
            idx = by_card.get(no, [])
            if idx:
                qb = bigr(q)
                best, bs = None, 0
                for i in idx:
                    u = U[i]; sc = 0.0
                    sc += 3 * sum(1 for t in u['timing'] if f'【{t}】' in q)
                    sc += 3 * sum(1 for k in u['keywords'] if k in q)
                    if u['where'] == '진화원 효과' and '진화원 효과' in q: sc += 2
                    if u['where'] == '시큐리티 효과' and '【시큐리티】' in q: sc += 2
                    ub = bigr(u['text']); sc += 4 * len(qb & ub) / (len(ub) + 1)
                    if sc > bs: best, bs = i, sc
                if len(idx) == 1 or bs >= 1.2:
                    item['unit'] = best
            qa_items.append(item)
for it in qa_items:
    if it['unit'] is not None:
        U[it['unit']].setdefault('qa', []).append(it['id'])

# ---- Q7 second pass: quoted phrase → unit; remainder → "general ruling" linked to nearest rule clause ----
import math
rb = {r['n']: bigr(r['t']) for r in R if len(r['t']) >= 15}
df = collections.Counter(g for s in rb.values() for g in s)
NR = len(rb)
def nearest_rule(q):
    qb = bigr(q); best, bs = None, 0
    for n, s in rb.items():
        sc = sum(math.log(1 + NR / df[g]) ** 2 for g in (qb & s)) / (1 + 0.25 * len(s) ** 0.5)
        if sc > bs: best, bs = n, sc
    return best
for it in qa_items:
    if it['unit'] is not None or it['card'] not in by_card:
        continue
    quotes = [x for x in re.findall(r'「([^「」]{4,})」', it['q'])]
    hit = None
    for i in by_card[it['card']]:
        if any(x.replace(' ', '') in U[i]['text'].replace(' ', '') for x in quotes):
            hit = i; break
    if hit is None:
        # questions about the card's special parts name them: 진화 조건, 어플 합체, 〈룰〉, {패}, 디지크로스 …
        cues = [('진화 조건', lambda u: u['kind'].startswith('특수 진화 조건')), ('조그레스', lambda u: u['kind'] == '특수 진화 조건:조그레스'),
                ('어플 합체', lambda u: u['kind'] == '특수 진화 조건:어플 합체'), ('버스트 진화', lambda u: u['kind'] == '특수 진화 조건:버스트 진화'),
                ('〈룰〉', lambda u: u['kind'] == '카드 고유 룰'), ('디지크로스', lambda u: u['kind'] == '디지크로스'), ('어셈블리', lambda u: u['kind'] == '어셈블리'),
                ('링크', lambda u: u['kind'] == '링크'), ('{패}', lambda u: '패' in u['limit']), ('{트래시}', lambda u: '트래시' in u['limit']),
                ('{육성}', lambda u: '육성' in u['limit']), ('{시큐리티}', lambda u: '시큐리티' in u['limit'])]
        for cue, ok in cues:
            if cue in it['q']:
                c = [i for i in by_card[it['card']] if ok(U[i])]
                if c: hit = c[0]; break
    if hit is not None:
        it['unit'] = hit; it['how'] = 'quote'
        U[hit].setdefault('qa', []).append(it['id'])
    else:
        it['general'] = True
        it['rule'] = nearest_rule(re.sub(r'\d{4}/\d{2}/\d{2}.*', '', it['q']))
gen_by_rule = collections.defaultdict(list)
for it in qa_items:
    if it.get('general') and it.get('rule'):
        gen_by_rule[it['rule']].append(it['id'])
json.dump(gen_by_rule, open('general_by_rule.json', 'w', encoding='utf-8'), ensure_ascii=False)

# ---- rule-explanation topics → keyword / kind ----
topic_items = []
for ci, c in enumerate(QA['rqa']):
    for ti, t in enumerate(c['topics']):
        topic_items.append({'id': f'H{ci}-{ti}', 'cat': c['cat'], 'name': t['name'], 'n': len(t['qa'])})
def topics_for(u):
    names = set(u['keywords']) | {u['kind'].split(':')[-1]} | set(u['timing']) | set(u['actions'])
    return [t['id'] for t in topic_items if any(n and (n == t['name'] or n in t['name'].split(' (')[0]) for n in names)]
for u in U:
    u['topics'] = topics_for(u)

json.dump(U, open('units3.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(qa_items, open('qa_items.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(topic_items, open('topic_items.json', 'w', encoding='utf-8'), ensure_ascii=False)
withcard = [q for q in qa_items if q['card'] in CARDS]
print('quote-linked', sum(1 for q in qa_items if q.get('how')=='quote'), 'general', sum(1 for q in qa_items if q.get('general')))
print('card QA', len(qa_items), 'card found', len(withcard), 'assigned to unit', sum(1 for q in qa_items if q['unit'] is not None))
print('units with rules', sum(1 for u in U if u['rules']), '/', len(U), ' with QA', sum(1 for u in U if u.get('qa')), ' with topics', sum(1 for u in U if u['topics']))
print('missing maps:', {a: v for a, v in ACTION_RULE.items() if not v})
print('timing map', TIMING_RULE)
