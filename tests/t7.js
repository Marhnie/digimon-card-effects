const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');const errs=[];let prompt='';
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.HTMLInputElement.prototype.reportValidity=function(){return false};w.addEventListener('error',e=>errs.push(e.message));
 const f=async()=>{};f.json=async(p)=>{prompt=p;return {verdict:'아니요',summary:'t',reasons:[],caution:''}};w.claude={use:async()=>f}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const key=(k)=>$('q').dispatchEvent(new w.KeyboardEvent('keydown',{key:k,bubbles:true}));
(async()=>{
 // autocomplete
 for(const t of ['파닥','bt14-03','BT1403','메탈그레이','P-10']){ $('q').value=t;$('q').dispatchEvent(new w.Event('input'));
   console.log(t,'->',[...d.querySelectorAll('#ac li[role=option]')].slice(0,4).map(li=>li.textContent).join(' | '))}
 $('q').value='파닥';$('q').dispatchEvent(new w.Event('input'));key('ArrowDown');key('Enter');
 console.log('picked value:',$('q').value,'| out:',d.getElementById('out').textContent.slice(0,80),'| heading:',(d.querySelector('.cardhead')||{textContent:'-'}).textContent.replace(/\s+/g,' ').slice(0,40),'| dropdown hidden',$('ac').hidden);
 // combo
 $('q').value='BT22-007 마더 이터';key('Enter');
 d.querySelector('[data-ask]').click();
 $('xcard').value='BT9-047 폼몬';$('xadd').click();
 console.log('extra chips',d.querySelectorAll('[data-xdel]').length, d.querySelectorAll('[data-xunit] option').length,'options');
 $('askq').value='상대의 폼몬이 배틀 에어리어에 있을 때, 이 카드의 효과로 진화원에서 「마더 이터」를 등장시킬 수 있나요?';$('askq').dispatchEvent(new w.Event('input'));
 $('askgo').click();await sleep(300);
 console.log('verdict:',d.querySelector('#askres .verdict .lvl')?.textContent,'| combo list:',[...d.querySelectorAll('#askres details summary')].map(s=>s.textContent.replace(/\s+/g,' ')).join(' / '));
 console.log('prompt has extra card:',prompt.includes('[함께 관련된 카드] BT9-047'),'| evidence items',(prompt.match(/^\[[QR]/gm)||[]).length);
 console.log('errors',errs);
})();
