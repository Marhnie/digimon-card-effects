// E48: an explanation ruling (ans null) saved from a Claude draft is shown as 「확인된 설명」 for the same question (live server; cleans up)
const {JSDOM}=require('jsdom');const fs=require('fs');const {execSync}=require('child_process');const BASE='http://127.0.0.1:8787';
const K=Object.keys(JSON.parse(fs.readFileSync('server/judges.json','utf8')))[0];
const py=s=>execSync('python -c "'+s.replace(/"/g,'\\"')+'"').toString().trim();
const Q='[설명 시험] 이 카드의 등장 시 효과로 덱 위를 공개하는 처리 순서는 어떻게 되나요?';
const did=py("import sqlite3,json,time;c=sqlite3.connect('server/judge.db');i=c.execute('insert into drafts(doc,at) values(?,?)',(json.dumps({'card':'BT1-010','others':'','q':'"+Q+"','ans':None,'summary':'초안 설명'},ensure_ascii=False),time.time())).lastrowid;c.commit();print(i)");
let bad=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)bad++};
(async()=>{
 const r=await fetch(BASE+'/api/drafts/'+did+'/approve',{method:'POST',headers:{'content-type':'application/json','x-judge-key':K},body:JSON.stringify({ans:null,summary:'심판이 고친 설명: 덱 위 5장을 공개하고 테이머 1장을 패에 넣은 뒤 나머지를 덱 아래로 되돌립니다.'})});
 ok(r.ok,'approve as explanation '+r.status);
 const L=await (await fetch(BASE+'/api/rulings')).json();const R=L.find(x=>x.q===Q);ok(R&&R.ans===null&&/심판이 고친/.test(R.summary),'stored ans null with edited text');ok(R&&R.agreed===true,'agreed (both explanation)');
 const html=fs.readFileSync('server/static/index.html','utf8');
 const dom=new JSDOM('<!doctype html><html><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,url:BASE+'/',beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.__noVerdictSave=1;w.fetch=(u,o)=>fetch(new URL(u,BASE+'/').href,o)}});
 const w=dom.window,d=w.document,$=i=>d.getElementById(i);const sleep=ms=>new Promise(r=>setTimeout(r,ms));const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
 await sleep(2500);type($('cardq'),'BT1-010');$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(50);
 const rb=d.querySelector('input[name=mainEff]');if(rb){rb.checked=true;rb.dispatchEvent(new w.Event('change',{bubbles:true}))}
 type($('askq'),Q);$('go').click();await sleep(800);
 const txt=$('result').textContent;ok(/확인된 설명/.test(txt)&&/심판이 고친 설명/.test(txt),'page shows 확인된 설명');
 py("import sqlite3;c=sqlite3.connect('server/judge.db');c.execute(\"delete from rulings where doc like '%설명 시험%'\");c.execute(\"delete from drafts where doc like '%설명 시험%'\");c.commit()");
 console.log(bad?bad+' failed':'all passed');process.exit(bad?1:0)})();
