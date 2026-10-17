"""New question -> issue group of its most similar Q&A (bigram Jaccard on the raw question, as the page does) -> group majority."""
import json,re,random,collections,numpy as np
exec(open('sim_est_eval.py',encoding='utf-8').read().split("L=[d for d in D")[0])   # D with bg, neg, unit, card
lab=np.load('qa_labels_0.25.npy')
for k,d in enumerate(D): d['g']=int(lab[k]); d['k']=k
members=collections.defaultdict(list)
for d in D: members[d['g']].append(d)
L=[d for d in D if d['y'] is not None]
random.seed(5); test=random.sample(L,1000)
out=collections.defaultdict(lambda:[0,0])
for t in test:
    best=None;bs=0
    for d in D:
        if d is t: continue
        x=len(t['bg']&d['bg']); s=x/((len(t['bg'])+len(d['bg'])-x) or 1)
        if (d['card']==t['card'] and s>0.55) or s>0.92: continue
        if s>bs: bs,best=s,d
    if not best: continue
    g=best['g']
    mem=[m for m in members[g] if m is not t and m['y'] is not None and not (m['card']==t['card'] and len(t['bg']&m['bg'])/((len(t['bg'])+len(m['bg'])-len(t['bg']&m['bg'])) or 1)>0.55)]
    if len(mem)<2: continue
    ys=[m['y']^(m['neg']^t['neg']) for m in mem]; c=collections.Counter(ys); ans,cnt=c.most_common(1)[0]; cons=cnt/len(ys)
    for th in (0.3,0.4,0.5,0.6):
        if bs>=th:
            for cth in (0.0,0.8,1.0):
                if cons>=cth: k=(th,cth); out[k][0]+=ans==t['y']; out[k][1]+=1
for (th,cth),(a,b) in sorted(out.items()):
    print(f'가장 가까운 질문 유사도≥{th} · 그룹 답 일관성≥{cth:.0%}: 커버 {b/10:.1f}%  정확도 {a/max(b,1):.1%}')
