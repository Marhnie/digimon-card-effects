"""Trigger condition (유발 조건) of each effect: '누가 · 어디서 · 무엇으로 · 무슨 일이' from the clause ending in '~때,'.
e.g. 'EX8-005: 이 카드가 「광물형」 디지몬의 진화원에서 효과로 파기되었을 때' -> 이 카드 · 진화원에서 · 효과로 · 파기됨"""
import json, re, collections
from parse_fx import TIMING_RUN

SUBJ = [
    ('이 카드', r'이 (?:카드|디지몬|테이머)(?:가|이|는|를|의)?'),
    ('다른 자신의 디지몬', r'다른 자신의 (?:[^ ]{0,12} )?디지몬'),
    ('자신의 디지몬', r'자신의 (?:[^ ]{0,12} )?디지몬'),
    ('상대의 디지몬', r'상대의 (?:[^ ]{0,12} )?디지몬'),
    ('디지몬', r'(?:^|[ ,])디지몬(?:이|가)'),
    ('자신의 테이머', r'자신의 (?:[^ ]{0,8} )?테이머'),
    ('상대의 테이머', r'상대의 (?:[^ ]{0,8} )?테이머'),
    ('자신의 시큐리티', r'자신의 시큐리티'),
    ('상대의 시큐리티', r'상대의 시큐리티'),
    ('자신(플레이어)', r'자신이 '),
    ('상대(플레이어)', r'상대가 '),
    ('카드', r'카드(?:가|이)'),
]
PLACE = [('진화원에서', r'진화원(?:에서|으로부터)'), ('진화원으로', r'진화원(?:에|으로) (?:놓|들어)'), ('패에서', r'패에서'), ('패로', r'패(?:로|에) (?:되돌|돌아|추가|넣)'),
         ('트래시에서', r'트래시에서'), ('트래시로', r'트래시(?:로|에) '), ('배틀 에어리어', r'배틀 에어리어'), ('육성 에어리어', r'육성 에어리어'),
         ('시큐리티에서', r'시큐리티(?:에서|로부터)'), ('덱', r'덱(?:에서|으로|의)')]
CAUSE = [('상대의 효과로', r'상대의 효과(?:로|에 의해)'), ('자신의 효과로', r'자신의 효과(?:로|에 의해)'), ('효과로', r'효과(?:로|에 의해)'),
         ('배틀로', r'배틀(?:로|에서|에 의해)'), ('룰로', r'룰(?:로|에 의해)')]
EVENT = [
    ('파기됨', r'파기(?:되|됐|당)'), ('소멸함', r'소멸(?:했|할|되|된|하)'), ('등장함', r'등장(?:했|할|하|시켰)'), ('진화함', r'진화(?:했|할|하)'),
    ('어택함', r'어택(?:했|할|하)'), ('블록함', r'블록(?:했|할|하)'), ('블록당함', r'블록당'), ('레스트함', r'레스트(?:했|되|할|시켰)'),
    ('액티브가 됨', r'액티브(?:가 되|로 되|가 됐)'), ('줄어듦', r'줄어(?:들었|들|든)'), ('늘어남', r'늘어(?:났|날|나)'),
    ('벗어남', r'벗어(?:났|날|나)'), ('되돌아감', r'(?:되돌아|돌아)(?:갔|갈|가)|되돌려(?:졌|질)'), ('놓임', r'놓였|놓일|놓아졌'),
    ('사용함', r'사용(?:했|할|하)'), ('드로우함', r'드로우(?:했|할|하)'), ('링크함', r'링크(?:했|할|하)'), ('퇴화함', r'퇴화(?:했|할|하)'),
    ('효과를 받음', r'효과를 받|대상(?:이 되|으로 선택)'), ('공개함', r'공개(?:했|할|되)'), ('체크함', r'체크(?:했|할|하)'),
    ('배틀함', r'배틀(?:했|할|하)'), ('턴 종료', r'턴(?:이)? 종료'),
]
for L in (SUBJ, PLACE, CAUSE, EVENT):
    L[:] = [(n, re.compile(p)) for n, p in L]

def clause(text):
    body = TIMING_RUN.sub('', text, count=1)
    body = re.sub(r'^\s*(?:\[[^\]]+\]|〔[^〕]+〕|\{[^}]+\})\s*', '', body)
    body = re.sub(r'《[^》]*》\s*\([^)]*\)', '', body)   # keyword reminder text
    m = re.search(r'(?:했을|되었을|됐을|졌을|당했을|났을|었을|았을|였을|할|될|날|질|일|을) 때[,，]', body[:220])
    if not m: return None
    c = body[:m.end()]
    if '.' in c[:-1] and c.rfind('.') > 5: c = c[c.rfind('.') + 1:]
    return c.strip()

def trigger(text):
    c = clause(text)
    if not c: return None
    c2 = c
    for _ in range(3): c2 = re.sub(r'「[^「」]*」', '', c2)
    pick = lambda L: next((n for n, p in L if p.search(c2)), '')
    ev = pick(EVENT)
    if not ev: return {'clause': c, 'key': '', 'subj': '', 'place': '', 'cause': '', 'event': ''}
    subj, place, cause = pick(SUBJ), pick(PLACE), pick(CAUSE)
    key = ' · '.join(x for x in (subj, place, cause, ev) if x)
    return {'clause': c, 'key': key, 'subj': subj, 'place': place, 'cause': cause, 'event': ev}

if __name__ == '__main__':
    U = json.load(open('units3.json', encoding='utf-8'))
    T = [trigger(u['text']) for u in U]
    has = [t for t in T if t]; keyed = [t for t in has if t['key']]
    print('효과', len(U), '유발 조건 문장', len(has), '분해됨', len(keyed))
    c = collections.Counter(t['key'] for t in keyed)
    print('유발 조건 종류', len(c))
    for k, v in c.most_common(30): print(f'  {v:4} {k}')
    print('예:', [(U[i]['card'], T[i] and T[i]['key']) for i in range(len(U)) if U[i]['card'] in ('EX8-005', 'BT10-072', 'EX10-039')])
    miss = [t['clause'] for t in has if not t['key']][:10]
    print('분해 안 됨 예:', miss)
