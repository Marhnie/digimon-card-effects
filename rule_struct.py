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

ACT = [(n, p) for n, p in ACTIONS if n not in ('코스트 무료',)] + [('코스트 감소', re.compile(r'코스트를\s*-\s*\d')), ('어택 종료', re.compile(r'어택을 종료')), ('금지', re.compile(r'(?:할|될|받을|놓을|시킬) 수 없|하지 않는다$')),
       ('룰 변경', re.compile(r'조건이[^.]{0,30}(?:된다|한다)')), ('디지크로스 확장', re.compile(r'디지크로스로')),
       ('상한·수치 변경', re.compile(r'경감 수치')), ('코스트 증가', re.compile(r'코스트\s*\+\s*\d')), ('선택', re.compile(r'선택한다|선택할 수(?! 있는)')),
       ('시큐리티 추가', re.compile(r'시큐리티 (?:위|아래)에 (?:앞면으로 |뒷면으로 )?놓')), ('금지', re.compile(r'만 \S+ 수 있다')),
       ('선언', re.compile(r'선언한다|선언할 수')), ('덱으로 되돌림', re.compile(r'덱 (?:위|아래)(?: 또는 (?:위|아래))?로 되돌')),
       ('시큐리티 추가', re.compile(r'시큐리티(?:의)? (?:위|아래)(?: 또는 (?:위|아래))?에\s*(?:뒤집어서? |앞면으로 |뒷면으로 )+놓')), ('시큐리티 추가', re.compile(r'시큐리티로 (?:되돌|돌려)')), ('등장', re.compile(r'등장시키거나')), ('진화원에 놓기', re.compile(r'진화원 (?:위|아래)에 [^.,]{0,14}놓|(?:디지몬|테이머) 아래에 놓')), ('소멸', re.compile(r'(?:시, |시 )소멸한다')), ('어택 금지', re.compile(r'어택과 블록을 할 수 없')), ('어플 합체', re.compile(r'어플 합체')), ('공개', re.compile(r'오픈(?:한다|하고|하여|할|해|하는)'))]   # 「~으로만 진화할 수 있다」 = restriction
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
COND_RE = re.compile(r'([^,.]*?(?:라면|다면|경우|' + DUR_NOT + r' 동안|' + STATE_WHEN + r' 때))[,，]')
COND3_RE = re.compile(r'((?:\d+색|DP ?\d+|Lv\.?\s?\d+) ?(?:이상|이하)(?:의|인) 이 디지몬)(?:은|을|의|에게)')
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
            sub = [x.strip(' ,') for x in re.split(r'(?<=[하키리얻주있없]고|으며|하며)[,，]\s*', p)]
            if len(sub) > 1 and all(any(pp.search(x) for _, pp in ACT) or '에게도 어택' in x for x in sub): parts += [sub[0]] + ['⁂' + x for x in sub[1:]]   # ⁂ = continues the previous step's object
            else: parts.append(p)
    return parts

ANAPH = re.compile(r'^[・,\s]*(?:[^,，]{0,24}(?:까지|동안|종료 시)[,，]\s*)?(?:(그중|그 중|나머지는|남은 카드[는를]?|오픈한 카드[는를]?)|((?:고른|선택한|그) (?:디지몬|카드|테이머|시큐리티)|이 효과로 [^\s,]+(?:한|된|시킨) (?:디지몬|카드|테이머)))')   # 「그중 …」「그 디지몬은 …」: the object is the previous step's
STEM = {'등장': '등장', '진화': '진화', '파기': '파기', '소멸': '소멸', '레스트': '레스트', '놓': '놓기'}

