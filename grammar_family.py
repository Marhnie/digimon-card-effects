"""E54: 「같은 문법 구조」 evidence — official Q&A of effects that share the grammatical construct a question is about,
whatever the card (the reasoning the operator asked for, 2026-10-25: 「A/B 1장」, 덱 오픈 후 추가, 「상대는 ~할 수 있다」 …).

  constructs(effect text)  -> set of construct ids (regexes below)
  focus(question)          -> the constructs the question touches (question cue words) ∩ the effect's constructs
  family(i)                -> older Q&A whose effect has those constructs, same asked thing, ranked by construct rarity + wording

Measured in __main__ on the time split (newest products = test, older = evidence), like sna_links.py:
  * evidence: does the family surface an official Q&A explained the same way (reason group) that 2-gram search misses?
  * decision: on questions the page leaves undecided, does a family vote reach high precision (thresholds chosen on one half)?
  python grammar_family.py  -> paper/results/grammar_family.json
"""
import json, re, math, collections, os, sys

# construct: (effect-text regex, question cue regex). The cue says the question is ABOUT that construct.
CONSTRUCTS = {
    'slash':      (r'(?:[가-힣」》】])/(?:[「《【가-힣])',            r'한쪽|어느 쪽|둘 중|어느 하나|둘 다|양쪽|/'),
    'multi_slot': (r'1장과|1마리와|1장씩|1마리씩',                  r'1장씩|각각|둘 다|모두|한 장만|1장만|하나만'),
    'deck_open':  (r'오픈한다|오픈하고',                            r'오픈'),
    'optional':   (r'할 수 있다|시킬 수 있다|놓을 수 있다|추가할 수 있다', r'않아도|안 해도|하지 않|선택하지|않고|안 하고|하지 않을'),
    'then':       (r'그 후',                                        r'그 후'),
    'cost':       (r'것으로',                                       r'것으로|조건|못 하면|못하면|일부'),
    'if':         (r'라면[,，]|다면[,，]',                          r'라면|다면|조건|만족'),
    'opp_choose': (r'상대는',                                       r'상대가 (?:고|선택)|상대는'),
    'per':        (r'마다',                                         r'마다|만큼|매수|장수'),
    'count':      (r'(?:\d+|N)장 이상|(?:\d+|N)장 이하|매수 이상|매수 이하', r'0장|없|장 이상|장 이하|매수'),
    'leave':      (r'벗어날 때|떠날 때',                            r'벗어날|떠날|벗어나'),
    'instead':    (r'대신',                                         r'대신'),
    'limit':      (r'\[턴(?:에)? ?1회\]',                           r'턴에 1회|턴 1회|\[턴|한 번|두 번|다시'),
    'under':      (r'진화원 아래에|아래에 놓',                      r'아래에|진화원으로'),
    'from_trash': (r'트래시에서',                                   r'트래시'),
    'no_cost':    (r'코스트를 지불하지 않고',                       r'코스트'),
    'order':      (r'나머지는|원하는 순서',                         r'순서|나머지'),
    'all':        (r'전부|모든',                                    r'전부|모두|모든|전체'),
}
CX = {k: (re.compile(a), re.compile(b)) for k, (a, b) in CONSTRUCTS.items()}


def constructs(text):
    return {k for k, (ra, _) in CX.items() if ra.search(text or '')}


def focus(question, effect_constructs):
    return {k for k in effect_constructs if CX[k][1].search(question or '')}


class Family:
    def __init__(self, QA, UNITS, pool):
        """QA: test_data4 qa rows; UNITS: test_data4 units (text at [3]); pool: Q&A indices usable as evidence."""
        self.QA, self.U = QA, UNITS
        self.ec = {}
        self.pool = [j for j in pool if self._ec(j)]
        df = collections.Counter(k for j in self.pool for k in self._ec(j))
        n = len(self.pool) or 1
        self.idf = {k: math.log((n + 1) / (df[k] + 1)) + 0.1 for k in CONSTRUCTS}
        self.by_c = collections.defaultdict(list)
        for j in self.pool:
            for k in self._ec(j): self.by_c[k].append(j)

    def _ec(self, j):
        if j not in self.ec:
            u = self.QA[j][3]
            self.ec[j] = constructs(self.U[u][3]) if u is not None and 0 <= u < len(self.U) else set()
        return self.ec[j]

    def hits(self, q, unit, it, k=10, sim=None):
        """q: question text; unit: the effect unit asked about; it: asked-thing id (QA[.][6] / ST.it). -> [(score, j, shared constructs)]"""
        ec = constructs(self.U[unit][3]) if unit is not None and 0 <= unit < len(self.U) else set()
        fc = focus(q, ec)
        if not fc: return []
        cand = set().union(*(self.by_c[c] for c in fc))
        out = []
        for j in cand:
            if self.QA[j][6] != it: continue
            ej = self._ec(j)
            if not fc <= ej: continue                                        # the family must share every construct the question is about
            fj = focus(self.QA[j][1], ej)
            s = sum(self.idf[c] for c in fc) * (0.5 + len(fc & fj) / len(fc))    # the evidence question is about the same construct too
            s *= 0.3 + (sim(q, self.QA[j][1]) if sim else 0)
            out.append((s, j, sorted(fc)))
        out.sort(reverse=True)
        return out[:k]


