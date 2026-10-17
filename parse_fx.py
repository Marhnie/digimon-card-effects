"""Split each card's text into effect units and tag the elements of each unit.

Unit = one independently-triggered piece of text: a timing-led effect (【등장 시】…),
a keyword ability (《블로커》), a special play condition (〔진화〕…, 디지크로스, 어셈블리),
a card rule (〈룰〉), a link block (〈링크〉), or an untimed static sentence.
"""
import json, re, collections

def norm_text(s):
    s = s.replace('≪', '《').replace('≫', '》').replace('｛', '{').replace('｝', '}')
    s = re.sub(r'\s+', ' ', s).strip()
    return '' if s in ('-', 'ー', '－') else s

LIM = r'(?:\[[^\]\n]{1,8}\]|\{[^}\n]{1,4}\}|〔턴[^〕]{0,6}〕)'
TIMING_RUN = re.compile(r'(?:' + LIM + r'\s*)*(?:【[^】]{1,20}】\s*)+(?:' + LIM + r'\s*)*')
BOUNDARY_PREV = set('.。)）》〉」:') | {''}

def quote_depth_map(s):
    d, out = 0, []
    for ch in s:
        if ch == '「': d += 1
        out.append(d)
        if ch == '」': d = max(0, d - 1)
    return out

def unit_starts(s):
    depth = quote_depth_map(s)
    starts = {0}
    for m in TIMING_RUN.finditer(s):
        i = m.start()
        if depth[i] > 0:
            continue
        prev = s[:i].rstrip()[-1:] if s[:i].strip() else ''
        if prev in BOUNDARY_PREV or re.search(r'코스트\s*\d+\s*$', s[:i]) or re.search(r'\d\)$', s[:i].rstrip()):
            starts.add(i)
    for m in re.finditer(r'〔(?!턴)[^〕]+〕|〈(?:룰|링크)〉|디지크로스\s*-\s*\d|어셈블리\s*-\s*\d', s):
        if depth[m.start()] == 0:
            starts.add(m.start())
    # keyword ability standing alone at a sentence boundary: 《블로커》 《S 어택 +1》 …
    for m in re.finditer(r'《', s):
        i = m.start()
        if depth[i] > 0:
            continue
        prev = s[:i].rstrip()[-1:] if s[:i].strip() else ''
        if prev in ('', '.', ')', '）', '》') and not re.search(r'[가-힣]\s*$', s[:i]):
            # skip the inner 《 of a nested keyword like 《리커버리 +1 《덱》》
            if prev == '》' or prev == '' or prev in '.)）':
                starts.add(i)
    return sorted(starts)

def split_units(s):
    if not s:
        return []
    st = unit_starts(s) + [len(s)]
    parts = [s[a:b].strip() for a, b in zip(st, st[1:])]
    out = []
    for p in parts:
        if not p:
            continue
        # glue nested-keyword tails (《리커버리 +1 《덱》》) back on
        if out and (p.startswith('《덱》') or re.match(r'^《[^》]*》》', p)):
            out[-1] += ' ' + p
        else:
            out.append(p)
    return out

KEYWORD_RE = re.compile(r'《\s*([^《》\d+\-]+?)\s*(?:[+\-]?\s*\d+)?\s*(?:《[^》]*》)?\s*》')
def keywords(u):
    ks = []
    for m in KEYWORD_RE.finditer(u):
        k = re.sub(r'\s+', ' ', m.group(1)).strip()
        k = {'시큐리티 어택': 'S 어택', 'S어택': 'S 어택', '블록커': '블로커', '흡수진화': '흡수 진화'}.get(k, k)
        ks.append(k)
    return ks