def steps_from(text, ctx=()):
    """step_info for every step; a step split off by 「…하고,」 keeps the previous step's target when it names none.
    Anaphoric steps (그중·나머지·그 디지몬·이 효과로 등장한 디지몬) take target/side from the step they refer to; ctx = steps of the cost clause (임의 처리 조건), context only"""
    out = []; prev = list(ctx)
    choose = re.search(r'이하의 효과에서 (\d+)개를 발휘', text)
    for x in steps_of(text):
        cont = x.startswith('⁂'); x = x.lstrip('⁂'); bullet = x.startswith('・'); s = step_info(x)
        if cont and out and not s['target'] and s['side'] in ('', out[-1]['side']) and not set(s['acts']) <= NO_OBJ:
            for f in ('target', 'side', 'scope', 'dur'): s[f] = s[f] or out[-1][f]
        elif cont and out and not s['side'] and out[-1]['side'] and not set(s['acts']) <= NO_OBJ:
            s['side'] = out[-1]['side']
        m = ANAPH.match(x)
        implicit = not m and prev and not s['target'] and not s['side'] and set(prev[-1]['acts']) & {'덱 위 확인', '공개'} and set(s['acts']) & {'패로 회수', '덱으로 되돌림', '파기', '트래시로 보냄', '시큐리티 추가', '배틀 에어리어에 놓기'}
        if (m or implicit) and prev and not set(s['acts']) <= NO_OBJ:
            ref = next((p_ for p_ in reversed(prev) if not set(p_['acts']) <= NO_OBJ), prev[-1])
            if m and m.group(1): ref = next((p_ for p_ in reversed(prev) if set(p_['acts']) & {'덱 위 확인', '공개'}), ref)   # 그중·나머지 refer to the opened cards
            mm = re.match(r'이 효과로 ([^\s,]+?)(?:한|된|시킨) ', (m.group(2) or '') if m else '')
            if mm:
                key = next((v for k, v in STEM.items() if mm.group(1).startswith(k)), None)
                ref = next((p_ for p_ in reversed(prev) if key and any(key in a for a in p_['acts'])), ref)
            if ref in ctx and not mm and '공개' not in ref['acts']: ref = None      # 「그 디지몬은」 right after a cost clause refers to the trigger's subject, not the cost's object
            if ref:
                side = ref['side']
                if mm and side == '이 카드': side = '자신'
                if (implicit or (m and m.group(1))) and not s['target']: s['target'] = '카드'
                if not s['target']: s['target'] = ref['target'] if not (ref['target'] == '시큐리티' and '시큐리티 추가' in ref['acts']) else ''
                if not s['side'] or (s['side'] == '이 카드' and mm): s['side'] = side
        if choose and bullet: s['선택지'] = '택%s' % choose.group(1)                  # 「이하의 효과에서 1개를 발휘한다」 ・A ・B : only N of the bulleted steps happens
        out.append(s)
        if s['acts'] or s['scope']: prev.append(s)
    return out

NO_OBJ_STRICT = {'메모리 증가', '메모리 감소', '메모리 설정', '드로우', '키워드 실행: 드로우', '코스트 감소', '코스트 증가'}
NO_OBJ = {'메모리 증가', '메모리 감소', '메모리 설정', '드로우', '키워드 실행: 드로우', '코스트 감소', '코스트 증가', '상한·수치 변경'}   # steps whose action takes no object (no target/side to inherit)
WHEN_CLAUSE = re.compile(r'^.*?(?:았|었|했|였|졌|됐|되었|시켰)을 때[,，]\s*(?=\S)')                      # 「…하지 않았을 때, 이 디지몬을 …」: the clause is a condition, not the object
BASIS = re.compile(r'[^,，.]*합계[^,，.]*되도록[,，]?\s*')                                    # 「등장 코스트 합계가 …이하가 되도록,」 : a comparison basis, not a filter
PASSIVE = re.compile(r'상대의 (?:디지몬|카드|테이머)의 효과|상대의 효과|상대의 (?:디지몬|카드|테이머) 효과')    # the effect's source, not the object
RELCL = re.compile(r'이 효과로 [^\s,]+(?:한|된|시킨|당한)(?= )')
SUBWHEN = re.compile(r'(?:[^\s,]+ )*?\S+(?:할|될) 때에?(?=[ ,])')                                             # a leftover 「…진화할 때」 condition inside a step: its verb is not an action of the step
NOUN = r'(?:디지몬|테이머|시큐리티|패|트래시|덱|「X」|육성 에어리어|배틀 에어리어)'

