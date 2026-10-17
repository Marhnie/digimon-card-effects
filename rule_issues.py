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
]

def exemplars(qa_rows):
    """qa_rows: the judge helper's D.qa rows [card, q, a, ...]; returns {issue id: [row indices]}"""
    out = {}
    for it in ISSUES:
        p = re.compile(it['ans'])
        out[it['id']] = [i for i, r in enumerate(qa_rows) if p.search(r[2])]
    return out
