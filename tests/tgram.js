// E54: 「같은 문법 구조」 tab lists other cards' official Q&A sharing the construct the question is about
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-dist.html','utf8');
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false})}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const sleep=ms=>new Promise(r=>setTimeout(r,ms));const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
let bad=0;const ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m);if(!c)bad++};
(async()=>{await sleep(300);type($('cardq'),'EX5-008');$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(20);
 const rb=[...d.querySelectorAll('input[name=mainEff]')].find(r=>/오픈/.test(r.closest('label')?r.closest('label').textContent:''))||d.querySelector('input[name=mainEff]');rb.checked=true;rb.dispatchEvent(new w.Event('change',{bubbles:true}));
 type($('askq'),'오픈한 카드 중 한쪽만 있으면 그 카드만 패에 넣을 수 있나요?');$('go').click();await sleep(300);
 const tab=[...d.querySelectorAll('[role=tab],button')].find(b=>/같은 문법 구조/.test(b.textContent));ok(!!tab,'tab shown');
 if(tab){tab.click();await sleep(100);const t=$('result').textContent;ok(/문법 구조/.test(t)&&/「A\/B」 선택|여러 칸|덱 오픈/.test(t),'tab body lists constructs and Q&A')}
 console.log(bad?bad+' failed':'all passed');process.exit(bad?1:0)})();
