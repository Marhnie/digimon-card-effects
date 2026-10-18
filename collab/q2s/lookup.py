#!/usr/bin/env python
"""usage: lookup.py ID_OR_NAME [...]   -> compact card info (Korean card data + whether DCGO has it)
       lookup.py --filler           -> vanilla (no-effect) filler card IDs by level, usable as neutral board pieces"""
import json,sys,os,collections
H=os.path.dirname(os.path.abspath(__file__))
EN=json.load(open(os.path.join(H,'dcgo_cards_en.json'),encoding='utf-8'))
C=json.load(open(os.path.join(H,'..','..','cards.json'),encoding='utf-8')); IDS=set(json.load(open(os.path.join(H,'dcgo_ids.json'))))
def show_en(i):
    e=EN[i]
    print(f"   [DCGO 영문] {e['name']} | {e['kind']} Lv{e['lv']} cost{e['cost']} DP{e['dp']} | evo {e['evo']} | traits {e['type']}")
    print('   text:',e['text'].replace('\n',' ')); 
    if e['inh'] not in ('','-'): print('   inherited:',e['inh'])
    if e['sec'] not in ('','-'): print('   security:',e['sec'])
def show(x):
    print(f"## {x['no']} {x['name'].split(' ',1)[-1]} | {x['type']} {x.get('lv','')} | color {x['color']} | 등장코스트 {x.get('등장 코스트')} DP {x.get('DP')} | 진화코스트 {x.get('진화 코스트 1')} | 형태 {x.get('형태')} 속성 {x.get('속성')} 유형 {x.get('유형')} | DCGO:{'yes' if x['no'] in IDS else 'NO'}")
    print('  상단:',x.get('상단 텍스트')); 
    if (x.get('하단 텍스트') or '-')!='-': print('  하단(진화원/시큐리티):',x.get('하단 텍스트'))
if sys.argv[1:]==['--filler']:
    van=collections.defaultdict(list)
    for x in C:
        if x['no'] not in IDS or x.get('parallel'): continue
        t=(x.get('상단 텍스트') or '').replace('-','').strip()+(x.get('하단 텍스트') or '').replace('-','').strip()
        if len(t)<2: van[(x['type'],x['lv'])].append(f"{x['no']}({x['name'].split(' ',1)[-1]} 코스트{x.get('등장 코스트')} {x.get('유형')})")
    for k,v in sorted(van.items()): print(k,'|',', '.join(v[:8]))
else:
    for q in sys.argv[1:]:
        hits=[x for x in C if not x.get('parallel') and (x['no']==q or q in x['name'])]
        for x in hits[:6]: show(x); show_en(x['no']) if x['no'] in EN else None
        if not hits and q in EN: print('## '+q+' (한글 데이터 없음, DCGO에는 있음)'); show_en(q)
        elif not hits:
            m=[k for k,e in EN.items() if q.lower() in e['name'].lower()][:6]
            for k in m: print('## '+k); show_en(k)
            if not m: print('no match:',q)
