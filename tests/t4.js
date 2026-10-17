const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');const errs=[];let prompt=null;
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.addEventListener('error',e=>errs.push(e.message));
  const fake=async()=>{};fake.json=async(p,o)=>{prompt=p;const ids=[...p.matchAll(/^\[([QR][\w.-]+)\]/gm)].map(m=>m[1]);return {verdict:'아니요',summary:'테스트',reasons:[{text:'근거 1',cite:[ids[0],ids[1],'Q999999']}],caution:''}};
  w.claude={use:async n=>n==='sample'?fake:null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function ask(card,unitIdx,q){$('q').value=card;$('go').click();d.querySelectorAll('[data-ask]')[unitIdx].click();
  $('askq').value=q;$('askq').dispatchEvent(new w.Event('input'));
  const it=$('askit').selectedOptions[0].textContent;const sl=[...d.querySelectorAll('[data-slot][aria-pressed=true]')].map(b=>b.textContent);
  $('askgo').click();await sleep(300);
  const v=d.querySelector('#askres .verdict');return {it,sl,lvl:v&&v.querySelector('.lvl').textContent,big:v&&v.querySelector('.big')?.textContent,prec:d.querySelectorAll('#askres .qa').length,cites:[...d.querySelectorAll('#askres .cite')].map(c=>c.textContent)}}
(async()=>{
  console.log(JSON.stringify(await ask('BT22-007',0,'육성 에어리어의 이 카드의 진화원이 10장 이상 있고, 그중 「마더 이터」가 2장만 있는 상황입니다. 이 카드의 효과로 「마더 이터」를 2장만 등장시킬 수 있습니까?')));
  console.log(JSON.stringify(await ask('EX5-021',0,'이 카드의 효과로 육성 에어리어에 디지몬을 등장시켰을 때, 「자신/상대의 디지몬이 등장했을 때」의 효과는 발휘되나요?')));
  console.log('prompt chars',prompt&&prompt.length, prompt&&prompt.slice(0,300).replace(/\n/g,' | '));
  console.log(JSON.stringify(await ask('BT14-033',0,'이 카드의 효과로 시큐리티를 공개했을 때, 공개한 카드는 시큐리티로 되돌리나요?')));
  console.log('errors',errs);
})();
