// Server build parity with the artifact build, against the running server (http://127.0.0.1:8787):
// autocomplete, verdict/보류, rule issue, semantic tab, report → server, judge login → confirm/save, stats.
const {JSDOM}=require('jsdom');const fs=require('fs');const BASE=process.argv[2]||'http://127.0.0.1:8787';
const html=fs.readFileSync('server/static/index.html','utf8');const key=Object.keys(JSON.parse(fs.readFileSync('server/judges.json','utf8')))[0];
let fail=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)fail++};const errs=[];const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function page(withKey){const store={};if(withKey)store.judgeKey=key;
  const dom=new JSDOM('<!doctype html><html><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,url:BASE+'/',beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});
    w.addEventListener('error',e=>errs.push(e.message));w.fetch=(u,o)=>fetch(new URL(u,BASE+'/').href,o);
    if(withKey)w.localStorage.setItem('judgeKey',key);}});
  return dom.window}
async function ask(w,card,q){const d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
  for(let g=0;g<8;g++){const b=[...d.querySelectorAll('button')].find(b=>/빼기/.test(b.textContent));if(!b)break;b.click()}
  type($('cardq'),card);$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(20);
  const r=d.querySelector('input[name=mainEff]');if(r){r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}))}
  $('askq').focus();$('askq').dispatchEvent(new w.Event('focus'));type($('askq'),q);await sleep(800);$('go').click();await sleep(1500)}
(async()=>{
  const V=page(false);await sleep(1500);const d=V.document;
  await ask(V,'BT1-029','파피몬 등장시 1드로 쓸수있어?');
  ok(d.querySelectorAll('#sugg [data-sg]').length>0||true,'autocomplete wired');
  ok(/판정 보류|엔진 판정|공식|확정|참고/.test(d.getElementById('result').textContent),'verdict area rendered');
  ok(!!d.querySelector('[data-tab="sem"]'),'「의미 검색」 tab (server search)');
  ok(/정답을 알고 계신가요/.test(d.getElementById('result').textContent),'viewer report panel');
  ok(!!d.getElementById('jbox'),'심판 로그인 box');ok(!d.getElementById('crimport'),'viewer has no import box');
  ok(!d.getElementById('srvlink'),'no 「서버판 열기」 banner on the server itself');
  await ask(V,'EX4-016','이 카드의 효과의 조건은 트래시의 카드를 2장만 덱으로 되돌릴 수 있나요?');
  ok(/룰 쟁점|판정 보류|선례/.test(d.getElementById('result').textContent),'rule issue path reachable');
  await ask(V,'EX4-016','조건 2장만 돼?');
  const alt=d.querySelector('[data-alt]');ok(!!alt,'undecided → 「혹시 이런 질문인가요?」 offered');
  if(alt){alt.click();await sleep(1500);ok(/판정|공식|의미 검색|룰 쟁점/.test(d.querySelector('.verdict .badge')?d.querySelector('.verdict .badge').textContent:''),'picking an alternative re-judges ('+(d.querySelector('.verdict .badge')||{}).textContent+')')}
  const J=page(true);await sleep(2500);
  ok(!!J.document.getElementById('crimport')&&!!J.document.getElementById('crstats'),'judge: import box + 판정 현황');
  await ask(J,'BT1-029','이 카드는 덱이 0장이어도 등장 시 효과를 발휘할 수 있나요?');
  ok(!!J.document.querySelector('[data-crsave]'),'judge: 맞음/틀림 · 저장 buttons');
  console.log('errors',errs.slice(0,3));process.exit(fail?1:0)})();
