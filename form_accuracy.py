"""Accuracy of the standardized-question form: answer only when a precedent with the same
situation exists; otherwise say '선례 없음'. Slots/intent are auto-extracted from the official
questions, so this approximates what a filled-in form would give (a real form is cleaner)."""
import json, re, collections, numpy as np
exec(open('q_slots.py', encoding='utf-8').read().split("def run(alpha")[0])  # L, Y, S (leak-masked), J, pats, neg, intent()

its = np.array([d['it'] for d in L])
tsets = [d['types'] for d in L]
same_type = np.array([[bool(a & b) for b in tsets] for a in tsets]) if n < 5000 else None
exact = J > 0.999
valid = S > -0.5                         # leak-masked pairs are -1
np.fill_diagonal(valid, False)           # a question is never its own precedent
negi = neg.astype(int)

def vote(i, cand):
    w = np.clip(S[i][cand], 0.05, None) ** 2
    yy = Y[cand] ^ (negi[cand] ^ negi[i])
    yes = (w * (yy == 1)).sum(); no = (w * (yy == 0)).sum()
    return int(yes >= no), abs(yes - no) / (yes + no)

TIERS = [
    ('A 같은 효과 패턴 + 같은 상황 + 같은 질문', lambda i: valid[i] & exact[i] & (its == its[i]) & (pats == pats[i]) & (pats[i] >= 0)),
    ('B 같은 효과 유형 + 같은 상황 + 같은 질문', lambda i: valid[i] & exact[i] & (its == its[i]) & same_type[i]),
    ('C 같은 상황 + 같은 질문 (효과 무관)',       lambda i: valid[i] & exact[i] & (its == its[i])),
    ('D 비슷한 상황(슬롯 80%↑) + 같은 효과 유형',  lambda i: valid[i] & (J[i] >= 0.8) & same_type[i]),
]
res = {}
answered = np.zeros(n, bool); pred = np.full(n, -1); tier_of = np.full(n, -1); conf = np.zeros(n)
for t, (name, fn) in enumerate(TIERS):
    for i in range(n):
        if answered[i]: continue
        cand = np.where(fn(i))[0]
        if len(cand):
            pred[i], conf[i] = vote(i, cand); answered[i] = True; tier_of[i] = t
print(f'네/아니요 질문 {n}개 (같은 질문의 재진술·같은 카드 유사 질문은 선례에서 제외)\n')
cum_c = cum_ok = 0
for t, (name, _) in enumerate(TIERS):
    m = tier_of == t; c = m.sum(); ok = (pred[m] == Y[m]).sum(); cum_c += c; cum_ok += ok
    print(f'{name:34} 이 단계에서 답함 {c:5} ({c / n:5.1%})  정확도 {ok / max(c, 1):.1%}   | 누적 커버 {cum_c / n:5.1%} 누적 정확도 {cum_ok / max(cum_c, 1):.1%}')
print(f'{"선례 없음":34} {(~answered).sum():5} ({(~answered).mean():5.1%})')
# unanimity: precedents all agree
for t, (name, _) in enumerate(TIERS[:3]):
    m = (tier_of == t) & (conf > 0.999)
    print(f'  {name[:1]} 단계 중 선례가 만장일치인 경우: {m.sum()}개, 정확도 {(pred[m] == Y[m]).mean():.1%}')
