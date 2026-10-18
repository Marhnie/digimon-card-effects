// Distribution build: Claude only on request; a viewer without write access gets a JD1 report code; an operator imports it → confirmed ruling
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-dist.html','utf8');const T=JSON.parse(fs.readFileSync('test_data4.json','utf8'));
let fail=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)fail++};const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function page(canWrite,store){let calls=0;const subs=[];
  const snap=()=>({docs:store.map((x,k)=>({id:'r'+k,data:()=>x})),size:store.length,empty:!store.length,docChanges:()=>[]});
  const db={collection:()=>({onSnapshot:n=>{subs.push(n);setTimeout(()=>n(snap()),0);return ()=>{}},add:async d=>{if(!canWrite){const e=new Error('denied');e.code='permission_denied';throw e}store.push(JSON.parse(JSON.stringify(d)));subs.forEach(n=>n(snap()));return {}}})};
  const sample=async()=>{};sample.json=async()=>{calls++;return {verdict:'아니요',summary:'모의',reasons:[],caution:'',conf:0.6}};
  const errs=[];
  const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.addEventListener('error',e=>errs.push(e.message));
    w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.claude={use:async n=>n==='db'?db:n==='user'?{id:async()=>canWrite?'u-op':'u-viewer',can:async()=>canWrite}:n==='sample'?sample:null}}});
  return {w:dom.window,d:dom.window.document,calls:()=>calls,errs}}
const units=T.units.map((u,i)=>({i,card:u[0],cls:(T.st[i]||[])[0]})).filter(u=>u.cls&&u.cls!=='카드 정보(효과 아님)');
const withQA=new Set(T.qa.map(r=>r[0]));const pick=units.find(u=>!withQA.has(u.card)&&T.units.filter(v=>v[0]===u.card).length===1);
const Q='이 카드의 효과로 상대의 디지몬을 선택하지 않고 효과를 종료할 수 있나요?';
async function ask(P,q){const {w,d}=P;const $=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
  for(const b of [...d.querySelectorAll('button')].filter(b=>/빼기/.test(b.textContent)))b.click();await sleep(5);
  type($('cardq'),pick.card);$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(5);
  const r=[...d.querySelectorAll('input[name=mainEff]')].find(r=>+r.value===pick.i);if(r){r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}))}
  type($('askq'),q);$('go').click();await sleep(30)}
(async()=>{
  // viewer (no write)
  const V=page(false,[]);await sleep(300);await ask(V,Q);
  ok(V.calls()===0,'distribution: Claude not called automatically');
  ok(/판정 보류/.test(V.d.getElementById('result').textContent),'undecided → 판정 보류 shown (no Claude)');
  ok(/정답을 알고 계신가요/.test(V.d.getElementById('result').textContent),'viewer sees report panel');
  ok(!V.d.getElementById('crimport'),'viewer has no import box');
  V.d.getElementById('crnote').value='공식 Q&A 기준';V.d.querySelector('[data-crrep]').click();await sleep(20);
  const code=(V.d.querySelector('.crcode')||{}).value||'';ok(code.startsWith('JD1:'),'report code produced');
  // operator imports
  const store=[];const O=page(true,store);await sleep(300);
  ok(O.d.getElementById('crimport'),'operator sees import box');
  O.d.getElementById('crin').value=code+'\nJD1:garbage';O.d.getElementById('crpreview').click();await sleep(10);
  ok(/읽지 못한 코드 1개/.test(O.d.getElementById('crprev').textContent)&&!O.d.getElementById('crimp').disabled,'preview parses 1 good / 1 bad');
  O.d.getElementById('crimp').click();await sleep(30);
  ok(store.length===1&&store[0].src==='report'&&store[0].note==='공식 Q&A 기준'&&store[0].reporter==='u-viewer'&&store[0].by==='u-op','imported as ruling (src report, reporter/by)');
  await ask(O,Q.replace('종료할 수 있나요','끝낼 수 있나요'));
  ok(/확인된 판정/.test(O.d.getElementById('result').textContent)&&O.calls()===0,'imported ruling answers similar question without Claude');
  console.log('errors',V.errs.concat(O.errs).slice(0,3));process.exit(fail?1:0)})();
