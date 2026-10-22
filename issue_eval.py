"""E44: candidate rule issues, written from OLDER products' questions only, measured on the newest (time split).
For each candidate: older exemplars (questions matching cue+ask, not 'not') must agree (aligned for negation);
newest matches: how many, how many right, and how many the page does NOT decide yet (net/tdec_items.json from tests/tdec.js)."""
import json, re, sys
sys.path.insert(0, '.')
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']; NEGI = len(T['form']['slots']) - 1
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}; prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
DEC = {d['i']: d for d in json.load(open('net/tdec_items.json'))}


def ev(c):
    cue, ask, nt = re.compile(c['cue']), re.compile(c['ask']), re.compile(c['not']) if c.get('not') else None
    m = [i for i, r in enumerate(QA) if r[0] and r[8] >= 0 and cue.search(r[1]) and ask.search(r[1]) and not (nt and nt.search(r[1]))]
    old = [i for i in m if prod(QA[i][0]) not in NEW]; new = [i for i in m if prod(QA[i][0]) in NEW]
    # page aligns each exemplar to the asker's polarity: y ^ (neg ^ myneg); judge with myneg = 0
    ys = [QA[i][8] ^ QA[i][9] for i in old]; yes = sum(ys)
    ok_old = len(ys) >= 3 and yes in (0, len(ys)); ans0 = 1 if yes else 0
    r = {'id': c['id'], 'old': len(old), 'old_unanimous': ok_old, 'old_yes': yes}
    if ok_old:
        got = [(i, (ans0 ^ QA[i][9]) == QA[i][8]) for i in new]
        und = [(i, ok) for i, ok in got if i in DEC and not DEC[i]['by']]
        r.update(new=len(got), new_ok=sum(ok for _, ok in got), new_undecided=len(und), new_undecided_ok=sum(ok for _, ok in und))
    return r


if __name__ == '__main__':
    from rule_issues_cand import CANDS
    for c in CANDS: print(json.dumps(ev(c), ensure_ascii=False))
