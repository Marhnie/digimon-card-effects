import json,re,random
exec(open('q_slots.py',encoding='utf-8').read().split("for d in D: d['sl']")[0])
U=json.load(open('units3.json',encoding='utf-8')); QI=json.load(open('qa_items.json',encoding='utf-8'))
def bg(s):
    s=re.sub(r'\s+','',s); return {s[i:i+2] for i in range(len(s)-1)}
neg_re=SLOTS['부정'][0][1]
for q,d in zip(QI,D):
    d['bg']=bg(d['q']); d['neg']=1 if neg_re.search(d['q']) else 0; d['unit']=q['unit']; d['card']=q['card'] or ''
L=[d for d in D if d['y'] is not None]
random.seed(5); test=random.sample(L,1000)
res={'all':[0,0],'strong':[0,0],'weak':[0,0],'none':0}
for t in test:
    up=U[t['unit']]['pattern'] if t['unit'] is not None else None
    sc=[]
    for d in D:
        if d is t: continue
        x=len(t['bg']&d['bg']); s=x/((len(t['bg'])+len(d['bg'])-x) or 1)
        if s<0.12: continue
        if d['card']==t['card'] and s>0.55: continue       # the question's own restatement on the same card
        if s>0.92: continue                                 # verbatim duplicate elsewhere
        if d['card']==t['card']: s+=0.12
        if up is not None and d['unit'] is not None and U[d['unit']]['pattern']==up: s+=0.08
        sc.append((s,d))
    sc.sort(key=lambda x:-x[0]); yn=[(s,d['y']^(d['neg']^t['neg'])) for s,d in sc if d['y'] is not None][:5]
    if not yn: res['none']+=1; continue
    yes=sum(s**3 for s,y in yn if y); no=sum(s**3 for s,y in yn if not y); ans=1 if yes>=no else 0
    agree=sum(1 for s,y in yn if y==ans); strong=yn[0][0]>=0.45 and agree/len(yn)>=0.8
    ok=int(ans==t['y']); res['all'][0]+=ok; res['all'][1]+=1
    k='strong' if strong else 'weak'; res[k][0]+=ok; res[k][1]+=1
for k in ('all','strong','weak'):
    a,b=res[k]; print(f'{k:6} {a}/{b} = {a/max(b,1):.1%}  (전체의 {b/10:.0f}%)')
print('none',res['none'])
