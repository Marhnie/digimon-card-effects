"""Standardize the *situation*, not the question verb: extract slot values (zone, event, actor,
manner, timing, …) from each question and test whether matching on slots improves Claude-free answers."""
import json, re, collections, numpy as np
exec(open('q_intent.py', encoding='utf-8').read().split('# ---- simulation')[0])  # D, intent()

SLOTS = {
    '영역': [('육성 에어리어', r'육성'), ('배틀 에어리어', r'배틀 에어리어'), ('패', r'패(?:에서|의|로|에|를)'), ('트래시', r'트래시'),
            ('시큐리티', r'시큐리티'), ('진화원', r'진화원'), ('덱', r'덱(?:의|에서|으로|을|위|아래)'), ('디지타마 덱', r'디지타마')],
    '사건': [('등장', r'등장'), ('진화', r'진화(?!원)'), ('소멸', r'소멸'), ('어택', r'어택'), ('블록', r'블록'), ('배틀', r'배틀(?! 에어리어)'),
            ('레스트', r'레스트'), ('액티브', r'액티브'), ('파기', r'파기'), ('되돌림', r'되돌|돌아가'), ('드로우', r'드로우'), ('링크', r'링크'),
            ('디지크로스', r'디지크로스'), ('조그레스', r'조그레스'), ('퇴화', r'퇴화'), ('부화', r'부화'), ('이동', r'이동'), ('체크', r'체크'),
            ('옵션 사용', r'사용'), ('공개·오픈', r'공개|오픈'), ('DP 변화', r'DP'), ('메모리', r'메모리'), ('코스트', r'코스트')],
    '주체': [('상대', r'상대'), ('자신', r'자신'), ('테이머', r'테이머'), ('옵션', r'옵션'), ('토큰', r'토큰'), ('이 카드', r'이 (?:카드|디지몬)')],
    '방식': [('효과로', r'효과로|효과에 의해'), ('룰로', r'룰(?:로|에 의해|처리)'), ('코스트 미지불', r'코스트를 지불하지 않'), ('대신·치환', r'대신'),
            ('동시', r'동시'), ('이미 그 상태', r'이미'), ('0장·없음', r'0장|없는|없을|없다면'), ('[턴 1회]', r'\[턴|1회'),
            ('다른 효과 부여', r'얻|주어|부여'), ('취급', r'취급'), ('진화 조건 무시', r'진화 조건'), ('도중·처리 중', r'도중|처리 중|중에')],
    '타이밍': [(t, re.escape('【' + t + '】')) for t in ['등장 시', '진화 시', '소멸 시', '어택 시', '메인', '자신의 턴', '상대의 턴', '서로의 턴', '시큐리티', '어택 종료 시', '카운터']],
    '부정': [('부정 질문', r'(?:없|않|못)(?:습니까|나요|는지|을까요)|(?:없|않)[^.?]{0,6}[?？]?\s*$')],
}
SLOTS = {k: [(n, re.compile(p)) for n, p in v] for k, v in SLOTS.items()}
def slots(q):
    return {f'{k}:{n}' for k, v in SLOTS.items() for n, p in v if p.search(q)}
for d in D: d['sl'] = slots(d['q'])
print('평균 슬롯 수', np.mean([len(d['sl']) for d in D]).round(1))

L = [d for d in D if d['y'] is not None]; n = len(L); Y = np.array([d['y'] for d in L])
def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', '「X」', s)
    return re.sub(r'\d+', 'N', s)
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
raw = [d['q'] for d in L]; tq = [tpl(d['q']) for d in L]
X = normalize(hstack([TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform(raw),
                      TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), sublinear_tf=True, min_df=2).fit_transform(tq)]).tocsr())
S = (X @ X.T).toarray(); np.fill_diagonal(S, 0)
cards = np.array([d['card'] for d in L])
S[(S > 0.92) | ((S > 0.55) & (cards[:, None] == cards[None, :]))] = -1
# slot similarity matrix (Jaccard) via binary vectors
names = sorted({s for d in L for s in d['sl']}); idx = {s: i for i, s in enumerate(names)}
B = np.zeros((n, len(names)), np.float32)
for i, d in enumerate(L):
    for s in d['sl']: B[i, idx[s]] = 1
inter = B @ B.T; cnt = B.sum(1); J = inter / (cnt[:, None] + cnt[None, :] - inter + 1e-9)
neg = B[:, idx['부정:부정 질문']] if '부정:부정 질문' in idx else np.zeros(n)
pats = np.array([d['pat'] for d in L])

def run(alpha, exact=False, k=15, p=4.0, label=''):
    pred = np.zeros(n, int); conf = np.zeros(n)
    for i in range(n):
        s = S[i].copy()
        if exact:  # only neighbours whose situation slots are identical (what a structured form would give)
            s[J[i] < 0.999] = -1
        if (s > 0.05).sum() == 0: s = S[i].copy()
        top = np.argpartition(-s, k)[:k]
        base = np.clip(S[i][top], 0, None) ** p
        w = base * (1 + alpha * J[i][top]) ** 3 * np.where(pats[top] == pats[i], 1.8, 1.0)
        yy = Y[top] ^ (neg[top].astype(int) ^ int(neg[i]))
        yes = (w * (yy == 1)).sum(); no = (w * (yy == 0)).sum()
        pred[i] = int(yes >= no); conf[i] = abs(yes - no) / (yes + no + 1e-9)
    hi = conf > np.quantile(conf, 0.5)
    print(f'{label:36} 정답률 {(pred == Y).mean():.3f} | 확신 상위 50% {(pred[hi] == Y[hi]).mean():.3f}')
run(0, label='자유 질문 (지금)')
for a in (1, 3, 6):
    run(a, label=f'상황 슬롯 일치 가중 ×{a}')
run(3, exact=True, label='상황 슬롯 완전 일치 이웃 우선')
c = collections.Counter(s for d in L for s in d['sl'])
print('자주 나오는 슬롯', c.most_common(25))
