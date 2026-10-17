import re,html,json,urllib.request
from concurrent.futures import ThreadPoolExecutor
def get(u):
    for i in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode('utf-8','ignore')
        except Exception as e: err=e
    raise err
def clean(s):
    s=re.sub(r'<br\s*/?>','\n',s); s=re.sub(r'<!--.*?-->','',s,flags=re.S); s=re.sub(r'<[^>]+>','',s)
    return re.sub(r'[ \t\r\f\v ]+',' ',html.unescape(s)).strip()
def parse(h):
    out=[]
    for b in re.split(r'<li class="image_lists_item',h)[1:]:
        b=re.sub(r'<!--.*?-->','',b,flags=re.S)
        g=lambda p:(lambda m:clean(m.group(1)) if m else '')(re.search(p,b,re.S))
        c={'no':g(r'class="cardno">(.*?)</li>'),'name':g(r'class="card_name">(.*?)</div>'),
           'color':(re.search(r'card_detail card_detail_([\w_]+)',b) or [None,''])[1] if re.search(r'card_detail card_detail_([\w_]+)',b) else '',
           'lv':g(r'class="cardlv">(.*?)</li>'),'parallel':'cardParallel' in b}
        head=re.search(r'<ul class="cardinfo_head">(.*?)</ul>',b,re.S)
        lis=[clean(x) for x in re.findall(r'<li[^>]*>(.*?)</li>',head.group(1),re.S)] if head else []
        c['rarity']=lis[1] if len(lis)>1 else ''; c['type']=lis[2] if len(lis)>2 else ''
        for dt,dd in re.findall(r'<dt>(.*?)</dt>\s*<dd>(.*?)</dd>',b,re.S): c[clean(dt)]=clean(dd)
        if c['no']: out.append(c)
    return out
def page(p): return parse(get(f'https://digimoncard.co.kr/index.php?mid=cardlist&page={p}'))
with ThreadPoolExecutor(6) as ex: res=list(ex.map(page,range(1,293)))
cards=[c for r in res for c in r]
json.dump(cards,open('cards_raw.json','w',encoding='utf-8'),ensure_ascii=False)
print(len(cards), [len(r) for r in res[:3]], [len(r) for r in res[-3:]])
