// E51: 「AI 의견 보기」 appears only on held questions when the server reports ready, and the opinion is labeled unofficial (mocked AI endpoints)
const {JSDOM}=require('jsdom');const fs=require('fs');const BASE='http://127.0.0.1:8787';
const html=fs.readFileSync('server/static/index.html','utf8');let calls=0;
const mock=(u,o)=>{const p=new URL(u,BASE+'/').pathname;
  if(p==='/api/ai/usage')return Promise.resolve(new Response(JSON.stringify({ready:true}),{status:200}));
  if(p==='/api/ai'){calls++;return Promise.resolve(new Response(JSON.stringify({ans:1,confidence:'medium',summary:'테스트 의견입니다.',refs:[{id:'Q1',ref:12}],label:'AI 의견 · 비공식'}),{status:200}))}
  return fetch(new URL(u,BASE+'/').href,o)};
const dom=new JSDOM('<!doctype html><html><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,url:BASE+'/',beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.__noVerdictSave=1;w.fetch=mock}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const sleep=ms=>new Promise(r=>setTimeout(r,ms));const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
let bad=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)bad++};
(async()=>{await sleep(2500);type($('cardq'),'BT1-010');$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(50);
 const rb=d.querySelector('input[name=mainEff]');if(rb){rb.checked=true;rb.dispatchEvent(new w.Event('change',{bubbles:true}))}
 type($('askq'),'아무 근거도 없을 것 같은 완전히 새로운 상황의 질문인데 이게 되나요 zzqx');$('go').click();await sleep(1200);
 const held=/판정 보류/.test($('result').textContent);ok(held,'question is held');
 const b=$('aiopbtn');ok(!!b,'AI 의견 보기 button shown when ready');if(b){b.click();await sleep(400)}
 const t=$('result').textContent;ok(/AI 의견 · 비공식/.test(t)&&/테스트 의견/.test(t)&&/공식 판정이 아닙니다/.test(t),'opinion shown with unofficial label');ok(calls===1,'called once');
 console.log(bad?bad+' failed':'all passed');process.exit(bad?1:0)})();
