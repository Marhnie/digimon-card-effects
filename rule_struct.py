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
       ('룰 변경', re.compile(r'조건이[^.]{0,30}(?:된다|한다)')), ('디지크로스 확장', re.compile(r'디지크로스로')),
       ('상한·수치 변경', re.compile(r'경감 수치')), ('코스트 증가', re.compile(r'코스트\s*\+\s*\d')), ('선택', re.compile(r'선택한다|선택할 수')),
       ('시큐리티 추가', re.compile(r'시큐리티 (?:위|아래)에 (?:앞면으로 |뒷면으로 )?놓')), ('금지', re.compile(r'만 \S+ 수 있다')),
       ('선언', re.compile(r'선언한다|선언할 수')), ('덱으로 되돌림', re.compile(r'덱 (?:위|아래)(?: 또는 (?:위|아래))?로 되돌'))]   # 「~으로만 진화할 수 있다」 = restriction
OPT_KW = {'블래스트 진화', '블래스트 조그레스', '세이브'}   # keyword processings whose rule text is optional ('…할 수 있다')
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
        for n, p in [('상대 디지몬 소멸시킴', r'소멸시켰'), ('어택 대상 변경됨', r'대상이 변경'), ('소멸함', r'소멸할'), ('진화함', r'진화할'), ('등장함', r'등장(?:할|시킬)'), ('벗어남', r'벗어날|떠날'), ('되돌아감', r'(?:되)?돌아갈'),
                     ('파기됨', r'파기(?:될|할)'), ('사용함', r'사용할'), ('어택함', r'어택할'), ('디지크로스함', r'디지크로스할')]:
            if re.search(p, c): ev = n; break
    if not ev: return ''
    return ' · '.join(x for x in (pick(SUBJ), pick(PLACE), pick(CAUSE), ev) if x)

DUR_NOT = r'(?<!턴)(?<!배틀)(?<!어택)(?<!이 턴)'
COND_RE = re.compile(r'([^,.]*?(?:라면|다면|' + DUR_NOT + r' 동안|' + STATE_WHEN + r' 때))[,，]')
COND2_RE = re.compile(r'([^,.]*?(?:라면|다면|' + DUR_NOT + r' 동안))\s+(?=[^\s,.])')
COST_RE = re.compile(r'([^,.]*?것으로)[,，]?')

def steps_of(body):
    """processing steps in written order (15-1-2): split on sentences and '그 후'"""
    parts = []
    body = body.replace('Lv.', 'Lv․')
    for sent in re.split(r'(?<=[.。])\s*', body):
        for p in re.split(r'그 후[,，]?\s*', sent):
            p = re.sub(r'^또한[,，]?\s*', '', p.strip(' ,.')).replace('Lv․', 'Lv.')
            if not p: continue
            sub = [x.strip(' ,') for x in re.split(r'(?<=[하키리얻주]고)[,，]\s*', p)]
            if len(sub) > 1 and all(any(pp.search(x) for _, pp in ACT) for x in sub): parts += [sub[0]] + ['⁂' + x for x in sub[1:]]   # ⁂ = continues the previous step's object
            else: parts.append(p)
    return parts

def steps_from(text):
    """step_info for every step; a step split off by 「…하고,」 keeps the previous step's target when it names none"""
    out = []
    for x in steps_of(text):
        cont = x.startswith('⁂'); s = step_info(x.lstrip('⁂'))
        if cont and out and not s['target'] and s['side'] in ('', out[-1]['side']):
            for f in ('target', 'side', 'scope', 'dur'): s[f] = s[f] or out[-1][f]
        out.append(s)
    return out