if __name__ == '__main__':
    ROOT = os.path.dirname(os.path.abspath(__file__))
    T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8')); QA, U = T['qa'], T['units']
    NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}; HALF0 = {'BT22', 'EX9', 'ST21'}
    prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
    OF = {int(k): v for k, v in T['rg']['of'].items()}; RG = T['rg']['g']
    bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))
    BG = {}
    def sim(a, b):
        A = BG.setdefault(a, bg(a)); B = BG.setdefault(b, bg(b)); return len(A & B) / (len(A | B) or 1)
    YN = [i for i, r in enumerate(QA) if r[0] and r[3] is not None and r[3] >= 0]
    pool = [i for i in YN if prod(QA[i][0]) not in NEW]
    test = [i for i in YN if prod(QA[i][0]) in NEW and QA[i][8] >= 0]
    F = Family(QA, U, pool)
    DEC = {d['i']: d for d in json.load(open(os.path.join(ROOT, 'net', 'tdec_full.json')))}
    al = lambda j, i: QA[j][8] ^ (QA[j][9] ^ QA[i][9])
    res = {}

    # coverage of the construct analysis
    with_focus = [i for i in test if F.hits(QA[i][1], QA[i][3], QA[i][6], 1, sim)]
    res['test'] = len(test); res['with_family'] = len(with_focus)
    print('test yes/no', len(test), '| questions with a same-grammar family', len(with_focus))

    # (1) evidence recall: reason group of the answer found in top-10 family vs top-10 2-gram search
    grp = [i for i in test if OF.get(i) is not None]
    def top_text(i): return sorted(pool, key=lambda j: -sim(QA[i][1], QA[j][1]))[:10]
    for name, S in (('with reason group', grp), ('page-undecided with reason group', [i for i in grp if i in DEC and not DEC[i]['by']])):
        tx = {i: any(OF.get(j) == OF[i] for j in top_text(i)) for i in S}
        fm = {i: any(OF.get(j) == OF[i] for _, j, _ in F.hits(QA[i][1], QA[i][3], QA[i][6], 10, sim)) for i in S}
        r = {'n': len(S), 'text_top10': round(sum(tx.values()) / max(1, len(S)), 3), 'family_top10': round(sum(fm.values()) / max(1, len(S)), 3),
             'family_only': sum(1 for i in S if fm[i] and not tx[i]), 'union': round(sum(1 for i in S if fm[i] or tx[i]) / max(1, len(S)), 3)}
        res['recall: ' + name] = r; print('recall', name, r)

    # (2) decision on page-undecided questions: weighted vote of the family (aligned for negation), honest half split
    rows = []
    for i in test:
        if i not in DEC or DEC[i]['by']: continue
        h = F.hits(QA[i][1], QA[i][3], QA[i][6], 10, sim)
        if not h: continue
        yes = sum(s for s, j, _ in h if al(j, i)); no = sum(s for s, j, _ in h if not al(j, i))
        rows.append({'m': abs(yes - no) / (yes + no), 'n': len(h), 'top': h[0][0], 'ok': int(int(yes >= no) == QA[i][8]),
                     'half': 0 if prod(QA[i][0]) in HALF0 else 1})
    res['undecided_with_family'] = len(rows); res['vote_acc_all'] = round(sum(r['ok'] for r in rows) / max(1, len(rows)), 3)
    hon = []
    for a, b in ((0, 1), (1, 0)):
        best = None
        for mt in (0.5, 0.7, 0.8, 0.9, 1.0):
            for nt in (1, 2, 3, 5):
                s = [r for r in rows if r['half'] == a and r['m'] >= mt and r['n'] >= nt]
                if len(s) >= 6 and sum(r['ok'] for r in s) / len(s) >= 0.97 and (best is None or len(s) > best[2]): best = (mt, nt, len(s))
        ev = [r for r in rows if best and r['half'] == b and r['m'] >= best[0] and r['n'] >= best[1]]
        hon.append({'rule': best, 'n': len(ev), 'ok': sum(r['ok'] for r in ev)})
    res['decision_honest'] = hon
    print('undecided with a family', len(rows), 'vote acc', res['vote_acc_all'], '| honest', hon)
    json.dump(res, open(os.path.join(ROOT, 'paper', 'results', 'grammar_family.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
