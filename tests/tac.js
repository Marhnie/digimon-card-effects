// Question autocomplete: suggestions appear for the chosen effect; picking this card's official question shows its official answer (no Claude)
const {JSDOM}=require('jsdom');const fs=require('fs');const dist=process.argv.includes('--dist');
const html=fs.readFileSync(dist?'card-effect-dist.html':'card-effect-test.html','utf8');const T=JSON.parse(fs.readFileSync('test_data4.json','utf8'));
let fail=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)fail++};const sleep=ms=>new Promise(r=>setTimeout(r,ms));let calls=0;const errs=[];
const dom=new JSDOM('<!doctype html><html><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.addEventListener('error',e=>errs.push(e.message));
  const f=async()=>{};f.json=async()=>{calls++;return {verdict:'네',summary:'',reasons:[],caution:'',conf:0.5}};w.claude={use:async n=>n==='sample'?f:null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
// a card whose one effect has several yes/no official Q&A
const cnt={};T.qa.forEach(r=>{if(r[3]!=null&&r[3]>=0&&r[8]>=0)cnt[r[3]]=(cnt[r[3]]||0)+1});
const u=+Object.keys(cnt).find(k=>cnt[k]>=4&&T.units.filter(v=>v[0]===T.units[k][0]).length===1);const card=T.units[u][0];
const target=T.qa.findIndex(r=>r[3]===u&&r[8]>=0);
(async()=>{await sleep(300);
  type($('cardq'),card);$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(10);
  const r=d.querySelector('input[name=mainEff]');if(r){r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}))}
  $('askq').focus();$('askq').dispatchEvent(new w.Event('focus'));type($('askq'),T.qa[target][1].slice(0,12));await sleep(10);
  const sg=[...d.querySelectorAll('#sugg [data-sg]')];ok(sg.length>0,'suggestions shown ('+sg.length+') for '+card);
  const mine=sg.find(b=>b.textContent.includes(T.qa[target][1].slice(0,30)));ok(!!mine,'this card\'s official question among suggestions');
  if(mine){mine.click();await sleep(20);const t=$('result').textContent;
    ok(/공식 Q&A/.test(t)&&t.includes(T.qa[target][8]?'네':'아니요'),'picked official question → official answer');ok(calls===0,'no Claude call');}
  // keyboard: ArrowDown + Enter picks first suggestion
  type($('askq'),'효과');await sleep(5);$('askq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));$('askq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(20);
  ok($('askq').value!=='효과','keyboard pick fills the question');
  console.log('errors',errs.slice(0,3));process.exit(fail?1:0)})();
