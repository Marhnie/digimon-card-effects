import json,numpy as np
exec(open('form_accuracy.py',encoding='utf-8').read().split("print(f'네/아니요 질문")[0])
gold=json.load(open('eval/gold.json',encoding='utf-8')); res={r['id']:r for r in json.load(open('eval/results.json',encoding='utf-8'))}
QIall=json.load(open('qa_items.json',encoding='utf-8'))
id2L={}
k=0
for q in QIall:
    import re
    if lab(cq(q['a'])) is None: continue
    id2L[q['id']]=k; k+=1
yn=lambda v:1 if v=='네' else 0
eng=cl=0; ne=nc=0; both=0
for tid,g in gold.items():
    i=id2L[g['qa_id']]; r=res[tid]; gy=Y[i]
    if answered[i] and tier_of[i]<=2:
        ne+=1; eng+=(pred[i]==gy)
    else:
        nc+=1; cl+=(yn(r['S3'])==gy)
    both+=(yn(r['S3'])==gy)
print(f'100문항 중 선례 있음 {ne}: 엔진 정답 {eng}/{ne}')
print(f'선례 없음 {nc}: Claude+검색 정답 {cl}/{nc}')
print(f'하이브리드 합계 {eng+cl}/100 , 전부 Claude(S3) {both}/100, Claude 호출 {nc}회(전부 Claude면 100회)')
print('--- 엔진이 답하는 기준을 바꾸면 ---')
for name,cond in [('A~C 전부',lambda i: answered[i] and tier_of[i]<=2),('A~C + 만장일치',lambda i: answered[i] and tier_of[i]<=2 and conf[i]>0.999),
                  ('A만',lambda i: answered[i] and tier_of[i]==0),('A + 만장일치',lambda i: answered[i] and tier_of[i]==0 and conf[i]>0.999)]:
    e=c=ne=0
    for tid,g in gold.items():
        i=id2L[g['qa_id']]; r=res[tid]
        if cond(i): ne+=1; e+=(pred[i]==Y[i])
        else: c+=(yn(r['S3'])==Y[i])
    print(f'{name:14} 엔진 {e}/{ne}  Claude {c}/{100-ne}  합계 {e+c}/100  Claude 호출 {100-ne}회')
# same thresholds on the full 4052 set (engine side only)
for name,cond in [('A~C 전부',(answered)&(tier_of<=2)),('A~C + 만장일치',(answered)&(tier_of<=2)&(conf>0.999)),('A만',(tier_of==0)),('A + 만장일치',(tier_of==0)&(conf>0.999))]:
    print(f'[전체 4052] {name:14} 엔진이 답하는 비율 {cond.mean():.1%}  정확도 {(pred[cond]==Y[cond]).mean():.1%}')