def step_info(s):
    s_t = s.split('마다', 1)[1] if re.search(r'마다[,，]?\s', s) else s   # 「상대의 디지몬 1마리마다, 이 디지몬은 …」: target follows 마다
    acts = list(dict.fromkeys(n for n, p in ACT if p.search(s)))
    if re.search(r'에게도 어택', s): acts = [a for a in acts if a != '추가 어택'] + ['어택 대상 확장']
    for k in re.findall(r'《\s*(?:\d+\s*)?([^《》\d+\-]+?)\s*(?:[+\-]?\s*\d+)?\s*(?:《[^》]*》)?\s*》', s):   # a keyword effect executed as this step (《세이브》, 《1 드로우》…)
        if not re.search(r'(?:을|를|과|와)\s*(?:얻|준|가진|갖)', s[s.find(k):s.find(k) + 40]):
            acts.append('키워드 실행: ' + k.strip())
    q = re.search(r'(\d+)\s*(마리|장|명)(까지)?', s_t)
    if re.search(r'전부', s): scope = '전체 처리'
    elif q: scope = '단일 처리' + ('(최대)' if q.group(3) else '')
    elif re.search(r'이 (?:디지몬|카드|테이머)', s_t): scope = '자신(이 카드)'
    else: scope = ''
    player = '자신' if re.search(r'^자신은|[ ,]자신은', s) else ('상대' if re.search(r'^상대는|[ ,]상대는', s) else ('서로' if '서로는' in s else ''))
    dur = next((d for d, p in [('턴 종료까지', r'(?<!상대의 )턴 종료까지|이 턴 동안|이번 턴 동안'), ('상대의 턴 종료까지', r'상대의 턴 종료까지'),
                               ('어택 종료까지', r'어택 (?:종료까지|동안)'), ('배틀 동안', r'배틀 동안')] if re.search(p, s)), '')
    tg = next((n for n, p in [('디지몬·테이머', r'디지몬\s*(?:/|또는|과|와)\s*테이머'), ('시큐리티 디지몬', r'시큐리티 디지몬'), ('테이머', r'테이머 ?\d+ ?(?:명|마리|장)|테이머 전부|테이머를'),
                               ('옵션 카드', r'옵션 카드'), ('시큐리티', r'시큐리티(?:를|의|에서| 위| 아래)'), ('디지몬', r'디지몬 ?\d+ ?마리|디지몬 전부|디지몬을|디지몬에게'),
                               ('카드', r'카드 ?\d+ ?장|카드를')] if re.search(p, s_t)), '')
    sq = re.search(r'(상대|자신)의? (?:[^ ,.]{0,15} ){0,3}?(?:디지몬|테이머|카드)\s*\d+\s*(?:마리|명|장)\s*(?:을|를|은|는|에게|까지|씩|\()', s_t)
    side = sq.group(1) if sq else '상대' if re.search(r'상대의? (?:[^ ,.]{0,15} )?(?:디지몬|테이머|시큐리티|패|트래시)', s_t) else ('자신' if re.search(r'자신의? (?:[^ ,.]{0,15} )?(?:디지몬|테이머|시큐리티|패|트래시|덱)', s_t) else ('이 카드' if re.search(r'이 (?:디지몬|카드|테이머)', s_t) else ''))
    filt = [n for n, p in [('등장 코스트 이하', r'등장 코스트 ?\d+ ?이하'), ('등장 코스트 이상', r'등장 코스트 ?\d+ ?이상'), ('DP 이하', r'DP ?\d+ ?이하'), ('DP 이상', r'DP ?\d+ ?이상'),
                           ('Lv 이하', r'Lv\.\s?\d+ ?이하'), ('Lv 이상', r'Lv\.\s?\d+ ?이상'), ('Lv 지정', r'Lv\.\s?\d+(?:의|인)'), ('사용 코스트', r'사용 코스트 ?\d+'),
                           ('특징 지정', r'특징(?:으로|에|을)? ?「'), ('명칭 지정', r'명칭에 ?「|「[^」]+」 ?\d+ ?(?:장|마리)'), ('색 지정', r'(?:레드|블루|옐로|그린|블랙|퍼플|화이트)(?:인|의)'),
                           ('진화원 조건', r'진화원(?:을|이)? ?(?:갖지 않|없는|\d+장)'), ('레스트 상태', r'레스트 상태인'), ('가장 높은/낮은', r'가장 (?:높|낮)')] if re.search(p, s)]
    return {'text': s, 'acts': acts, 'target': tg, 'side': side, 'filters': filt, '임의': bool(re.search(r'수 있다|수 있으며|해도 된다|놓을 수|선택할 수', s)) and not re.search(r'만 \S+ 수 있다', s), 'scope': scope, 'player': player, 'dur': dur,
            '정보 추가': bool(re.search(r'(?:로|으로)도 취급', s)), '정보 변경': bool(re.search(r'(?:으로|로) 변경(?:한다|하고)', s)),
            '효과 부여': bool(re.search(r'효과를 (?:얻|주|부여)|》(?:을|를|과)?\s*(?:얻|준)', s)), '치환': bool(re.search(r'대신', s))}

