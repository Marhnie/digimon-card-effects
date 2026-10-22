// E41: judge panel lists Claude drafts and saves one as a ruling (live server; inserts and removes its own test rows). node tests/tdraft.js
const {JSDOM}=require('jsdom');const fs=require('fs');const {execSync}=require('child_process');const BASE='http://127.0.0.1:8787';
const K=Object.keys(JSON.parse(fs.readFileSync('server/judges.json','utf8')))[0];
const py=s=>execSync('python -c "'+s.replace(/"/g,'\\"')+'"').toString().trim();
const did=py("import sqlite3,json,time;c=sqlite3.connect('server/judge.db');i=c.execute('insert into drafts(doc,at) values(?,?)',(json.dumps({'card':'BT1-001','q':'__E41 ui test__','ans':1,'summary':'ui'}),time.time())).lastrowid;c.commit();print(i)");
const html=fs.readFileSync('server/static/index.html','utf8');
const dom=new JSDOM('<!doctype html><html><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,url:BASE+'/',beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.__noVerdictSave=1;w.localStorage.setItem('judgeKey',K);w.alert=()=>{};w.fetch=(u,o)=>fetch(new URL(u,BASE+'/').href,o)}});
const w=dom.window,d=w.document;const sleep=ms=>new Promise(r=>setTimeout(r,ms));let bad=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)bad++};
(async()=>{await sleep(1500);const jb=d.getElementById('jbox');ok(!!jb,'judge box');jb.open=true;jb.dispatchEvent(new w.Event('toggle'));await sleep(800);
 const box=d.querySelector(`[data-drbox="${did}"]`);ok(!!box&&/__E41 ui test__/.test(box.textContent),'draft listed');
 box.querySelector('[data-act="1"]').click();await sleep(800);ok(!d.querySelector(`[data-drbox="${did}"]`),'draft removed after save');
 const n=py("import sqlite3;c=sqlite3.connect('server/judge.db');print(c.execute(\"select count(*) from rulings where doc like '%__E41 ui test__%'\").fetchone()[0])");ok(n==='1','saved as ruling');
 py("import sqlite3;c=sqlite3.connect('server/judge.db');c.execute(\"delete from rulings where doc like '%__E41 ui test%'\");c.execute(\"delete from drafts where doc like '%__E41 ui test%'\");c.commit()");
 console.log(bad?bad+' failed':'all passed');process.exit(bad?1:0)})();
