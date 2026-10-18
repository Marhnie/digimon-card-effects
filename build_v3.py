import json
old=open('test_template.html',encoding='utf-8').read().split('\n')
def block(start_pat,end_pat):
    s=next(i for i,l in enumerate(old) if l.startswith(start_pat)); e=next(i for i,l in enumerate(old) if i>s and l.startswith(end_pat)); return '\n'.join(old[s:e])
logic=block('const D=JSON.parse','/* ---------- rendering')
render=block('/* ---------- rendering','function showText(')
showpat=block('function showPattern(','function run(')
ui=open('v3_ui.js',encoding='utf-8').read()
ex=json.load(open('examples.json',encoding='utf-8')); nb=json.load(open('examples_none.json',encoding='utf-8'))
E=[{'level':lv,'ask_card':x['ask_card'],'ask_name':x['ask_name'],'effect':x['effect'],'q':x['q'],'src':x['src'],'official':x['official']} for lv in ('확정','참고') for x in ex[lv]]+[{'level':'선례 없음','ask_card':x['ask_card'],'ask_name':x['ask_name'],'effect':x['effect'],'q':x['q']} for x in nb]
ui=ui.replace('__EXQ__',json.dumps(E,ensure_ascii=False).replace('</','<\/'))
head=open('v3_head.html',encoding='utf-8').read()
data=open('test_data4.json',encoding='utf-8').read()
import sys
DIST='--dist' in sys.argv
if DIST:
    head=head.replace('<title>디지몬 판정 도우미</title>','<title>디지몬 카드 판정 도우미</title>').replace('<span class="tagline">같은 선례가 있으면 바로, 없으면 Claude가 근거를 찾아 판정합니다</span>','<span class="tagline">공식 Q&amp;A·종합 룰과 확인된 판정으로 답합니다 · 비공식 도구이며 최종 판정은 대회 심판에게 확인하세요</span>')
html=head+('\n<script>window.__DIST__=1</script>' if DIST else '')+'\n<script id="data" type="application/json">'+data+'</script>\n<script>\n(function(){\n'+logic+'\n'+render+'\n'+showpat+'\n'+ui+'\n})();\n</script>\n'
open('card-effect-dist.html' if DIST else 'card-effect-test.html','w',encoding='utf-8').write(html)
print(len(html))
