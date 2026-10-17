"""Rulebook (종합 룰 Ver.4.3 ch.15) structure of every card effect.
  출처        2-3-3 효과(상단) / 15-3 진화원 효과 / 15-16-10 시큐리티 효과 ; 효과의 종류 15-2 (디지몬·테이머·옵션의 효과)
  분류        15-8 상재형 / 유발형 / 기동형 / 즉시형   (+ 키워드 효과 16장, 카드 정보 2-3: 진화 조건·디지크로스·〈룰〉…)
  타이밍      15-16 ;  아이콘 15-14 ([턴 X회] {패} {트래시} {육성} {시큐리티})
  유발 조건   15-5  (유발형 '~했을 때' / 즉시형 '~할 때')
  처리 조건   15-6  ('~라면', '~인 동안', 상태 '~일 때')
  임의 처리 조건 15-7 ('~하는 것으로')
  처리        15-1-2 순서대로; 15-9 강제/임의; 15-10 대상; 15-11 단일/전체; 15-12 정보 추가/변경; 15-13 부여; 18-2 치환
"""
import json, re, collections
from parse_fx import ACTIONS, TIMING_RUN, LIM

ACT = [(n, p) for n, p in ACTIONS if n not in ('코스트 무료',)] + [('코스트 감소', re.compile(r'코스트를\s*-\s*\d')), ('어택 종료', re.compile(r'어택을 종료')), ('금지', re.compile(r'(?:할|될|받을|놓을) 수 없|하지 않는다$')),
       ('룰 변경', re.compile(r'조건이[^.]{0,30}(?:된다|한다)')), ('디지크로스 확장', re.compile(r'디지크로스로'))]
KW_NOTE = re.compile(r'(《[^《》]*(?:《[^》]*》)?[^《》]*》)\s*\([^()]*\)')   # keyword + its reminder text
TRIGGER_TIMINGS = {'등장 시', '진화 시', '소멸 시', '어택 시', '링크 시', '시큐리티', '자신의 턴 개시 시', '상대의 턴 개시 시', '자신의 턴 종료 시',
                   '상대의 턴 종료 시', '서로의 턴 종료 시', '자신의 메인 페이즈 개시 시', '상대의 메인 페이즈 개시 시', '어택 종료 시', '이동 시'}
ACTIVATE_TIMINGS = {'메인', '카운터'}
DURATION_TIMINGS = {'자신의 턴', '상대의 턴', '서로의 턴'}

STATE_WHEN = r'(?:있을|없을|이하일|이상일|일|가질|포함할|있었을)'
PAST_WHEN = r'(?:했을|되었을|됐을|졌을|났을|었을|았을|였을|시켰을|당했을|들었을|갔을|왔을)'
NOW_WHEN = r'(?:할|될|날|갈|시킬|떠날|벗어날)'

