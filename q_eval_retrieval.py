"""E31: recall@1/3/10 of colloquial question -> official Q&A retrieval (retrieval-only; no yes/no verdict).

Corpus: Q&A of the older products (before BT22) + the Q&A of the same card (a new-product card has no older Q&A).
Gold A (source included): the source Q&A, or any Q&A in its reason group with the same polarity, or a word-identical question.
Gold B (source removed from the corpus): the same without the source (only items that still have a gold in the corpus).
Methods:  a raw 2-gram Jaccard (the judge helper today) | b normalised | c normalised + frame bonus
          d = c with IDF-weighted 2-gram overlap (extra, not asked for)
          upper = the official sentence itself as the query.
Usage: python q_eval_retrieval.py [eval|dev]   dev = paper/results/colloquial_dev.json (tuning only), eval = colloquial_test.json
"""
import json, re, sys, math, collections, itertools
import qnorm as Q

T = json.load(open('test_data4.json', encoding='utf-8'))
QA, CARDS = T['qa'], T['cards']
OF = {int(k): v for k, v in T['rg']['of'].items()}
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
pol = lambda i: (QA[i][8] ^ QA[i][9]) if QA[i][8] >= 0 else None

DOC = [i for i, r in enumerate(QA) if r[0]]
BG = {i: Q.bigrams(QA[i][1]) for i in DOC}
FR = {i: Q.frame(Q.normalize(QA[i][1], names=False)) for i in DOC}
CN = {i: (CARDS.get(QA[i][0]) or [''])[0] for i in DOC}
OLD = [i for i in DOC if prod(QA[i][0]) not in NEW]
BYCARD = collections.defaultdict(list)
for i in DOC:
    BYCARD[QA[i][0]].append(i)
GRP = collections.defaultdict(set)
for i, g in OF.items():
    GRP[g].add(i)
TEXT = collections.defaultdict(set)
for i in DOC:
    TEXT[re.sub(r'\s+', '', QA[i][1])].add(i)
DF = collections.Counter(g for i in DOC for g in BG[i])
IDF = lambda g: math.log((len(DOC) + 1) / (DF.get(g, 0) + 1)) + 1
VOCAB = set(re.findall(r'[가-힣]{3,}', ' '.join(QA[i][1] for i in DOC)))
import os
SYM = os.environ.get('SYM', '1') == '1'   # also normalise the corpus questions (symmetric)
CONTENT = os.environ.get('CONTENT', '1') == '1'  # drop question endings / filler words from the 2-gram text (ask class stays in the frame)
prep = (lambda t: Q.content(t)) if CONTENT else (lambda t: t)
BGN = {i: Q.bigrams(prep(Q.normalize(QA[i][1], names=False))) for i in DOC} if SYM else BG


def gold(qid, mode):
    g = {i for i in GRP.get(OF.get(qid), ()) if pol(i) == pol(qid) or pol(i) is None or pol(qid) is None} if qid in OF else set()
    g |= TEXT[re.sub(r'\s+', '', QA[qid][1])]
    g.add(qid) if mode == 'A' else g.discard(qid)
    return g


def corpus(card, qid, mode):
    c = set(OLD) | set(BYCARD[card])
    if mode == 'B':
        c.discard(qid)
    return c


def widj(a, b):
    inter = sum(IDF(g) for g in a & b)
    return inter / ((sum(IDF(g) for g in a) + sum(IDF(g) for g in b) - inter) or 1)


def rank(query, method, card, qid, mode, W=None):
    Q.W.update(W or {})
    qn = query if method == 'a' else Q.normalize(query, vocab=VOCAB)
    A = Q.bigrams(qn if method == 'a' else prep(qn))
    fq = Q.frame(qn) if method in 'cd' else None
    sc = []
    for i in corpus(card, qid, mode):
        B = BG[i] if method == 'a' else BGN[i]
        s = widj(A, B) if method == 'd' else Q.jac(A, B)
        if fq is not None:
            s += Q.frame_bonus(fq, FR[i], CN[i])
        sc.append((-s, i))
    sc.sort()
    return [i for _, i in sc]


def run(rows, field, method, mode, W=None):
    hit = {1: 0, 3: 0, 10: 0}
    n = 0
    for x in rows:
        g = gold(x['qid'], mode)
        if not (g & corpus(x['card'], x['qid'], mode)):
            continue
        n += 1
        rk = rank(x[field], method, x['card'], x['qid'], mode, W)
        for k in hit:
            hit[k] += bool(g & set(rk[:k]))
    return {'n': n, **{f'recall@{k}': round(v / n, 3) if n else None for k, v in hit.items()}}


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'eval'
    path = 'paper/results/' + ('colloquial_test.json' if which == 'eval' else 'colloquial_dev.json')
    rows = json.load(open(path, encoding='utf-8'))['items']
    base = dict(Q.W)
    out = {}
    for mode in 'AB':
        for name, field, m in [('a_raw', 'colloquial', 'a'), ('b_norm', 'colloquial', 'b'), ('c_norm+frame', 'colloquial', 'c'),
                               ('upper_official_raw', 'official', 'a'),
                               ('upper_official_norm+frame', 'official', 'c')]:
            out[f'{mode}:{name}'] = run(rows, field, m, mode)
            print(mode, name, out[f'{mode}:{name}'])
    for st in sorted({x['style'] for x in rows}):
        for m in 'abc':
            out[f'B:style:{st}:{m}'] = run([x for x in rows if x['style'] == st], 'colloquial', m, 'B')
            print('B', st, m, out[f'B:style:{st}:{m}'])
    lo = [x for x in rows if max([Q.jac(Q.bigrams(x['colloquial']), BG[i]) for i in gold(x['qid'], 'B') & corpus(x['card'], x['qid'], 'B')] or [1]) < 0.3]
    out['low_overlap_n'] = len(lo)
    for m in 'abc':
        out[f'B:low_overlap:{m}'] = run(lo, 'colloquial', m, 'B')
        print('B low-overlap(raw Jaccard to best gold < 0.3)', m, out[f'B:low_overlap:{m}'])
    json.dump(out, open(f'paper/results/e31_retrieval_{which}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
