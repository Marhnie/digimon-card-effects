// Semantic search wiring in the page (with any exported student dir): suggestions + 「의미 검색」 tab; no Claude, verdicts unchanged
const {JSDOM}=require('jsdom');const fs=require('fs'),path=require('path');const dir=process.argv[2]||'train/export_qemb_tiny';
const html=fs.readFileSync('card-effect-dist.html','utf8');let fail=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)fail++};const errs=[];
const dom=new JSDOM('<!doctype html><html><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});
  w.addEventListener('error',e=>errs.push(e.message));w.TextEncoder=require('util').TextEncoder;w.TextDecoder=require('util').TextDecoder;w.__QEMB_BASE='qemb/';
  w.fetch=async u=>{const b=fs.readFileSync(path.join(dir,String(u).replace('qemb/','')));return {ok:true,arrayBuffer:async()=>b.buffer.slice(b.byteOffset,b.byteOffset+b.length)}};w.claude={use:async()=>null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{await sleep(600);ok(w.eval('QEMB.st.ready'),'student loaded via fetch');
  type($('cardq'),'BT1-029');$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(10);
  const r=d.querySelector('input[name=mainEff]');if(r){r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}))}
  $('askq').focus();type($('askq'),'파피몬 등장시 1드로 쓸수있어?');await sleep(20);
  ok([...d.querySelectorAll('#sugg .sg-src')].some(x=>/의미가 비슷한/.test(x.textContent)),'semantic suggestions shown');
  $('go').click();await sleep(30);ok(d.querySelector('[data-tab="sem"]'),'「의미 검색」 tab');
  d.querySelector('[data-tab="sem"]').click();await sleep(10);ok(d.querySelectorAll('.tabp .item').length>0,'semantic evidence listed');
  console.log('errors',errs.slice(0,3));process.exit(fail?1:0)})();