def strip_quotes(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    return s

def trigger_clause(body):
    """first '~때,' clause that is an event (not a state); returns (clause, tense) or (None, None)"""
    b = strip_quotes(re.sub(r'《[^》]*》\s*\([^)]*\)', '', body))
    for m in re.finditer(r'(\S+) 때[,，]', b[:260]):
        w = m.group(1)
        if re.search(STATE_WHEN + r'$', w) and not re.search(PAST_WHEN + r'$', w): continue
        start = max(b.rfind('.', 0, m.start()), b.rfind(',', 0, m.start()) if False else -1) + 1
        clause = b[start:m.end()].strip()
        tense = '유발형' if re.search(PAST_WHEN + r'$', w) else ('즉시형' if re.search(NOW_WHEN + r'$', w) else '유발형')
        return clause, tense
    return None, None

from trigger_fx import SUBJ, PLACE, CAUSE, EVENT
def trigger_key(clause):
    c = re.sub(r'「X」', '', clause)
    pick = lambda L: next((n for n, p in L if p.search(c)), '')
    ev = pick(EVENT)
    # immediate ('~할 때') verbs: normalise to the same event names
    if not ev:
        for n, p in [('소멸함', r'소멸할'), ('진화함', r'진화할'), ('등장함', r'등장(?:할|시킬)'), ('벗어남', r'벗어날|떠날'), ('되돌아감', r'(?:되)?돌아갈'),
                     ('파기됨', r'파기(?:될|할)'), ('사용함', r'사용할'), ('어택함', r'어택할'), ('디지크로스함', r'디지크로스할')]:
            if re.search(p, c): ev = n; break
    if not ev: return ''
    return ' · '.join(x for x in (pick(SUBJ), pick(PLACE), pick(CAUSE), ev) if x)

COND_RE = re.compile(r'([^,.]*?(?:라면|다면|인 동안|있는 동안|하는 동안|하고 있는 동안|' + STATE_WHEN + r' 때))[,，]')
COST_RE = re.compile(r'([^,.]*?것으로)[,，]?')

def steps_of(body):
    """processing steps in written order (15-1-2): split on sentences and '그 후'"""
    parts = []
    body = body.replace('Lv.', 'Lv․')
    for sent in re.split(r'(?<=[.。])\s*', body):
        for p in re.split(r'그 후[,，]?\s*', sent):
            p = p.strip(' ,.').replace('Lv․', 'Lv.')
            if p: parts.append(p)
    return parts

def step_info(s):
    acts = [n for n, p in ACT if p.search(s)]
    for k in re.findall(r'《\s*(?:\d+\s*)?([^《》\d+\-]+?)\s*(?:[+\-]?\s*\d+)?\s*(?:《[^》]*》)?\s*》', s):   # a keyword effect executed as this step (《세이브》, 《1 드로우》…)
        if not re.search(r'(?:을|를|과|와)\s*(?:얻|준|가진|갖)', s[s.find(k):s.find(k) + 40]):
            acts.append('키워드 실행: ' + k.strip())
    q = re.search(r'(\d+)\s*(마리|장|명)(까지)?', s)
    if re.search(r'전부', s): scope = '전체 처리'
    elif q: scope = '단일 처리' + ('(최대)' if q.group(3) else '')
    elif re.search(r'이 (?:디지몬|카드|테이머)', s): scope = '자신(이 카드)'
    else: scope = ''
    player = '자신' if re.search(r'^자신은|[ ,]자신은', s) else ('상대' if re.search(r'^상대는|[ ,]상대는', s) else ('서로' if '서로는' in s else ''))
    dur = next((d for d, p in [('턴 종료까지', r'(?<!상대의 )턴 종료까지|이 턴 동안|이번 턴 동안'), ('상대의 턴 종료까지', r'상대의 턴 종료까지'),
                               ('어택 종료까지', r'어택 (?:종료까지|동안)'), ('배틀 동안', r'배틀 동안')] if re.search(p, s)), '')
    tg = next((n for n, p in [('디지몬·테이머', r'디지몬\s*(?:/|또는)\s*테이머'), ('시큐리티 디지몬', r'시큐리티 디지몬'), ('테이머', r'테이머 ?\d+ ?(?:명|마리|장)|테이머 전부|테이머를'),
                               ('옵션 카드', r'옵션 카드'), ('시큐리티', r'시큐리티(?:를|의|에서| 위| 아래)'), ('디지몬', r'디지몬 ?\d+ ?마리|디지몬 전부|디지몬을|디지몬에게'),
                               ('카드', r'카드 ?\d+ ?장|카드를')] if re.search(p, s)), '')
    side = '상대' if re.search(r'상대의? (?:[^ ,.]{0,15} )?(?:디지몬|테이머|시큐리티|패|트래시)', s) else ('자신' if re.search(r'자신의? (?:[^ ,.]{0,15} )?(?:디지몬|테이머|시큐리티|패|트래시|덱)', s) else ('이 카드' if re.search(r'이 (?:디지몬|카드|테이머)', s) else ''))
    filt = [n for n, p in [('등장 코스트 이하', r'등장 코스트 ?\d+ ?이하'), ('등장 코스트 이상', r'등장 코스트 ?\d+ ?이상'), ('DP 이하', r'DP ?\d+ ?이하'), ('DP 이상', r'DP ?\d+ ?이상'),
                           ('Lv 이하', r'Lv\.\s?\d+ ?이하'), ('Lv 이상', r'Lv\.\s?\d+ ?이상'), ('Lv 지정', r'Lv\.\s?\d+(?:의|인)'), ('사용 코스트', r'사용 코스트 ?\d+'),
                           ('특징 지정', r'특징(?:으로|에|을)? ?「'), ('명칭 지정', r'명칭에 ?「|「[^」]+」 ?\d+ ?(?:장|마리)'), ('색 지정', r'(?:레드|블루|옐로|그린|블랙|퍼플|화이트)(?:인|의)'),
                           ('진화원 조건', r'진화원(?:을|이)? ?(?:갖지 않|없는|\d+장)'), ('레스트 상태', r'레스트 상태인'), ('가장 높은/낮은', r'가장 (?:높|낮)')] if re.search(p, s)]
    return {'text': s, 'acts': acts, 'target': tg, 'side': side, 'filters': filt, '임의': bool(re.search(r'수 있다|수 있으며|해도 된다|놓을 수|선택할 수', s)), 'scope': scope, 'player': player, 'dur': dur,
            '정보 추가': bool(re.search(r'(?:로|으로)도 취급', s)), '정보 변경': bool(re.search(r'(?:으로|로) 변경(?:한다|하고)', s)),
            '효과 부여': bool(re.search(r'효과를 (?:얻|주|부여)|》(?:을|를|과)?\s*(?:얻|준)', s)), '치환': bool(re.search(r'대신', s))}

def analyse(u):
    t = u['ntext']; kind = u['kind']; out = {'card': u['card'], 'where': u['where'], 'text': u['text']}
    # 출처
    out['출처'] = {'진화원 효과': '진화원 효과', '시큐리티 효과': '시큐리티 효과'}.get(u['where'], '효과(상단 텍스트)' if u['where'] == '상단' else '하단 텍스트')
    if kind.startswith('특수 진화 조건') or kind in ('디지크로스', '어셈블리', '카드 고유 룰', '링크'):
        out['분류'] = '카드 정보(효과 아님)'; out['세부'] = kind; out['타이밍'] = []; out['아이콘'] = []; out['유발 조건'] = ''; out['유발 키'] = ''
        out['처리 조건'] = []; out['임의 처리 조건'] = []; out['처리'] = []
        return out
    t = re.sub(r'^진화\s*:\s*「[^」]+」에서\s*\d+\s*', '', t)          # old-format evolution condition glued to the effect
    m = TIMING_RUN.match(t); run = m.group(0) if m else ''
    timing = [x.strip() for x in re.findall(r'【([^】]+)】', run)]
    icons = [re.sub(r'[\[\]{}〔〕]', '', x) for x in re.findall(LIM, run)]
    body = t[len(run):] if run else t
    if kind == '키워드 능력' and not timing:
        out.update({'분류': '키워드 효과', '세부': ' / '.join(u['keywords']), '타이밍': [], '아이콘': icons, '유발 조건': '', '유발 키': '',
                    '처리 조건': [], '임의 처리 조건': [], '처리': []})
        return out
    kws = re.findall(r'《\s*([^《》\d+\-]+?)\s*(?:[+\-]?\s*\d+)?\s*(?:《[^》]*》)?\s*》', body)
    body = KW_NOTE.sub(lambda m_: m_.group(1), body)             # reminder text is not part of this effect's structure
    tset = set(timing)
    # an effect that already has a trigger/activation timing keeps any inner '~할 때' as part of its processing
    clause, tense = (None, None) if tset & (TRIGGER_TIMINGS | ACTIVATE_TIMINGS) else trigger_clause(body)
    if tset & ACTIVATE_TIMINGS: cls = '기동형'
    elif tset & TRIGGER_TIMINGS: cls = '유발형'
    elif clause: cls = tense
    else: cls = '상재형'
    if cls == '기동형' and clause and tense == '즉시형': cls = '즉시형'   # 【카운터】-style interrupts written as '~할 때'
    rest = body
    if clause:
        bq = strip_quotes(body); i = bq.find(clause)
        if i >= 0: rest = bq[i + len(clause):]
    else:
        rest = strip_quotes(body)
    conds = [c.strip() for c in COND_RE.findall(rest)]
    costs = []
    for m_ in re.finditer(r'것으로', rest):   # whole cost clause: back to the previous sentence end or condition
        st = rest.rfind('.', 0, m_.start()) + 1
        for c in conds:
            j = rest.find(c, st, m_.start())
            if j >= 0: st = max(st, j + len(c) + 1)
        costs.append(rest[st:m_.end()].strip(' ,'))
    proc = rest
    for c in conds + costs: proc = proc.replace(c, ' ', 1)
    steps = [step_info(s) for s in steps_of(proc)]
    steps = [s for s in steps if s['acts'] or s['scope'] or s['정보 추가'] or s['정보 변경'] or s['효과 부여'] or s['치환']]
    out.update({'키워드': sorted(set(k.strip() for k in kws)), '분류': cls, '세부': '', '타이밍': timing, '아이콘': icons, '유발 조건': clause or '', '유발 키': trigger_key(clause) if clause else '',
                '처리 조건': conds, '임의 처리 조건': [{'text': c, 'acts': [n for n, p in ACT if p.search(c)] or (['코스트 지불'] if '코스트' in c else [])} for c in costs],
                '처리': steps})
    return out

if __name__ == '__main__':
    U = json.load(open('units3.json', encoding='utf-8'))
    S = [analyse(u) for u in U]
    json.dump(S, open('struct.json', 'w', encoding='utf-8'), ensure_ascii=False)
    c = collections.Counter(s['분류'] for s in S); print('분류', c.most_common())
    print('유발형/즉시형 중 유발 키 있음', sum(1 for s in S if s['분류'] in ('유발형', '즉시형') and s['유발 키']), '/ 타이밍 없이 문장으로 유발', sum(1 for s in S if s['분류'] in ('유발형', '즉시형') and not s['타이밍']))
    print('처리 조건 있는 효과', sum(1 for s in S if s['처리 조건']), ' 임의 처리 조건', sum(1 for s in S if s['임의 처리 조건']), ' 처리 0단계', sum(1 for s in S if s['분류'] not in ('카드 정보(효과 아님)', '키워드 효과') and not s['처리']))
    print('처리 단계 수 분포', collections.Counter(min(len(s['처리']), 5) for s in S if s['분류'] not in ('카드 정보(효과 아님)', '키워드 효과')))
    print('즉시형 예', [s['유발 조건'] for s in S if s['분류'] == '즉시형'][:8])
