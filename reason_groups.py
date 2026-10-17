"""Reason groups (이유 묶음): official Q&A clustered by the EXPLANATION in their answer (the sentences after 「네/아니요 …」),
so questions worded differently but decided by the same principle fall together. For the judge helper (all Q&A).
Output: reason_groups.json {qa_index: group}, groups [{name, yes (answer if asked positively), cons, n, cards}]"""
import json, re, collections, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.cluster import AgglomerativeClustering
T = json.load(open('test_data3.json', encoding='utf-8')); QA = T['qa']           # rows: card, q, a, unit, rule, how, it, sl, y, neg, g
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    s = re.sub(r'[A-Z]{1,3}\d{0,2}-\d{2,3}', 'CARD', s); return re.sub(r'\d+', 'N', s)
def reason(a):
    a = re.sub(r'^\s*(네|예|아니요|아니오|아뇨)[,，.\s]+[^.]*?니다\.\s*', '', cq(a), count=1)
    return a.strip()
RS = [reason(r[2]) for r in QA]; RT = [tpl(r) for r in RS]
idx = [i for i, r in enumerate(RT) if len(r) >= 15]
X = normalize(TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform([RT[i] for i in idx]))
lab = AgglomerativeClustering(n_clusters=None, distance_threshold=0.35, metric='cosine', linkage='average').fit(X.toarray()).labels_
mem = collections.defaultdict(list)
for i, g in zip(idx, lab): mem[int(g)].append(i)
groups, of = [], {}
for g, ii in sorted(mem.items(), key=lambda x: -len(x[1])):
    ys = [QA[i][8] ^ QA[i][9] for i in ii if QA[i][8] >= 0]          # answer as if asked positively
    cards = len({QA[i][0] for i in ii})
    if len(ii) < 3 or cards < 2: continue
    yes = float(np.mean(ys)) if ys else None
    rep = collections.Counter(RS[i] for i in ii).most_common(1)[0][0]
    gid = len(groups)
    groups.append({'name': rep[:160], 'yes': (None if yes is None else round(yes, 3)), 'cons': (None if yes is None else round(max(yes, 1 - yes), 3)),
                   'n': len(ii), 'ny': len(ys), 'cards': cards})
    for i in ii: of[i] = gid
json.dump({'of': of, 'groups': groups}, open('reason_groups.json', 'w', encoding='utf-8'), ensure_ascii=False)
ok = [g for g in groups if g['ny'] >= 3 and g['cons'] >= 0.9]
print('reason groups (>=3 Q&A, >=2 cards):', len(groups), '| covering', len(of), 'Q&A | consistent yes/no groups', len(ok), 'covering', sum(g['n'] for g in ok))
for g in groups[:15]: print(g['n'], g['cards'], g['yes'], '|', g['name'][:90])
