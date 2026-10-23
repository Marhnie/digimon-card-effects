"""E50: turn the answer-unanimous gap clusters into rule-issue CANDIDATES (official answers already exist, so no judge queue is needed
to know the answer — a judge/maintainer only decides whether to promote a cluster to a question-pattern rule in rule_issues.py).
Needs paper/results/e50_gap_clusters.json (issue_gap_clusters.py). Marks clusters whose members are already caught by an existing rule issue."""
import json, re
import rule_issues as RI
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
G = json.load(open('paper/results/e50_gap_clusters.json', encoding='utf-8'))['clusters@0.35']
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
def caught(q):
    for it in RI.ISSUES:
        try:
            if it.get('ex') == 'q' and re.search(it['cue'], q) and re.search(it.get('ask', '.'), q) and not re.search(it.get('not', '^$'), q): return it['id']
        except re.error: pass
    return None
out = []
for c in G:
    if c['agree'] < 0.9: continue
    mem = c['members']; cov = [caught(QA[i][1]) for i in mem]
    ans = ['네' if QA[i][8] == 1 else '아니요' for i in mem]
    out.append({'n': c['n'], 'answer_mode': max(set(ans), key=ans.count), 'already_caught': sum(x is not None for x in cov), 'caught_by': sorted({x for x in cov if x}),
                'representative_q': c['representative'], 'representative_answer': cq(QA[c['qa_index']][2])[:300], 'cards': c['cards'], 'members': mem})
out.sort(key=lambda o: (o['already_caught'] / o['n'] >= .5, -o['n']))
json.dump(out, open('paper/results/e50_issue_candidates.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
new = [o for o in out if o['already_caught'] / o['n'] < .5]
print('unanimous clusters', len(out), '| mostly already caught', len(out) - len(new), '| new candidates', len(new), 'covering', sum(o['n'] for o in new), 'Q&A')
for o in new: print(o['n'], o['answer_mode'], o['representative_q'][:70], '→', o['representative_answer'][:60])
