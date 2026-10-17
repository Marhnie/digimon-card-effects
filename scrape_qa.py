import re,html,json,sys,urllib.request
from concurrent.futures import ThreadPoolExecutor
def get(u):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode('utf-8','ignore')
        except Exception as e: err=e
    raise err
def clean(s):
    s=re.sub(r'<br\s*/?>','\n',s); s=re.sub(r'</(p|div|tr)>','\n',s); s=re.sub(r'<[^>]+>','',s)
    s=html.unescape(s); s=re.sub(r'[ \t\r\f\v ]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s); return s.strip()
def parse(h):
    i=h.find('class="qaResult'); h=h[i:] if i>=0 else ''
    out=[]
    for b in re.split(r'<dl class="qa_box[^"]*"[^>]*>',h)[1:]:
        c=re.search(r'class="qa_category"[^>]*>(.*?)</dt>',b,re.S)
        if not c: continue
        upd=re.findall(r'(\d{4}/\d{2}/\d{2})\s*업데이트',clean(c.group(1)))
        name=re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트','',clean(c.group(1))); name=re.sub(r'\s+',' ',name).strip()
        qs=[]
        for q,a in re.findall(r'<dl class="questions">(.*?)</dl>\s*<dl class="answer">(.*?)</dl>',b,re.S):
            q=clean(re.sub(r'<dt>.*?</dt>','',q,flags=re.S)); a=clean(re.sub(r'<dt>.*?</dt>','',a,flags=re.S))
            q=re.sub(r'^Q\d+\s*','',q); a=re.sub(r'^A\d+\s*','',a)
            qs.append([q,a])
        out.append({'name':name,'upd':upd[0] if upd else '','qa':qs})
    return out
def board(mid,cat):
    res=[]; seen=set()
    for p in range(1,400):
        r=parse(get(f'https://digimoncard.co.kr/index.php?mid={mid}&category={cat}&page={p}'))
        new=[x for x in r if (x['name'],len(x['qa'])) not in seen]
        if not new: break
        for x in new: seen.add((x['name'],len(x['qa']))); res.append(x)
    return res
qh=open('qna.html',encoding='utf-8').read()
cats=re.findall(r'<option[^>]*value="(\d+)"[^>]*>([^<]*)</option>',qh)
rulecats=[('282','기본 규칙'),('9619','키워드 효과'),('9635','상세 규칙'),('9636','용어집')]
def job(t):
    mid,cat,title=t; r=board(mid,cat); print(mid,title,len(r),sum(len(x['qa']) for x in r),flush=True); return (mid,cat,title,r)
jobs=[('rule',c,t) for c,t in rulecats]+[('qna',c,html.unescape(t).strip()) for c,t in cats]
with ThreadPoolExecutor(6) as ex: res=list(ex.map(job,jobs))
json.dump(res,open('qa_raw.json','w',encoding='utf-8'),ensure_ascii=False)
