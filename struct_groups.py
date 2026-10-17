"""Structure groups (분류 · 타이밍/유발 조건 · 주 처리) and rulebook clause for every component."""
import json, re, collections
from link_fx import ACTION_RULE, KW_RULE, timing_rule, TITLE
S = json.load(open('struct.json', encoding='utf-8'))
U = json.load(open('units3.json', encoding='utf-8'))
QI = json.load(open('qa_items.json', encoding='utf-8'))
CLS_RULE = {'상재형': '15-8-2', '유발형': '15-8-3', '기동형': '15-8-4', '즉시형': '15-8-5', '키워드 효과': '16'}
INFO_RULE = {'특수 진화 조건:진화': ['2-3-5', '8-1'], '특수 진화 조건:조그레스': ['8-2'], '특수 진화 조건:어플 합체': ['8-4'], '특수 진화 조건:버스트 진화': ['8-3'],
             '디지크로스': ['7-2'], '어셈블리': ['7-3'], '카드 고유 룰': ['2-3-4'], '링크': ['10']}
SRC_RULE = {'진화원 효과': ['15-3'], '시큐리티 효과': ['15-16-10'], '효과(상단 텍스트)': ['2-3-3']}
ICON_RULE = {'턴 1회': '15-14-1', '턴에 1회': '15-14-1', '턴 2회': '15-14-1', '패': '15-14-2', '트래시': '15-14-3', '육성': '15-14-4', '시큐리티': '15-14-5'}
EXTRA_ACT = {'어택 종료': ['15-15-1'], '금지': ['15-1-3'], '룰 변경': [], '디지크로스 확장': ['7-2'], '코스트 감소': ACTION_RULE.get('코스트 감소', [])}
EV = {'파기됨': '파기', '소멸함': '소멸', '등장함': '등장', '진화함': '진화', '레스트함': '레스트', '액티브가 됨': '액티브', '링크함': '링크', '퇴화함': '퇴화',
      '드로우함': '드로우', '사용함': '옵션 사용', '되돌아감': '패로 회수', '어택함': '추가 어택', '블록함': '블록 금지', '벗어남': '배틀 에어리어에 놓기'}

def comp_rules(s):
    """list of (부품, 값, 조항) in rulebook order"""
    R = []
    add = lambda part, val, ns: R.extend((part, val, n) for n in ns if n)
    add('출처', s['출처'], SRC_RULE.get(s['출처'], []))
    if s['분류'] == '카드 정보(효과 아님)':
        add('분류', s['세부'], INFO_RULE.get(s['세부'], [])); return R
    add('분류', s['분류'], [CLS_RULE.get(s['분류'])])
    if s['분류'] == '키워드 효과':
        for k in s['세부'].split(' / '): add('키워드', k, [KW_RULE.get(k.strip())])
        return R
    for t_ in s['타이밍']: add('타이밍', '【' + t_ + '】', [timing_rule(t_)])
    for i in s['아이콘']: add('아이콘', i, [ICON_RULE.get(i)])
    if s['유발 조건']:
        add('유발 조건', s['유발 키'] or s['유발 조건'], ['15-5'])
        ev = (s['유발 키'] or '').split(' · ')[-1]
        add('유발 조건', ev, ACTION_RULE.get(EV.get(ev, ''), []))
    for c in s['처리 조건']: add('처리 조건', c, ['15-6'])
    for c in s['임의 처리 조건']: add('임의 처리 조건', c['text'], ['15-7'])
    if len(s['처리']) > 1: add('처리 순서', f"{len(s['처리'])}단계", ['15-1-2'])
    for p in s['처리']:
        add('강제/임의', '임의 처리' if p['임의'] else '강제 처리', ['15-9-2' if p['임의'] else '15-9-1'])
        if p['scope'].startswith('단일'): add('대상', p['scope'], ['15-11-1', '15-10-2'])
        elif p['scope'] == '전체 처리': add('대상', p['scope'], ['15-11-2', '15-10-2-4'])
        if p['player']: add('대상', '플레이어:' + p['player'], ['15-10-1'])
        if p['정보 추가']: add('처리', '정보 추가', ['15-12-1'])
        if p['정보 변경']: add('처리', '정보 변경', ['15-12-2'])
        if p['효과 부여']: add('처리', '효과 부여', ['15-13', '15-15-2'])
        if p['치환']: add('처리', '치환(대신)', ['18-2'])
        for a in p['acts']:
            if a.startswith('키워드 실행: '): add('처리', a, [KW_RULE.get(a[7:].strip())])
            else: add('처리', a, EXTRA_ACT.get(a, ACTION_RULE.get(a, [])))
    return R

def main_proc(s):
    for p in s['처리']:
        for a in p['acts']:
            if a not in ('공개', '덱 위 확인', '코스트 무료'): return a
    return s['처리'][0]['acts'][0] if s['처리'] and s['처리'][0]['acts'] else ''

def group_key(s):
    c = s['분류']
    if c == '카드 정보(효과 아님)': return f"카드 정보 | {s['세부']}"
    if c == '키워드 효과': return f"키워드 효과 | {s['세부']}"
    if c in ('유발형', '즉시형') and s['유발 키']: how = '유발 조건: ' + s['유발 키']
    elif s['타이밍']: how = '타이밍: ' + '+'.join(s['타이밍'])
    else: how = '타이밍 없음'
    return f"{c} | {how} | 처리: {main_proc(s) or '(없음)'}"

for i, s in enumerate(S):
    s['group'] = group_key(s); s['rules'] = comp_rules(s); s['i'] = i
G = collections.defaultdict(list)
for s in S: G[s['group']].append(s['i'])
qa_of = collections.defaultdict(list)
for k, q in enumerate(QI):
    if q['unit'] is not None: qa_of[q['unit']].append(k)
json.dump(S, open('struct2.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('구조 그룹', len(G), ' 효과 2개 이상 그룹', sum(1 for v in G.values() if len(v) > 1), ' 단독', sum(1 for v in G.values() if len(v) == 1))
print('그룹 크기 상위:')
for k, v in sorted(G.items(), key=lambda kv: -len(kv[1]))[:15]: print(f'  {len(v):4}  {k}')
# Q&A answer consistency inside structure groups (yes/no, by question similarity not needed: share of groups whose Q&A exist)
with_qa = sum(1 for v in G.values() if any(qa_of[i] for i in v))
print('Q&A가 있는 그룹', with_qa)
key = [s['group'] for s in S if s['card'] in ('EX8-005', 'BT10-072', 'EX10-039') and '파기' in s['text']]
print('고로몬·바그라군 그룹:', key)
