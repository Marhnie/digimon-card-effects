"""Mine rule issues (룰 쟁점) automatically (E32): every consistent reason group (official answers explained by the same
principle) becomes a candidate issue; its question cue is a small AND-set of phrases that the group's questions share
and that, across ALL pool questions containing them, predict the group's answer (aligned for negation) ≥ PREC.

Time split as everywhere: mined from products before BT22/BT23/BT24/EX9/EX10/ST21/ST22, evaluated on those.
  python issue_mine.py            → paper/results/issue_mine.json (test metrics) + rule_issues_auto.json mined on ALL data
Phrases are char n-grams of the question with quoted names removed, so the page can test them on the raw question.
"""
import json, re, collections, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.cluster import AgglomerativeClustering

T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
PREC, MIN_SUP, MAXP = float(sys.argv[1]) if len(sys.argv) > 1 else 0.97, int(sys.argv[2]) if len(sys.argv) > 2 else 5, 3
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()


def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    s = re.sub(r'[A-Z]{1,3}\d{0,2}-\d{2,3}', 'CARD', s); return re.sub(r'\d+', 'N', s)


reason = lambda a: tpl(re.sub(r'^\s*(네|예|아니요|아니오|아뇨)[,，.\s]+[^.]*?니다\.\s*', '', cq(a), count=1).strip())
# question text the page can match: quoted names and card numbers removed, whitespace removed
qkey = lambda q: re.sub(r'\s+', '', re.sub(r'「[^「」]*」|[A-Z]{1,3}\d{0,2}-\d{2,3}', '·', q))


def grams(s, lo=4, hi=8):
    return {s[i:i + n] for n in range(lo, hi + 1) for i in range(len(s) - n + 1) if '·' not in s[i:i + n]}


def groups_of(ids):
    ids = [i for i in ids if len(reason(QA[i][2])) >= 15]
    X = normalize(TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform([reason(QA[i][2]) for i in ids]))
    lab = AgglomerativeClustering(n_clusters=None, distance_threshold=0.35, metric='cosine', linkage='average').fit(X.toarray()).labels_
    m = collections.defaultdict(list)
    for i, l in zip(ids, lab): m[int(l)].append(i)
    return [v for v in m.values() if len(v) >= MIN_SUP]


def mine(pool):
    yn = [i for i in pool if QA[i][8] >= 0]
    G = {i: grams(qkey(QA[i][1])) for i in yn}
    inv = collections.defaultdict(set)
    for i, g in G.items():
        for x in g: inv[x].add(i)
    out = []
    for mem in groups_of(pool):
        my = [i for i in mem if QA[i][8] >= 0]
        if len(my) < MIN_SUP or len({QA[i][0] for i in my}) < 2: continue
        pos = [QA[i][8] ^ QA[i][9] for i in my]; gy = int(np.mean(pos) >= 0.5)
        if max(np.mean(pos), 1 - np.mean(pos)) < 0.95: continue
        cnt = collections.Counter(x for i in my for x in G[i])
        cand = [x for x, c in cnt.items() if c >= max(MIN_SUP, 0.5 * len(my))]
        ok = lambda S: [i for i in S if (gy ^ QA[i][9]) == QA[i][8]]
        chosen, S = [], set(yn)
        for _ in range(MAXP):
            best = None
            for x in cand:
                if x in chosen: continue
                S2 = S & inv[x]
                if len(S2) < MIN_SUP: continue
                p = len(ok(S2)) / len(S2)
                key = (p, len(S2), len(x))
                if best is None or key > best[0]: best = (key, x, S2)
            if not best: break
            chosen.append(best[1]); S = best[2]
            if best[0][0] >= PREC: break
        if not chosen or len(S) < MIN_SUP: continue
        p = len(ok(S)) / len(S)
        if p < PREC: continue
        # drop phrases contained in another chosen phrase
        chosen = [x for x in chosen if not any(x != y and x in y for y in chosen)]
        rep = collections.Counter(reason(QA[i][2]) for i in my).most_common(1)[0][0]
        out.append({'phrases': chosen, 'yes': gy, 'support': len(S), 'prec': round(p, 4), 'members': len(my), 'reason': rep[:200],
                    'qa': sorted(S)})
    return out


def match(iss, i):
    k = qkey(QA[i][1]); return all(x in k for x in iss['phrases'])


if __name__ == '__main__':
    L = [i for i, r in enumerate(QA) if r[0]]
    pool = [i for i in L if prod(QA[i][0]) not in NEW]; test = [i for i in L if prod(QA[i][0]) in NEW and QA[i][8] >= 0]
    iss = mine(pool)
    print('mined issues (pool only):', len(iss))
    hit, ok, conflict, per = 0, 0, 0, []
    for i in test:
        ms = [s for s in iss if match(s, i)]
        if not ms: continue
        ans = {s['yes'] ^ QA[i][9] for s in ms}
        if len(ans) > 1: conflict += 1; continue
        hit += 1; a = ans.pop(); ok += a == QA[i][8]
        for s in ms: per.append((s['reason'][:60], a == QA[i][8]))
    print(f'test yes/no {len(test)} | answered {hit} ({hit / len(test):.1%}) | acc {ok / max(1, hit):.1%} | conflicts {conflict}')
    bad = collections.Counter(r for r, c in per if not c)
    print('wrong by issue:', bad.most_common(5))
    E = json.load(open('net/engine_py_test.json'))
    extra = [i for i in test if any(match(s, i) for s in iss) and not (str(i) in E and E[str(i)][1] >= 0.8)]
    xo = sum(1 for i in extra if len({s['yes'] ^ QA[i][9] for s in iss if match(s, i)}) == 1 and (next(s for s in iss if match(s, i))['yes'] ^ QA[i][9]) == QA[i][8])
    print(f'beyond the engine (conf<0.80): {len(extra)} answered, {xo} correct')
    json.dump({'prec_threshold': PREC, 'n_issues_pool': len(iss), 'test_n': len(test), 'answered': hit, 'acc': round(ok / max(1, hit), 4), 'conflicts': conflict,
               'beyond_engine': len(extra), 'beyond_engine_correct': xo, 'issues': [{k: v for k, v in s.items() if k != 'qa'} for s in iss]},
              open('paper/results/issue_mine.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    full = mine(L)
    json.dump([{**{k: v for k, v in s.items()}, 'id': f'auto{k}'} for k, s in enumerate(full)], open('rule_issues_auto.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('mined on all data for the page:', len(full))