ACTIONS = [
    ('소멸', r'소멸시킨다|소멸시킬|소멸시키고|를 소멸|을 소멸'),
    ('소멸 내성', r'소멸하지 않는다|소멸되지 않는다|소멸하지 않을|소멸하지 않고'),
    ('레스트', r'레스트시킨다|레스트시킬|레스트시키고|레스트 상태로'),
    ('액티브', r'액티브로 한다|액티브로 할|액티브시킨다|액티브시킬|액티브로 하'),
    ('액티브 금지', r'액티브가 되지 않는다|액티브되지 않는다'),
    ('드로우', r'《\s*\d*\s*드로우|장 드로우|드로우한다|드로우할'),
    ('키워드 부여', r'》[^.]{0,120}?(?:얻는다|얻고|얻을|준다|주고|가진다|갖는다)'),
    ('다른 효과 발휘', r'효과(?: \d+개)?를[^.]{0,20}발휘한다|효과로써 발휘|효과를 발휘할 수 있다'),
    ('되돌림·이탈 내성', r'되돌아가지 않|되돌릴 수 없|벗어나지 않'),
    ('색 조건 무시', r'색 조건을 무시'),
    ('취급 변경', r'(?:로서|으로서|로도|으로도) 취급'),
    ('카드 효과 획득', r'카드의 효과[^.]{0,10}얻는다'),
    ('패로 회수', r'패에 (?:넣|더한|추가)|패로 (?:되돌|돌려|넣)|패에 가한'),
    ('덱으로 되돌림', r'덱(?:의)? (?:맨 )?(?:아래|위)(?:로|에) (?:되돌|돌려|놓)'),
    ('트래시로 보냄', r'트래시(?:에 놓|로 보내|에 버|로 버)|트래시한다'),
    ('시큐리티 추가', r'시큐리티(?:의)? (?:맨 )?(?:위|아래)에 (?:놓|추가|두)|시큐리티에 (?:놓|추가)|《리커버리'),
    ('시큐리티 제거', r'시큐리티(?:를|의)?[^.]{0,20}(?:트래시|파기|줄인다|제거)'),
    ('시큐리티 공개·확인', r'시큐리티[^.]{0,12}(?:공개|확인|뒤집)'),
    ('메모리 증가', r'메모리\s*\+|메모리를\s*\+|메모리 \+'),
    ('메모리 감소', r'메모리\s*-\s*\d|메모리를\s*-'),
    ('메모리 설정', r'메모리를\s*(?:자신|상대)?[^.]{0,6}\d+(?:으로|로)|\d+(?:으로|로) 한다'),
    ('DP 증가', r'DP\s*\+\s*\d|DP를\s*\+'),
    ('DP 감소', r'DP\s*-\s*\d|DP를\s*-'),
    ('코스트 감소', r'코스트\s*-\s*\d|코스트를\s*\d+\s*(?:줄|마이너스)|지불하는 코스트\s*-'),
    ('코스트 무료', r'코스트를 지불하지 않고'),
    ('등장', r'등장시킨다|등장시킬|등장시키고|등장할 수 있다'),
    ('진화', r'진화시킨다|진화시킬|진화시키고|진화할 수 있다|으로 진화|로 진화'),
    ('진화원에 놓기', r'(?:진화원|의 아래|카드 아래)(?:의 (?:위|아래))?에 놓|진화원 아래에 놓|아래에 놓을'),
    ('진화원 제거', r'진화원[^.]{0,25}(?:파기|트래시)'),
    ('퇴화', r'《퇴화|퇴화시킨'),
    ('효과 부여', r'효과를 (?:얻는다|얻고|얻을|준다|주고|부여)|의 효과를 얻|효과를 갖는다'),
    ('효과 발휘 금지', r'발휘하지 않|효과를 잃|효과는 발휘하지|효과가 발휘되지'),
    ('어택 금지', r'어택할 수 없|어택하지 않는다|어택하지 못'),
    ('블록 금지', r'블록할 수 없|블록되지 않|블록당하지 않|블록을 할 수 없'),
    ('배틀 에어리어에 놓기', r'배틀 에어리어에 놓'),
    ('등장 금지', r'등장할 수 없'),
    ('상한·수치 변경', r'상한 [+\-]|상한을'),
    ('추가 어택', r'어택할 수 있다|으로 어택한다|로 어택한다|어택시킨다'),
    ('어택 대상 변경', r'어택(?:의)? 대상을|어택(?:의)? 대상으로'),
    ('공개', r'공개하고|공개한다|공개하여|공개해'),
    ('덱 위 확인', r'덱(?:의)? 위에서 \d+장을 (?:공개|확인)|위에서 \d+장을|위에서부터 \d+장 오픈'),
    ('셔플', r'셔플'),
    ('토큰', r'토큰'),
    ('치환(대신)', r'대신(?:에|하여|해서)?[ ,]|대신 '),
    ('링크', r'링크(?:시킨다|시킬|할 수|한다)'),
    ('부화', r'부화'),
    ('이동', r'이동(?:시킨|시킬|한다|할 수)'),
    ('옵션 사용', r'(?:옵션 카드[^.]{0,15})?사용(?:할 수 있다|한다|하고)'),
    ('파기', r'파기(?:한다|할|하고)'),
    ('배틀시킴', r'배틀시킨|배틀하게'),
    ('효과 무시·내성', r'효과의 영향을 받지 않|효과를 받지 않|영향을 받지 않'),
    ('진화 조건 무시', r'진화 조건을 무시'),
]
ACTIONS = [(n, re.compile(p)) for n, p in ACTIONS]