def step_info(s):
    s_core = WHEN_CLAUSE.sub('', s)                                           # 「…하지 않았을 때, 이 디지몬을 액티브로 한다」: judge object/side/filters on the main clause
    s_t = s_core
    if re.search(r'(?:마다|\d(?:마리|명|장)당)[,，]?\s', s_core):                                      # 「상대의 디지몬 1마리마다, 이 디지몬은 …」: target follows 마다; 「…1마리를 …1장마다 DP -1000」: the object is before 마다
        before, after = re.split(r'마다|(?<=\d마리)당|(?<=\d명)당|(?<=\d장)당', s_core, 1)
        mo = re.match(r'(.*?\d+\s*(?:마리|명|장)\s*(?:을|를|은|는|에게))', before)
        s_t = mo.group(1) if mo and not re.search(NOUN + r'|이 (?:디지몬|카드|테이머)|\d+\s*(?:마리|명|장)', after) else after
    s_t = re.sub(r'^[^,，]*?턴 ?종료 ?(?:시 ?)?까지,?\s*', '', s_t)               # the duration phrase 「상대의 턴 종료까지」 is not an object
    s_t = BASIS.sub('', s_t).strip()
    s_t = PASSIVE.sub('효과', s_t)
    sa = SUBWHEN.sub('', RELCL.sub('', s_core))                               # action matching ignores 「이 효과로 진화한 …」 and 「…진화할 때」
    acts = list(dict.fromkeys(n for n, p in ACT if p.search(sa)))
    if re.search(r'뒤집어서? 놓', s) and '시큐리티 추가' in acts: acts = [a for a in acts if a != '시큐리티 공개·확인']
    if '덱 위 확인' in acts: acts = [a for a in acts if a != '공개']
    if re.search(r'어택시킨다|어택시킬', s): acts = [a for a in acts if a != '추가 어택'] + ['강제 어택']
    if re.search(r'에게도 어택', s): acts = [a for a in acts if a != '추가 어택'] + ['어택 대상 확장']
    for k in re.findall(r'《\s*(?:\d+\s*)?([^《》\d+\-]+?)\s*(?:[+\-]?\s*\d+)?\s*(?:《[^》]*》)?\s*》', s):   # a keyword effect executed as this step (《세이브》, 《1 드로우》…)
        if k.strip() not in ('덱', '트래시', '시큐리티', '패') and not re.search(r'(?:을|를|과|와)\s*(?:얻|준|주|가진|갖)', s[s.find(k):s.find(k) + 40]):   # 《리커버리 +1 《덱》》: 《덱》 is a parameter
            acts.append('키워드 실행: ' + k.strip())
    q = re.search(r'(\d+)\s*(마리|장|명)(까지)?', s_t)
    if re.search(r'전부', s_t): scope = '전체 처리'
    elif q: scope = '단일 처리' + ('(최대)' if q.group(3) else '')
    elif re.search(r'이 (?:디지몬|카드|테이머)', s_t): scope = '자신(이 카드)'
    else: scope = ''
    player = '자신' if re.search(r'^자신은|[ ,]자신은', s_core) else ('상대' if re.search(r'^상대는|[ ,]상대는', s_core) else ('서로' if '서로는' in s_core else ''))
    dur = next((d for d, p in [('다음 상대의 턴 종료까지', r'다음 상대의 턴 ?종료'), ('턴 종료까지', r'(?<!상대의 )턴 ?종료까지|이 턴 동안|이번 턴 동안'), ('상대의 턴 종료까지', r'상대의 턴 ?종료까지'),
                               ('어택 종료까지', r'어택 (?:종료까지|동안)'), ('배틀 동안', r'배틀 동안'), ('다음 상대의 액티브 페이즈까지', r'다음 상대의 액티브 페이즈')] if re.search(p, s)), '')
    TG = [('디지몬·테이머', r'디지몬\s*(?:/|또는|과|와)\s*(?:자신의 |상대의 )?테이머|디지몬 또는[^,.]{0,25}테이머'), ('디지몬·시큐리티 디지몬', r'디지몬과 시큐리티 디지몬'), ('시큐리티 디지몬', r'시큐리티 디지몬'), ('테이머', r'테이머 ?\d+ ?(?:명|마리|장)|테이머 전부|테이머를'),
          ('옵션 카드', r'옵션 카드'), ('시큐리티', r'시큐리티(?:를|의|에서| 위| 아래)'), ('디지몬', r'디지몬 ?\d+ ?마리|디지몬 전부|디지몬을|디지몬에게|「X」 ?\d+ ?마리'),
          ('카드', r'카드 ?\d+ ?장|카드를')]
    cands = [n for n, p in TG if re.search(p, s_t)]
    if cands[:1] == ['시큐리티'] and len(cands) > 1 and re.search(r'시큐리티(?:의)? (?:위|아래)(?: 또는 (?:위|아래))?에', s_t): cands = cands[1:]   # 「디지몬 1마리를 시큐리티 위에 놓는다」: the object is the card moved, the security is where it goes
    tg = cands[0] if cands else ''
    if re.search(r'^상대는|[ ,]상대는', s_t) and not re.search(r'자신의', s_t): s_t = '상대의 ' + s_t   # 「상대는 본인의 디지몬 …」
    sq = re.search(r'(상대|자신)의? (?:(?!자신|상대)[^ ,.]{0,15} ){0,3}?(?:' + NOUN[3:-1] + r')\s*\d+\s*(?:마리|명|장)\s*(?:을|를|은|는|에게|까지|씩|\()', s_t)
    side = sq.group(1) if sq else '양쪽' if re.search(r'(?<![상자][대신]의 )(?<!이 )(?<!고른 )(?<!선택한 )(?<!그 )디지몬 전부', s_t) and not re.search(r'(상대|자신)의?[^,.]{0,20}디지몬 전부', s_t) else '상대' if re.search(r'상대의? (?:(?!자신)[^ ,.]{0,15} )?' + NOUN, s_t) else ('자신' if re.search(r'자신의? (?:(?!상대)[^ ,.]{0,15} )?' + NOUN, s_t) else ('이 카드' if re.search(r'이 (?:디지몬|카드|테이머)', s_t) else ''))
    FILT = [('등장 코스트 이하', r'등장 코스트 ?\d+ ?이하'), ('등장 코스트 이상', r'등장 코스트 ?\d+ ?이상'), ('DP 이하', r'DP ?\d+ ?이하|DP 이하(?:의|인)'), ('DP 이상', r'DP ?\d+ ?이상'),
            ('Lv 이하', r'Lv\.\s?\d+ ?이하'), ('Lv 이상', r'Lv\.\s?\d+ ?이상'), ('Lv 지정', r'Lv\.\s?\d+(?:의|인)'), ('사용 코스트', r'사용 코스트 ?\d+'),
            ('특징 지정', r'특징(?:으로|에|을)? ?「'), ('명칭 지정', r'명칭에 ?「|「[^」]+」 ?\d+ ?(?:장|마리)'), ('색 지정', r'(?:레드|블루|옐로|그린|블랙|퍼플|화이트)(?:인|의)'),
            ('진화원 조건', r'진화원(?:을|이)? ?(?:갖지 않|없는|\d+장)'), ('레스트 상태', r'레스트 상태인'), ('액티브 상태', r'액티브 상태(?:인|의)'),
            ('가장 높은/낮은', r'가장 [^,，]{0,14}?(?:높|낮|많|적)은'), ('키워드 미보유', r'》(?:\s*\([^)]*\))?(?:을|를)\s*(?:갖지|가지지) 않'), ('키워드 보유', r'》(?:을|를)\s*(?:가진|가지는|갖는) (?:상대|자신|다른|디지몬)')]
    filt = [n for n, p in FILT if re.search(p, s_t)]
    if player == '서로' and not side: side = '양쪽'
    if acts and set(acts) <= NO_OBJ_STRICT:                                              # 메모리·드로우·코스트 증감: no object, so no target/side/filter (they came from the condition fragment)
        tg, side, filt = '', '', []
        if scope == '자신(이 카드)': scope = ''
    return {'text': s, 'acts': acts, 'target': tg, 'side': side or ('상대' if player == '상대' else ''), 'filters': filt, '임의': bool(re.search(r'수 있다|수 있고|수 있으며|해도 된다|놓을 수|선택할 수(?! 있는)', s)) and not re.search(r'만 \S+ 수 있다', s), 'scope': scope, 'player': player, 'dur': dur,
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
        mm = re.match(r'(〔[^〕]+〕.*?코스트\s*\d+(?:\s*/\s*[^/]*?코스트\s*\d+)*\s*(?:지정된 디지몬 \d마리를 겹쳐 (?:액티브로 |레스트로 )?진화시킨다\.?|\d종의 카드에 의해 링크 상태라면, 링크 카드를 위에 겹쳐 진화시킨다)?)\s*(\S.*)$', t)
        if mm and (re.search(r'때[,，]|【', mm.group(2)) or mm.group(2).startswith('《')):
            rem = mm.group(2); kw = re.findall(r'《\s*([^《》\d+\-]+?)\s*(?:[+\-]?\s*\d+)?\s*》', rem)
            sub = analyse({**u, 'kind': '키워드 능력' if rem.startswith('《') else '효과', 'ntext': rem, 'keywords': kw})
            sub['카드 정보'] = mm.group(1)   # the evolution condition in front stays card info (2-3), not part of this effect
            return sub
    if kind.startswith('특수 진화 조건') or kind in ('디지크로스', '어셈블리', '카드 고유 룰', '링크'):
        out['분류'] = '카드 정보(효과 아님)'; out['세부'] = kind; out['타이밍'] = []; out['아이콘'] = []; out['유발 조건'] = ''; out['유발 키'] = ''
        out['처리 조건'] = []; out['임의 처리 조건'] = []; out['처리'] = []
        return out
    rule_note = re.search(r'\s*<룰>.*$', t)                                      # 「<룰>특징: 유형 …」 is a card rule note, not part of the effect
    if rule_note: out['룰 문구'] = rule_note.group(0).strip(); t = t[:rule_note.start()]
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
    if kind == '키워드 능력' and not timing and u['keywords'] and all(k.startswith('오버플로우') for k in u['keywords']):
        out.update({'분류': '카드 정보(효과 아님)', '세부': '오버플로우(4-19)', '타이밍': [], '아이콘': [], '유발 조건': '', '유발 키': '', '처리 조건': [], '임의 처리 조건': [], '처리': [], '부가 효과': extra})
        return restore(out)
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
            pm = re.search(r'([^,.]*?(?:거나|에|이며|하고|이고|있고|가지고))[,，]\s*$', rest[:st])
            if not pm or (re.search(r'(?:하고|이고|있고|가지고)$', pm.group(1)) and any(pp.search(pm.group(1)) for _, pp in ACT)): break   # 「…포함하고, 〜라면」 continues the condition; 「…오픈하고, 〜라면」 does not
            c = pm.group(1) + ', ' + c.lstrip(); st = pm.start(1)
        conds.append(c.strip())
    conds += [c.strip() for c in COND2_RE.findall(rest) if c.strip() not in conds and not any(c.strip() in x for x in conds)]
    conds += [c + '인 동안(수식어)' for c in COND3_RE.findall(rest) if not any(c in x for x in conds)]
    costs = []
    for m_ in re.finditer(r'것으로', rest):   # whole cost clause: back to the previous sentence end or condition
        st = max(rest.rfind('.', 0, m_.start()), rest.rfind('・', 0, m_.start())) + 1   # 《딜레이》 ・… : the bullet starts the delayed effect
        for c in conds:
            j = rest.find(c, st, m_.start())
            if j >= 0: st = max(st, j + len(c) + 1)
        costs.append(rest[st:m_.end()].strip(' ,・'))
    proc = rest
    for c in conds + costs: proc = proc.replace(c, ' ', 1)
    steps = steps_from(proc, [step_info(c) for c in costs])
    for s in steps:
        if any(a == '키워드 실행: ' + k for a in s['acts'] for k in OPT_KW): s['임의'] = True
        if s['dur'] == '상대의 턴 종료까지' and '다음 상대의 턴 종료' in u['text']: s['dur'] = '다음 상대의 턴 종료까지'   # normalisation dropped 「다음」
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
