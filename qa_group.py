"""Group card Q&A into fine-grained *issues* (same thing being asked), across cards.
Features: templated question text (card names / numbers / 'this card' removed) + situation slots + intent
+ the effect's timing/type it is about. Picks the cut by answer purity and leave-one-out accuracy."""
import json, re, sys, collections, numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.cluster import AgglomerativeClustering
exec(open('q_slots.py', encoding='utf-8').read().split("for d in D: d['sl']")[0])   # D (all card Q&A), intent(), slots()
U = json.load(open('units3.json', encoding='utf-8')); QI = json.load(open('qa_items.json', encoding='utf-8'))
neg_re = SLOTS['부정'][0][1]

def tpl(q, card):
    s = q
    s = re.sub(r'\s*\d{4}/\d{2}/\d{2}.*$', '', s)
    s = re.sub(r'「[A-Z]{1,3}\d{0,2}-\d{1,3}\s*[^」]*」', '「카드」', s)        # 「BT9-047 폼몬」
    for _ in range(3): s = re.sub(r'「[^「」]{1,30}」', '「X」', s)
    s = re.sub(r'이 (?:카드|디지몬|테이머|옵션)', '이 카드', s)
    s = re.sub(r'\d+', 'N', s)
    s = re.sub(r'레드|블루|옐로|그린|블랙|퍼플|화이트', '色', s)
    return s
rows = []
for q, d in zip(QI, D):
    u = U[q['unit']] if q['unit'] is not None else None
    rows.append({'id': q['id'], 'card': q['card'] or '', 'q': d['q'], 'a': cq(q['a']), 'y': d['y'], 'it': d['it'],
                 'sl': sorted(slots(d['q'])), 'neg': 1 if neg_re.search(d['q']) else 0, 't': tpl(d['q'], q['card']),
                 'tm': u['timing'] if u else [], 'ty': u['types'] if u else [], 'pat': u['pattern'] if u else -1})
n = len(rows)
X1 = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform([r['t'] for r in rows])
tok = lambda r: ' '.join(['S_' + s.replace(' ', '_') for s in r['sl']] + ['I_' + r['it'].replace(' ', '_')] +
                         ['T_' + t.replace(' ', '_') for t in r['tm']] + ['Y_' + t.replace(' ', '_') for t in r['ty'][:3]])
X2 = TfidfVectorizer(token_pattern=r'\S+', lowercase=False).fit_transform([tok(r) for r in rows])
X = normalize(hstack([X1, X2 * 0.6]).tocsr())
Xd = X.toarray().astype(np.float32)
Y = np.array([-1 if r['y'] is None else r['y'] for r in rows]); NEG = np.array([r['neg'] for r in rows])
cards = np.array([r['card'] for r in rows])
S = Xd @ Xd.T

def evaluate(labels):
    groups = collections.defaultdict(list)
    for i, l in enumerate(labels): groups[l].append(i)
    sizes = [len(v) for v in groups.values()]
    # purity: within each multi-member group, share of yes/no answers (negation-normalised) that agree with the majority
    agree = tot = 0
    for v in groups.values():
        ys = [Y[i] ^ NEG[i] for i in v if Y[i] >= 0]
        if len(ys) >= 2: c = collections.Counter(ys); agree += c.most_common(1)[0][1]; tot += len(ys)
    # leave-one-out: predict a yes/no question from the other members of its group (not its own card, not verbatim copies)
    ok = cov = 0; m = 0
    for v in groups.values():
        for i in v:
            if Y[i] < 0: continue
            m += 1
            others = [j for j in v if j != i and Y[j] >= 0 and cards[j] != cards[i] and S[i, j] < 0.95]
            if not others: continue
            vote = collections.Counter(int(Y[j] ^ NEG[j] ^ NEG[i]) for j in others)
            pred = vote.most_common(1)[0][0]; cov += 1; ok += pred == Y[i]
    return len(groups), sum(1 for s in sizes if s == 1), np.mean([s for s in sizes if s > 1]), agree / max(tot, 1), cov / m, ok / max(cov, 1)

if __name__ == '__main__':
    print('Q&A', n)
    best = None
    for th in (0.25, 0.35, 0.45, 0.55, 0.65):
        cl = AgglomerativeClustering(n_clusters=None, metric='cosine', linkage='average', distance_threshold=th).fit(Xd)
        g, single, avg, pur, cov, acc = evaluate(cl.labels_)
        print(f'거리 {th:.2f}: 그룹 {g:5}  단독 {single:5}  여럿 그룹 평균 {avg:4.1f}개  답 일관성 {pur:.1%}  새 질문 커버 {cov:.1%}  정확도 {acc:.1%}')
        np.save(f'qa_labels_{th:.2f}.npy', cl.labels_)
    json.dump(rows, open('qa_rows.json', 'w', encoding='utf-8'), ensure_ascii=False)
