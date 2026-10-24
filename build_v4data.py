"""Judge helper data v4 = test_data3.json + rulebook structure per effect unit (struct2.json) + effect-network cluster (net/effect_sna.json).
D.st[i] = [분류, 유발 조건(아이콘 타이밍 포함)[], 처리 조건[], 임의 처리 조건[], 처리 단계[[처리, 편, 대상, 필터, 임의, 단일/전체, 지속]], 구조 그룹, 세부 클러스터 or -1]
D.clu[c] = [세부 이름, 대분류 번호, 대분류 이름, 효과 수]"""
import json
T = json.load(open('test_data3.json', encoding='utf-8'))
S = json.load(open('struct2.json', encoding='utf-8'))
NET = json.load(open('net/effect_sna.json', encoding='utf-8'))
TRIG_TM = {'등장 시', '진화 시', '소멸 시', '어택 시', '링크 시', '시큐리티', '자신의 턴 개시 시', '상대의 턴 개시 시', '자신의 턴 종료 시',
           '상대의 턴 종료 시', '서로의 턴 종료 시', '자신의 메인 페이즈 개시 시', '상대의 메인 페이즈 개시 시', '어택 종료 시', '이동 시'}
nodes = [s for s in S if s['분류'] != '카드 정보(효과 아님)']
# effect-network clusters are matched by (card, text): units added after the network was built (e.g. a new set
# imported from a translation workbook) get no cluster until effect_sna2.py is re-run
U3 = json.load(open('units3.json', encoding='utf-8'))
byct = {(n['card'], n['text']): n['c'] for n in NET['nodes']}
clu_of = {s['i']: byct.get((U3[s['i']]['card'], U3[s['i']]['text']), -1) for s in nodes}
st = [None] * len(T['units'])
for s in S:
    trig = ['【' + x + '】' for x in s.get('타이밍', []) if x in TRIG_TM] + ([s['유발 키']] if s.get('유발 키') else [])
    conds = [c if isinstance(c, str) else c.get('text', '') for c in s.get('처리 조건', [])]
    costs = [c.get('text', '') if isinstance(c, dict) else str(c) for c in s.get('임의 처리 조건', [])]
    steps = [[' / '.join(p['acts']), p.get('side', ''), p.get('target', ''), ', '.join(p.get('filters', [])), 1 if p['임의'] else 0, p.get('scope', ''), p.get('dur', '')]
             for p in s.get('처리', [])]
    st[s['i']] = [s['분류'], trig, conds, costs, steps, s['group'], clu_of.get(s['i'], -1)]
assert all(x is not None for x in st)
co = {f: c for c in NET['coarse'] for f in c['fine']}
T['st'] = st
T['clu'] = [[c['name'], co[c['id']]['id'], co[c['id']]['name'], c['n']] for c in NET['clusters']]
from rule_issues import ISSUES, exemplars
EX = exemplars(T['qa'])
T['issues'] = [{**{k: it[k] for k in ('id', 'name', 'desc', 'rules', 'cue', 'ask', 'not', 'needs_trigger') if k in it}, 'qa': EX[it['id']]} for it in ISSUES]
print('rule issues', {it['id']: len(EX[it['id']]) for it in ISSUES})
# reason groups (all Q&A) — only the consistent ones are used by the engine; engine-lite weights (time-split trained)
RGJ = json.load(open('reason_groups.json', encoding='utf-8'))
T['rg'] = {'of': RGJ['of'], 'g': [[g['name'], g['yes'], g['cons'], g['ny'], g['cards']] for g in RGJ['groups']]}
T['eng'] = json.load(open('net/engine_lite.json')); T['eng']['thr'] = 0.80
# E39: community nicknames (user-confirmed) -> official wording / cards
AL = json.load(open('aliases.json', encoding='utf-8'))['alias']
for x in AL:
    assert all(n in T['cards'] for n in x.get('nos', [])), x
T['alias'] = [[x['a'], x['to'], x.get('nos', []), 1 if x.get('deck') else 0] for x in AL]
# E53: question normalization rules (qnorm_dict.json, E31) for the page: colloquial terms -> official terms before matching
QD = json.load(open('qnorm_dict.json', encoding='utf-8'))
T['qnorm'] = [[x['p'], x['r']] for x in QD['pre']] + [[x['p'], x['r']] for x in QD['rules'] if x.get('g', '') in ('num', 'timing', 'keyword', 'term', 'ending')]
json.dump(T, open('test_data4.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('units', len(st), 'clusters', len(T['clu']), 'with cluster', sum(x[6] >= 0 for x in st))
