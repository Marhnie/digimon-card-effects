// Browser engine vs Python engine on the time-split test: hide the newest products' Q&A, ask each test question, compare
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');const T=JSON.parse(fs.readFileSync('test_data4.json','utf8'));
const NEW=new Set(['BT22','BT23','BT24','EX9','EX10','ST21','ST22']);const prod=c=>((c||'').match(/^([A-Z]+\d*)-/)||[])[1];
const items=T.qa.map((r,i)=>({i,card:r[0],q:r[1],unit:r[3],y:r[8]})).filter(x=>x.y>=0&&NEW.has(prod(x.card))&&x.unit!=null&&x.unit>=0);
const N=+process.argv[2]||items.length;const errs=[];
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.addEventListener('error',e=>errs.push(e.message));w.__exProducts=NEW;const f=async()=>{};f.json=async()=>({verdict:'x',conf:0.5});w.claude={use:async()=>f}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};const key=(el,k)=>el.dispatchEvent(new w.KeyboardEvent('keydown',{key:k,bubbles:true}));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{await sleep(300);const out=[];
 for(const it of items.slice(0,N)){
  // reset to an empty card list by reloading state: remove existing cards
  for(const b of [...d.querySelectorAll('[data-remove],.rmcard,button')].filter(b=>/빼기/.test(b.textContent)))b.click();
  await sleep(5);type($('cardq'),it.card);key($('cardq'),'Enter');await sleep(5);
  const r=[...d.querySelectorAll('input[name=mainEff]')].find(r=>+r.value===it.unit);if(!r){out.push({i:it.i,skip:1});continue}
  r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}));type($('askq'),it.q);$('go').click();await sleep(5);
  const R=w.__engTest();const e=R.eng;if(R.card!==it.card){out.push({i:it.i,skip:2});continue}out.push({i:it.i,y:it.y,ans:e?e.ans:null,conf:e?+e.conf.toFixed(4):null,sure:e?e.sure:false});
 }
 fs.writeFileSync('net/engine_js_test.json',JSON.stringify(out));
 const ok=out.filter(o=>o.conf!=null);const sure=ok.filter(o=>o.sure);
 console.log('asked',out.length,'engine',ok.length,'sure',sure.length,'=',(sure.length/out.length*100).toFixed(1)+'%','acc(sure)',(sure.filter(o=>o.ans===o.y).length/sure.length*100).toFixed(1)+'%','acc(all)',(ok.filter(o=>o.ans===o.y).length/ok.length*100).toFixed(1)+'%');
 console.log('errors',errs.slice(0,3))})();
