"""E50: question-pattern drafts for rule-issue candidates (NOT merged into rule_issues.py — that file belongs to the judge-screen session).
Same fields as rule_issues.ISSUES (ex='q'); run `python rule_issues_cand_e50.py` to see matches, answer agreement and the old/new split."""
import json, re
CANDS = [
    {'id': 'evo_cond_required', 'name': '진화 조건을 만족하지 않는 카드로는 진화 불가(Lv만 무시해도 조건은 필요)',
     'desc': '효과로 진화할 때 「Lv.을 무시」하더라도 진화 조건(색·특징 등)은 만족해야 하며, 조건을 만족하지 않는 카드로는 진화할 수 없습니다.',
     'cue': r'진화 조건을 만족하지 않[은는][^?？]{0,30}(으로|에게)[^?？]{0,25}진화', 'ask': r'수 있', 'not': r'무시하고|대신'},
    {'id': 'summoned_vanish_each_turn_end', 'name': '효과로 등장한 디지몬 중 「턴 종료 시 소멸」이 붙은 것은 매 턴 종료마다 소멸',
     'desc': '【시큐리티】·【등장 시】·《딜레이》 등 「턴 종료 시 소멸」이 붙는 효과로 등장한 디지몬은 소멸하는 타이밍이 될 때마다 소멸합니다.',
     'cue': r'(효과|《[^》]+》)로 등장한 (이 카드|디지몬)[은는] ?(자신의 |상대의 )?턴 종료 시가 될 때마다 소멸', 'ask': r'소멸하나요|소멸합니까', 'not': r'^$'},
]
if __name__ == '__main__':
    T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
    NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
    prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
    for it in CANDS:
        m = [i for i, r in enumerate(QA) if r[0] and r[8] >= 0 and re.search(it['cue'], r[1]) and re.search(it['ask'], r[1]) and not re.search(it['not'], r[1])]
        ans = [QA[i][8] ^ QA[i][9] for i in m]
        print(it['id'], 'matches', len(m), 'positive-answer share', round(sum(ans) / len(ans), 2) if m else None,
              '| distinct q', len({re.sub(r'\s+', '', QA[i][1]) for i in m}), '| old', sum(prod(QA[i][0]) not in NEW for i in m), 'new', sum(prod(QA[i][0]) in NEW for i in m))
        for i in m[:4]: print('   ', QA[i][8], QA[i][1][:90])
