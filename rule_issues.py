"""Rule issues (룰 쟁점): recurring rulebook points that decide many questions whatever the card.
Each issue: how to recognise it in a question (cue, JS regex), the rule clauses, and the official Q&A whose ANSWER
states that point (exemplars, found by ans regex). The judge helper puts these first in the evidence and, when the
exemplars agree, answers without Claude.  Used by build_v4data.py (D.issues)."""
import re
ISSUES = [
    {'id': 'pending_leave', 'name': '발휘 대기 중 카드 이동',
     'desc': '유발한 효과가 발휘되기 전에 그 카드가 있던 곳을 벗어나면(덱·패로 되돌아감, 등장 등) 그 효과는 발휘할 수 없습니다.',
     'rules': ['15-4-4-3', '4-17-5', '15-4-2-2'],
     # an effect that triggered from a zone (trashed / deleted / from sources) and the card then moves on before it resolves
     'cue': r'(소멸|파기|진화원에서|트래시)[^?？]{0,120}(그 후|같은 효과|이후|뒤|다음|곧바로|바로|직후|자마자|되돌아간|되돌린|되돌리)[^?？]{0,80}(덱|패|등장|되돌|벗어|이동)',
     'ans': r'(발휘 대기|유발한)[^.]{0,50}발휘(?:하|되|시키)기 전에[^.]{0,30}(벗어|떠|이동)',
     # the question must ask whether that (moved) card's effect still activates — not whether a step may be skipped
     'ask': r'((효과|【[^】]+】)[^?？]{0,20}(발휘|유발)|메모리|드로우|발휘)[^?？]{0,25}(할 수 있|하나요|합니까|되나요|됩니까|돼요|되요|해요)[^?？]{0,10}[?？]?\s*$',
     'not': r'않을 수|않는 것|선택하지|생략',
     'needs_trigger': True},
    {'id': 'mid_resolution', 'name': '효과 처리 도중 카드가 바뀜',
     'desc': '효과를 발휘한 카드가 그 효과의 처리 도중에 새로운 카드가 되어도, 그 효과는 끝까지 해결됩니다.',
     'rules': ['15-4-1-2'],
     'cue': r'(처리 도중|처리 중|해결 도중|효과 도중)[^?？]{0,80}(진화|소멸|이동|벗어|새로운 카드)', 'ask': r'.', 'not': r'^$',
     'ans': r'(처리 도중|도중에)[^.]{0,60}(모두 해결|끝까지|해결됩니다|처리합니다)',
     'needs_trigger': False},
    # E32: issues whose exemplars are found by the QUESTION (ex='q': Q&A whose question matches cue+ask and not 'not');
    # each was checked on older products (answer unanimous) before being added
    {'id': 'cost_partial', 'name': '「것으로」 조건은 일부만 실행할 수 없음',
     'desc': '「~하는 것으로」 조건(비용)은 지정된 내용을 전부 실행해야 하며, 일부(예: 2장만)만 실행해서 효과를 발휘할 수 없습니다.',
     'rules': ['15-7'], 'ex': 'q',
     'cue': r'(것으로|조건)[^?？]{0,60}(\d+ ?(장|마리|개)만|일부만)|(\d+ ?(장|마리|개)만|일부만)[^?？]{0,40}조건',
     'ask': r'수 있|가능', 'not': r'조건을 가진|조건이 있는|디지크로스', 'needs_trigger': False},
    {'id': 'cost_unmet_then', 'name': '「것으로」 조건을 못 채우면 「그 후」도 처리 불가',
     'desc': '「~하는 것으로」 조건을 실행하지 못하면 그 효과는 발휘되지 않으므로, 「그 후」 이후의 처리도 할 수 없습니다.',
     'rules': ['15-7'], 'ex': 'q',
     'cue': r'것으로」?[^?？]{0,15}조건[^?？]{0,30}(충족|만족|실행)(하지|시키지) ?(않|못)[^?？]{0,40}그 후', 'ask': r'.', 'not': r'^$', 'needs_trigger': False},
    {'id': 'if_unmet_then', 'name': '「~라면」 조건을 못 채워도 「그 후」는 처리',
     'desc': '「~라면」은 그 처리만의 조건입니다. 만족하지 않아도 「그 후」 이후의 처리는 할 수 있습니다.',
     'rules': ['15-6'], 'ex': 'q',
     'cue': r'라면」?[^?？]{0,15}조건[^?？]{0,30}(충족|만족)(하지|시키지) ?(않|못)[^?？]{0,40}그 후', 'ask': r'.', 'not': r'^$', 'needs_trigger': False},
    {'id': 'option_not_used', 'name': '사용하지 않고 발휘한 옵션은 「사용했을 때」가 아님',
     'desc': '【시큐리티】 효과나 《딜레이》처럼 사용하지 않고 옵션 카드의 효과를 발휘한 경우, 「옵션 카드를 사용했을 때」 효과는 유발되지 않습니다.',
     'rules': ['4-3'], 'ex': 'q',
     'cue': r'(사용 이외|사용하지 않고|【시큐리티】|《딜레이》|≪딜레이≫)[^?？]{0,80}옵션 카드를 사용했을 때', 'ask': r'.', 'not': r'^$', 'needs_trigger': False},
    {'id': 'limit_not_spent', 'name': '발휘하지 못한 효과는 [턴 1회]를 소비하지 않음',
     'desc': '그 타이밍에 효과를 발휘할 수 없었다면 그 효과의 [턴에 X회]는 소비되지 않습니다.',
     'rules': ['15-11'], 'ex': 'q',
     'cue': r'(발휘할 수 없|발휘하지 않|발휘되지 않)[^?？]{0,60}(턴 ?\d회|턴에 ?\d회|\[턴)[^?？]{0,40}(소비|사용)', 'ask': r'.', 'not': r'^$', 'needs_trigger': False},
    {'id': 'link_swap_no_trigger', 'name': '링크 교체로 파기된 카드는 「링크할 때/파기될 때」 유발 아님',
     'desc': '링크하는 효과로 링크할 때 이미 링크되어 있던 카드를 바꿔 끼워 파기하는 것은 링크 처리의 일부이므로, 그 파기로는 효과가 유발되지 않습니다.',
     'rules': ['4-21'], 'ex': 'q',
     'cue': r'링크(하는|할) ?(효과로|때)[^?？]{0,40}(이미 링크|링크되어 있던)[^?？]{0,30}(바꿔|교체)[^?？]{0,20}파기', 'ask': r'유발|발휘', 'not': r'^$', 'needs_trigger': False},
]


# E44: written from older products' questions only (rule_issues_cand.py, issue_eval.py); older exemplars unanimous (n >= 10).
# 「어떤 진화든 진화 드로우」 was left out: on the newest products it added one wrong answer.
from rule_issues_cand import CANDS as _C
ISSUES += [c for c in _C if c['id'] != 'evolution_draw_always']

def exemplars(qa_rows):
    """qa_rows: the judge helper's D.qa rows [card, q, a, ...]; returns {issue id: [row indices]}"""
    out = {}
    for it in ISSUES:
        if it.get('ex') == 'q':
            c, a, n = re.compile(it['cue']), re.compile(it['ask']), re.compile(it['not']) if it.get('not') else None
            out[it['id']] = [i for i, r in enumerate(qa_rows) if c.search(r[1]) and a.search(r[1]) and not (n and n.search(r[1]))]
        else:
            p = re.compile(it['ans'])
            out[it['id']] = [i for i, r in enumerate(qa_rows) if p.search(r[2])]
    return out
