"""What do card Q&A questions ask? Rule-based intent tags, then: does knowing the intent
(as a standardized question form would) make Claude-free answers more accurate?"""
import json, re, collections, numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

QI = json.load(open('qa_items.json', encoding='utf-8'))
U = json.load(open('units3.json', encoding='utf-8'))
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
lab = lambda a: 1 if re.match(r'^\s*(네|예)[,，.\s]', a) else (0 if re.match(r'^\s*(아니요|아니오|아뇨)[,，.\s]', a) else None)

# order matters: the first match is the question's intent (what is being asked)
INTENTS = [
    ('처리 순서', r'어느 (?:쪽|것)(?:이|을|부터)?[^.?]{0,20}(?:먼저|순서)|순서(?:는|로|대로)|먼저 (?:처리|발휘|유발)'),
    ('정의·의미', r'(?:이란|란|라는 것은|는 것은)[^?]{0,25}(?:가리킵|무엇|어떤|의미)|가리킵니까|가리키나요|무엇입니까|무엇인가요|의미합니까'),
    ('수치 결과', r'몇 ?(?:장|마리|번|회|개)|DP는 (?:얼마|어떻게|몇)|얼마(?:가|인가|입니까)|몇이'),
    ('유발·발휘 여부', r'유발(?:합니까|하나요|됩니까|되나요|하지 않|되지 않|할까요)|발휘(?:됩니까|되나요|합니까|하나요|할 수 있|되지 않|하지 않)'),
    ('대상 선택 가능', r'(?:대상으로|대상에|선택(?:할|하는 것이|해서)|고를 수|지정할 수)[^?]{0,20}(?:수 있|가능)'),
    ('횟수 제한', r'\[턴 ?\d회\]|턴(?:에)? ?\d회|소비(?:합니까|하나요|하지)'),
    ('포함·해당 여부', r'포함(?:합니까|되나요|됩니까|하나요)|해당(?:합니까|하나요|됩니까|되나요)|취급(?:됩니까|되나요|합니까|하나요)|간주'),
    ('지속·종료', r'(?:계속|남(?:습니까|나요|아 있)|사라(?:집니까|지나요)|유지(?:됩니까|되나요)|끝나|종료(?:됩니까|되나요))'),
    ('결과(어떻게 되나)', r'어떻게 (?:되|처리|됩|하)'),
    ('가능 여부', r'수 (?:있|없)(?:습니까|나요|을까요|는지)|가능(?:합니까|한가요|하나요)'),
    ('여부(그 밖)', r'(?:습니까|나요|까요)\s*$'),
]
INTENTS = [(n, re.compile(p)) for n, p in INTENTS]
def intent(q):
    for n, p in INTENTS:
        if p.search(q): return n
    return '기타'

D = []
for q in QI:
    qq = cq(q['q']); u = U[q['unit']] if q['unit'] is not None else None
    D.append({'q': qq, 'y': lab(cq(q['a'])), 'it': intent(qq), 'card': q['card'] or '',
              'pat': u['pattern'] if u else -1, 'types': set(u['types']) if u else set(), 'timing': set(u['timing']) if u else set()})
c = collections.Counter(d['it'] for d in D)
print('all card Q&A', len(D))
for k, v in c.most_common():
    ys = [d['y'] for d in D if d['it'] == k and d['y'] is not None]
    print(f'  {k:12} {v:5} ({v / len(D):.0%})  네/아니요형 {len(ys):4}  네 비율 {np.mean(ys) if ys else 0:.2f}')

# ---- simulation: kNN restricted to the same intent (+ same effect type) vs unrestricted ----
L = [d for d in D if d['y'] is not None]; n = len(L); Y = np.array([d['y'] for d in L])
def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    return re.sub(r'\d+', 'N', s)
raw = [d['q'] for d in L]; tq = [tpl(d['q']) for d in L]
X = normalize(hstack([TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform(raw),
                      TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform(tq)]).tocsr())
S = (X @ X.T).toarray(); np.fill_diagonal(S, 0)
cards = np.array([d['card'] for d in L])
# same leakage rule as the Claude test: drop the question's own restatements
leak = (S > 0.92) | ((S > 0.55) & (cards[:, None] == cards[None, :]))
S[leak] = -1
its = np.array([d['it'] for d in L]); pats = np.array([d['pat'] for d in L])
def run(mask_fn, k=15, p=4.0, label=''):
    pred = np.zeros(n, int); cover = 0; conf = np.zeros(n)
    for i in range(n):
        s = S[i].copy(); m = mask_fn(i); s[~m] = -1
        top = np.argpartition(-s, k)[:k]; top = top[s[top] > 0.05]
        if len(top) == 0:
            s = S[i]; top = np.argpartition(-s, k)[:k]  # fall back to unrestricted
        else: cover += 1
        w = np.clip(S[i][top], 0, None) ** p
        w = w * np.where(pats[top] == pats[i], 1.8, 1.0) * np.where((pats[i] >= 0), 1, 1)
        yes = (w * (Y[top] == 1)).sum(); no = (w * (Y[top] == 0)).sum()
        pred[i] = 1 if yes >= no else 0; conf[i] = abs(yes - no) / (yes + no + 1e-9)
    acc = (pred == Y).mean()
    hi = conf > np.quantile(conf, 0.5)
    print(f'{label:34} 정답률 {acc:.3f} | 확신 상위 50% {(pred[hi] == Y[hi]).mean():.3f} | 같은 조건 이웃 있음 {cover / n:.0%}')
everyone = np.ones(n, bool)
run(lambda i: everyone, label='자유 질문 (지금)')
run(lambda i: its == its[i], label='질문 유형 일치')
tsets = [d['types'] for d in L]
run(lambda i: (its == its[i]) & np.array([bool(tsets[i] & t) or not tsets[i] for t in tsets]), label='질문 유형 + 효과 유형 일치')
run(lambda i: (its == its[i]) & (pats == pats[i]) if pats[i] >= 0 else its == its[i], label='질문 유형 + 효과 패턴 일치')
json.dump([[d['q'], d['it']] for d in D[:400]], open('intent_sample.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