TARGETS = [
    ('상대 디지몬', r'상대의 (?:Lv\.\d+ (?:이하|이상)의 )?(?:[^ .]{0,10} )?디지몬'),
    ('자신 디지몬', r'자신의 (?:[^ .]{0,10} )?디지몬'),
    ('이 디지몬', r'이 디지몬'),
    ('상대 테이머', r'상대의 [^.]{0,10}테이머'),
    ('자신 테이머', r'자신의 [^.]{0,10}테이머'),
    ('시큐리티 디지몬', r'시큐리티 디지몬'),
    ('패', r'패(?:의|에서|로|에)'),
    ('트래시', r'트래시(?:의|에서)'),
    ('덱', r'덱(?:의|에서)'),
    ('진화원', r'진화원'),
    ('전부', r'전부'),
]
TARGETS = [(n, re.compile(p)) for n, p in TARGETS]

FILTERS = [
    ('Lv 조건', r'Lv\.\d+ ?(?:이하|이상)|Lv\.\d+의'),
    ('DP 조건', r'DP\s?\d+\s?(?:이하|이상)|DP가[^.]{0,12}(?:이하|이상|높은|낮은)'),
    ('코스트 조건', r'코스트 ?\d+ ?(?:이하|이상)'),
    ('특징 지정', r'특징(?:에|으로|이|을)?\s?「'),
    ('명칭 지정', r'명칭(?:에|이|을)?\s?「|「[^」]+」(?:을|를|의|인|이)'),
    ('색 지정', r'레드|블루|옐로|그린|블랙|퍼플|화이트'),
]
FILTERS = [(n, re.compile(p)) for n, p in FILTERS]

FORMS = [
    ('선택(임의)', r'할 수 있다|시킬 수 있다|놓을 수 있다|있다\.?$'),
    ('조건(~라면)', r'라면|인 경우|일 경우|있다면|없다면'),
    ('개수 비례(마다)', r'마다'),
    ('트리거(~했을 때)', r'했을 때|될 때|할 때|되었을 때|졌을 때'),
    ('기간(~까지)', r'턴 종료까지|종료 시까지|동안'),
    ('후속(그 후)', r'그 후'),
    ('횟수 제한', r'\[턴(?:에)? ?\d회\]'),
]
FORMS = [(n, re.compile(p)) for n, p in FORMS]

def head_kind(u):
    if re.match(r'〔(진화|조그레스|어플 합체|버스트 진화)〕', u):
        return '특수 진화 조건:' + re.match(r'〔([^〕]+)〕', u).group(1)
    if u.startswith('〈룰〉'): return '카드 고유 룰'
    if u.startswith('〈링크'): return '링크'
    if re.match(r'디지크로스\s*-', u): return '디지크로스'
    if re.match(r'어셈블리\s*-', u): return '어셈블리'
    if re.match(r'(?:' + LIM + r'\s*)*【', u): return '타이밍 효과'
    if u.startswith('《'): return '키워드 능력'
    return '상시·기타 문장'