def restore(o):
    if isinstance(o, str): return o.replace('Lv․', 'Lv.')
    if isinstance(o, list): return [restore(x) for x in o]
    if isinstance(o, dict): return {k: restore(v) for k, v in o.items()}
    return o

def analyse(u):
    t = u['ntext']; kind = u['kind']; out = {'card': u['card'], 'where': u['where'], 'text': u['text']}
    # 출처
    out['출처'] = {'진화원 효과': '진화원 효과', '시큐리티 효과': '시큐리티 효과'}.get(u['where'], '효과(상단 텍스트)' if u['where'] == '상단' else '하단 텍스트')
    if kind.startswith('특수 진화 조건'):
        mm = re.match(r'(〔[^〕]+〕.*?코스트\s*\d+(?:\s*/\s*[^/]*?코스트\s*\d+)*\s*(?:지정된 디지몬 \d마리를 겹쳐 (?:액티브로 |레스트로 )?진화시킨다\.?)?)\s*(\S.*)$', t)
        if mm and (re.search(r'때[,，]|【', mm.group(2)) or mm.group(2).startswith('《')):
            rem = mm.group(2); kw = re.findall(r'《\s*([^《》\d+\-]+?)\s*(?:[+\-]?\s*\d+)?\s*》', rem)
            sub = analyse({**u, 'kind': '키워드 능력' if rem.startswith('《') else '효과', 'ntext': rem, 'keywords': kw})
            sub['카드 정보'] = mm.group(1)   # the evolution condition in front stays card info (2-3), not part of this effect
            return sub
    if kind.startswith('특수 진화 조건') or kind in ('디지크로스', '어셈블리', '카드 고유 룰', '링크'):
        out['분류'] = '카드 정보(효과 아님)'; out['세부'] = kind; out['타이밍'] = []; out['아이콘'] = []; out['유발 조건'] = ''; out['유발 키'] = ''
        out['처리 조건'] = []; out['임의 처리 조건'] = []; out['처리'] = []
        return out
    t = re.sub(r'^[-―ー]\s+', '', t.strip())                                  # stray list dash before the effect
    if re.fullmatch(r'[-―ー\s]*', t) or t.startswith('■') or re.match(r'^《진화\s*:', t):
        sub = '효과 없음(―)' if re.fullmatch(r'[-―ー\s]*', t) else ('토큰 룰' if t.startswith('■') else '특수 진화 조건(옛 표기)')
        out.update({'분류': '카드 정보(효과 아님)', '세부': sub, '타이밍': [], '아이콘': [], '유발 조건': '', '유발 키': '', '처리 조건': [], '임의 처리 조건': [], '처리': []})
        return out
    t = re.sub(r'^진화\s*:\s*(?:『[^』]+』|「[^」]+」)에서\s*\d+\s*', '', t)   # old-format evolution condition glued to the effect
    t = re.sub(r'」\s*\((?:디지몬|테이머)・[^()]*\)', '」', t)                   # token stats 「사역마」(디지몬・옐로・DP3000・…) are not a step
    t = t.replace('Lv.', 'Lv․')                                                # protect 'Lv.' from sentence splitting (restored at the end)
    m = TIMING_RUN.match(t); run = m.group(0) if m else ''
    timing = [x.strip() for x in re.findall(r'【([^】]+)】', run)]
    icons = [re.sub(r'[\[\]{}〔〕]', '', x) for x in re.findall(LIM, run)]
    body = t[len(run):] if run else t
    extra = []
    lk = body.split('〈링크 중〉', 1)
    if len(lk) > 1:
        body = lk[0].rstrip()
        extra.append({'분류': '상재형', '조건': '〈링크 중〉', '처리': [s for s in steps_from(lk[1]) if s['acts'] or s['scope']]})
    # (f) a leading 「…동안, 이 카드는 색 조건을 무시할 수 있다.」 sentence is a separate continuous effect
    mc = re.match(r'([^.]*색 조건을 무시(?:하고 사용)?할 수 있다\.)\s*(\S.*)$', body)
    if mc and re.search(r'때[,，]|【', mc.group(2)):
        cs = [c.strip() for c in COND_RE.findall(strip_quotes(mc.group(1)))]
        extra.append({'분류': '상재형', '조건': ' / '.join(cs), '처리': steps_from(mc.group(1))})
        body = mc.group(2)
    if kind == '키워드 능력' and not timing:
        out.update({'분류': '키워드 효과', '세부': ' / '.join(u['keywords']), '타이밍': [], '아이콘': icons, '유발 조건': '', '유발 키': '',
                    '처리 조건': [], '임의 처리 조건': [], '처리': [], '부가 효과': extra})
        return restore(out)
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
    conds = []
    for m_ in COND_RE.finditer(rest):
        c, st = m_.group(1), m_.start(1)
        while True:
            pm = re.search(r'([^,.]*?(?:거나|에|이며))[,，]\s*$', rest[:st])
            if not pm: break
            c = pm.group(1) + ', ' + c.lstrip(); st = pm.start(1)
        conds.append(c.strip())
    conds += [c.strip() for c in COND2_RE.findall(rest) if c.strip() not in conds and not any(c.strip() in x for x in conds)]
    costs = []
    for m_ in re.finditer(r'것으로', rest):   # whole cost clause: back to the previous sentence end or condition
        st = max(rest.rfind('.', 0, m_.start()), rest.rfind('・', 0, m_.start())) + 1   # 《딜레이》 ・… : the bullet starts the delayed effect
        for c in conds:
            j = rest.find(c, st, m_.start())
            if j >= 0: st = max(st, j + len(c) + 1)
        costs.append(rest[st:m_.end()].strip(' ,・'))
    proc = rest
    for c in conds + costs: proc = proc.replace(c, ' ', 1)
    steps = steps_from(proc)
    for s in steps:
        if any(a == '키워드 실행: ' + k for a in s['acts'] for k in OPT_KW): s['임의'] = True
    if '《딜레이》' in body:
        costs.insert(0, '《딜레이》(배틀 에어리어의 이 카드를 파기하는 것으로)')
        for s in steps: s['acts'] = [a for a in s['acts'] if a != '키워드 실행: 딜레이']
    steps = [s for s in steps if s['acts'] or s['scope'] or s['정보 추가'] or s['정보 변경'] or s['효과 부여'] or s['치환']]
    dual = '【' + '】【'.join(x for x in timing if x in TRIGGER_TIMINGS) + '】 유발 겸용' if cls == '기동형' and tset & TRIGGER_TIMINGS else ''
    out.update({'키워드': sorted(set(k.strip() for k in kws)), '분류': cls, '세부': dual, '부가 효과': extra, '타이밍': timing, '아이콘': icons, '유발 조건': clause or '', '유발 키': trigger_key(clause) if clause else '',
                '처리 조건': conds, '임의 처리 조건': [{'text': c, 'acts': [n for n, p in ACT if p.search(c)] or (['코스트 지불'] if '코스트' in c else [])} for c in costs],
                '처리': steps})
    return restore(out)

if __name__ == '__main__':
    U = json.load(open('units3.json', encoding='utf-8'))
    S = [analyse(u) for u in U]
    json.dump(S, open('struct.json', 'w', encoding='utf-8'), ensure_ascii=False)
    c = collections.Counter(s['분류'] for s in S); print('분류', c.most_common())
    print('유발형/즉시형 중 유발 키 있음', sum(1 for s in S if s['분류'] in ('유발형', '즉시형') and s['유발 키']), '/ 타이밍 없이 문장으로 유발', sum(1 for s in S if s['분류'] in ('유발형', '즉시형') and not s['타이밍']))
    print('처리 조건 있는 효과', sum(1 for s in S if s['처리 조건']), ' 임의 처리 조건', sum(1 for s in S if s['임의 처리 조건']), ' 처리 0단계', sum(1 for s in S if s['분류'] not in ('카드 정보(효과 아님)', '키워드 효과') and not s['처리']))
    print('처리 단계 수 분포', collections.Counter(min(len(s['처리']), 5) for s in S if s['분류'] not in ('카드 정보(효과 아님)', '키워드 효과')))
    print('즉시형 예', [s['유발 조건'] for s in S if s['분류'] == '즉시형'][:8])
