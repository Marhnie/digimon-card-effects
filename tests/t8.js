const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');const errs=[];let prompt='';
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.addEventListener('error',e=>errs.push(e.message+' @'+e.lineno));
 const f=async()=>{};f.json=async(p)=>{prompt=p;const ids=[...p.matchAll(/^\[([QR][\w.-]+)\]/gm)].map(m=>m[1]);return {verdict:'아니요',summary:'요약',reasons:[{text:'이유',cite:ids.slice(0,2)}],caution:''}};w.claude={use:async()=>f}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
const key=(el,k)=>el.dispatchEvent(new w.KeyboardEvent('keydown',{key:k,bubbles:true}));
const state=()=>({go:$('go').disabled,hint:$('gohint').textContent,verdict:(d.querySelector('.verdict .badge')||{}).textContent,ans:(d.querySelector('.verdict .ans')||{}).textContent,tabs:[...d.querySelectorAll('.tabs button')].map(b=>b.textContent).join(' | ')});
(async()=>{
 console.log('init',JSON.stringify(state()),'examples',d.querySelectorAll('[data-ex]').length);
 type($('cardq'),'파닥');console.log('ac',[...d.querySelectorAll('#ac1 li')].slice(0,3).map(l=>l.textContent).join(' / '));
 key($('cardq'),'ArrowDown');key($('cardq'),'ArrowDown');key($('cardq'),'ArrowDown');key($('cardq'),'Enter');
 console.log('cards',[...d.querySelectorAll('.cb-h')].map(h=>h.textContent.replace(/\s+/g,' ')).join(' || '),'effects',d.querySelectorAll('input[name=mainEff]').length);
 console.log('after card',JSON.stringify(state()));
 const r=d.querySelector('input[name=mainEff]');r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}));
 type($('askq'),'이 카드의 효과로 시큐리티를 전부 확인했지만 진화하지 않았을 때도, 자신의 시큐리티를 셔플하나요?');
 console.log('meta',$('meta').textContent.replace(/\s+/g,' ').slice(0,120));
 console.log('ready',JSON.stringify(state()));
 $('go').click();await sleep(300);console.log('judged',JSON.stringify(state()));
 d.querySelector('.cite')&&d.querySelector('.cite').click();console.log('cite tab ->',(d.querySelector('.tabs [aria-selected=true]')||{}).textContent,'flash',d.querySelectorAll('.item.flash').length);
 // add extra card
 $('addcard').click();type($('cardq'),'BT9-047');key($('cardq'),'Enter');
 console.log('cards now',d.querySelectorAll('.cardbox').length,'result cleared',$('result').innerHTML.length===0);
 $('go').click();await sleep(300);console.log('combo judged',JSON.stringify(state()),'prompt extra',prompt.includes('[함께 관련된 카드] BT9-047'));
 // example
 d.querySelector('[data-ex]').click();await sleep(200);console.log('example',JSON.stringify(state()),'q=',$('askq').value.slice(0,30));
 // slot picker
 d.getElementById('pickt').click();console.log('picker chips',d.querySelectorAll('[data-slot]').length);
 // paste mode
 $('pastetoggle').click();type($('pastebox'),'【등장 시】상대의 디지몬 1마리를 레스트시킨다. 【자신의 턴】이 디지몬을 DP +2000.');
 console.log('paste units',d.querySelectorAll('input[name=mainEff]').length,JSON.stringify(state()));
 // browse
 $('pastetoggle').click();type($('cardq'),'BT22-007');key($('cardq'),'Enter');console.log('browse units',d.querySelectorAll('#out section.unit').length);
 console.log('errors',errs);
})();
setTimeout(()=>{
 const tabs=[...d.querySelectorAll('.tabs button')].map(b=>b.textContent);console.log('final tabs',tabs.join(' | '));
 const sim=[...d.querySelectorAll('.tabs button')].find(b=>b.dataset.tab==='sim');if(sim){sim.click();console.log('sim first',(d.querySelector('.tabp .item .src')||{}).textContent)}
 console.log('verdict badge',(d.querySelector('.verdict .badge')||{}).textContent);
 console.log('prompt QA-first:',prompt.split('[자료]')[1]?.trim().slice(0,160).replace(/\n/g,' '));
},2000);
