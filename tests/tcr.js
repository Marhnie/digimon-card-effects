// Confirmed rulings (확인 판정): save from a verdict → the same/similar question is answered from the saved ruling without Claude
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');const T=JSON.parse(fs.readFileSync('test_data4.json','utf8'));
const store=[];const subs=[];let claudeCalls=0;
const snap=()=>({docs:store.map((x,k)=>({id:'r'+k,data:()=>x})),size:store.length,empty:!store.length,docChanges:()=>[]});
const db={collection:p=>({onSnapshot:(n)=>{subs.push(n);setTimeout(()=>n(snap()),0);return ()=>{}},add:async d=>{store.push(JSON.parse(JSON.stringify(d)));subs.forEach(n=>n(snap()));return {id:'r'+(store.length-1)}}})};
const sample=async()=>{};sample.json=async()=>{claudeCalls++;return {verdict:'네',summary:'테스트 판정',reasons:[],caution:'',conf:0.6}};
const errs=[];
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.addEventListener('error',e=>errs.push(e.message));
  w.claude={use:async n=>n==='db'?db:n==='user'?{id:async()=>'u-test'}:n==='sample'?sample:null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};const key=(el,k)=>el.dispatchEvent(new w.KeyboardEvent('keydown',{key:k,bubbles:true}));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let fail=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)fail++};
// a card + effect with no official Q&A precedent so the page goes to Claude: pick a unit whose card has no Q&A
const units=T.units.map((u,i)=>({i,card:u[0],cls:(T.st[i]||[])[0]})).filter(u=>u.cls&&u.cls!=='카드 정보(효과 아님)');
const withQA=new Set(T.qa.map(r=>r[0]));const pick=units.find(u=>!withQA.has(u.card)&&T.units.filter(v=>v[0]===u.card).length===1)||units[0];
const Q='이 카드의 효과로 상대의 디지몬을 선택하지 않고 효과를 종료할 수 있나요?';
async function ask(q){for(const b of [...d.querySelectorAll('button')].filter(b=>/빼기/.test(b.textContent)))b.click();await sleep(5);
  type($('cardq'),pick.card);key($('cardq'),'Enter');await sleep(5);const r=[...d.querySelectorAll('input[name=mainEff]')].find(r=>+r.value===pick.i);if(r){r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}))}
  type($('askq'),q);$('go').click();await sleep(30)}
(async()=>{await sleep(300);
  await ask(Q);const calls1=claudeCalls;
  const verdict1=$('result').textContent;
  ok(/판정 확인/.test(verdict1),'confirm panel shown after a verdict ('+pick.card+')');
  const wrong=[...d.querySelectorAll('[data-crsave]')].find(b=>/틀림/.test(b.textContent))||d.querySelector('[data-crsave]');
  d.getElementById('crnote').value='테스트 메모';wrong.click();await sleep(30);
  ok(store.length===1,'ruling saved to db');ok(store[0]&&store[0].card===pick.card&&store[0].by==='u-test'&&store[0].note==='테스트 메모','saved fields (card, by, note)');
  ok(/저장했습니다/.test($('result').textContent),'saved message');
  await ask(Q.replace('종료할 수 있나요','끝낼 수 있나요'));
  const t2=$('result').textContent;
  ok(/확인된 판정/.test(t2),'similar question answered from confirmed ruling');
  ok(claudeCalls===calls1,'no Claude call for the confirmed question (calls '+calls1+' → '+claudeCalls+')');
  ok(d.querySelector('[data-tab="cr"]'),'「확인된 판정」 tab present');
  await ask('이 카드는 진화원에 있을 때 상대의 턴에도 효과가 적용되나요?');
  ok(!/확인된 판정 ·/.test($('result').textContent),'different question not matched');
  console.log('errors',errs.slice(0,3));process.exit(fail?1:0)})();