def timings(u):
    m = TIMING_RUN.match(u)
    run = m.group(0) if m else ''
    return [t.strip() for t in re.findall(r'【([^】]+)】', run)], [re.sub(r'[\[\]{}〔〕]', '', x) for x in re.findall(LIM, run)]

def template(u):
    t = u
    for _ in range(3):
        t = re.sub(r'「[^「」]*」', '「X」', t)
    t = re.sub(r'\d+', 'N', t)
    t = re.sub(r'레드|블루|옐로|그린|블랙|퍼플|화이트', '色', t)
    t = re.sub(r'\([^()]*\)', '', t)  # keyword reminder text
    return re.sub(r'\s+', ' ', t).strip()

# Old and current card wordings that mean the same processing (user decision 2026-10-17, Q3/Q4).
# Applied only for classification; the unit keeps its original text.
WORDING = [
    (r'DP를\s*([+\-])\s*(\d+)(?:\s*한다)?', r'DP \1\2'),
    (r'시큐리티 어택', 'S 어택'),
    (r'메모리를\s*([+\-])\s*(\d+)(?:\s*한다)?', r'메모리 \1\2'),
    (r'이 턴 동안', '턴 종료까지'),
    (r'(?:다음 )?상대의 턴 종료 시까지', '상대의 턴 종료까지'),
    (r'[\[〔]턴에 (\d)회[\]〕]', r'[턴 \1회]'),
    (r'(?<!의 )상대 디지몬', '상대의 디지몬'),
    (r'특징에 「', '특징으로 「'),
    (r'([을를]) 갖는', r'\1 가진'),
    (r'(\d+)장 드로우한다', r'《\1 드로우》'),
]
WORDING = [(re.compile(a), b) for a, b in WORDING]
def normalize_wording(s):
    for a, b in WORDING:
        s = a.sub(b, s)
    return s

def analyse(card):
    from trigger_fx import trigger
    units = []
    for field, label in (('상단 텍스트', '상단'), ('하단 텍스트', '하단')):
        txt = norm_text(card.get(field, ''))
        for u0 in split_units(txt):
            u = normalize_wording(u0)
            tm, lim = timings(u)
            body = TIMING_RUN.sub('', u, count=1) if tm else u
            kind = head_kind(u)
            trg = trigger(u)
            if kind == '상시·기타 문장' and trg and trg['key']:
                kind = '유발 효과(타이밍 표시 없음)'
            if trg and trg['key'] and trg['clause'] in body:
                body = body[body.index(trg['clause']) + len(trg['clause']):]   # results come after '~때,'
            where = label
            if label == '하단':
                where = '시큐리티 효과' if '시큐리티' in tm else ('진화원 효과' if card['type'] == '디지몬' or card['type'] == '디지타마' else '하단')
            units.append({
                'card': card['no'], 'where': where, 'kind': kind, 'text': u0, 'ntext': u,
                'timing': tm, 'limit': lim,
                'keywords': sorted(set(keywords(u))),
                'actions': [n for n, p in ACTIONS if p.search(body)],
                'targets': [n for n, p in TARGETS if p.search(body)],
                'filters': [n for n, p in FILTERS if p.search(body)],
                'forms': [n for n, p in FORMS if p.search(u)],
                'tpl': template(u),
                'trigger': trg['key'] if trg else '', 'trigger_clause': trg['clause'] if trg else '',
            })
    return units

if __name__ == '__main__':
    from trigger_fx import trigger
    cards = json.load(open('cards.json', encoding='utf-8'))
    U = [u for c in cards for u in analyse(c)]
    json.dump(U, open('units.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('cards', len(cards), 'units', len(U))
    print(collections.Counter(u['kind'] for u in U).most_common())
    print(collections.Counter(u['where'] for u in U).most_common())
    print('no actions', sum(1 for u in U if u['kind'] == '타이밍 효과' and not u['actions']))
    print(collections.Counter(a for u in U for a in u['actions']).most_common(50))
