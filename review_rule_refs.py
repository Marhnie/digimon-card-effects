import json,re,collections
kr=json.load(open('rules2.json',encoding='utf-8')); jp=json.load(open('jp.json',encoding='utf-8'))
K=[r for r in kr['rules'] if r['l']>=0]; J=[r for r in jp['rules'] if r['l']>=0]
print('count',len(K),len(J))
diff=[(a['n'],b['n']) for a,b in zip(K,J) if a['n']!=b['n']]
print('numbering diffs',len(diff),diff[:5])
# refs: number + bracket title
refre=re.compile(r'(\d+(?:-\d+)*)\.?\s?[「『]([^」』]+)[」』]')
def heads(R):
    m=collections.defaultdict(list)
    for r in R: m[re.sub(r'[「」《》『』\s・·]','',r['t'])].append(r['n'])
    return m
def check(R,label):
    byn={r['n']:r for r in R}; H=heads(R); res=[]
    for r in R:
        for m in refre.finditer(r['t']):
            num,title=m.group(1),m.group(2)
            if '-' not in num and not num.isdigit(): continue
            ctx=r['t'][max(0,m.start()-12):m.end()+6]
            if not re.search(r'참조|参照',r['t'][m.end():m.end()+12]): continue
            tgt=byn.get(num); tt=re.sub(r'[「」《》『』\s・·]','',tgt['t']) if tgt else None
            key=re.sub(r'[「」《》『』\s・·]','',title)
            ok = tgt is not None and (tt==key or key in tt or tt in key)
            res.append({'at':r['n'],'num':num,'title':title,'ok':ok,'target':tgt['t'][:30] if tgt else None,'where':H.get(key)})
    return res
rk=check(K,'KR'); rj=check(J,'JP')
print('refs',len(rk),len(rj))
bad=[x for x in rk if not x['ok']]
print('KR bad',len(bad))
for x in bad: print(x)
# also plain number refs without title, e.g. "(자세한 내용은 15-8 참조)"
plain=re.compile(r'(\d+(?:-\d+)+)\.?\s*(?:을|를|의|에서)?\s*참조')
for r in K:
    for m in plain.finditer(r['t']): print('PLAIN',r['n'],m.group(0), K and ({x['n'] for x in K}.__contains__(m.group(1))))
json.dump({'kr':rk,'jp':rj},open('refs.json','w',encoding='utf-8'),ensure_ascii=False)
