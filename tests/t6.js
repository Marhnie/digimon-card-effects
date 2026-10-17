const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');const errs=[];
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.addEventListener('error',e=>errs.push(e.message));
 const f=async()=>{};f.json=async()=>({verdict:'아니요',summary:'t',reasons:[],caution:''});w.claude={use:async()=>f}}});
const w=dom.window,d=w.document;const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{const n=d.querySelectorAll('[data-qex]').length;console.log('example buttons',n);
 for(const i of [0,4,8,13]){const btn=[...d.querySelectorAll('[data-qex]')].find(b=>b.dataset.qex==String(i));if(!btn){d.getElementById('q').value='';d.getElementById('go').click()}
  const b=[...d.querySelectorAll('[data-qex]')].find(b=>b.dataset.qex==String(i));b.click();await sleep(200);
  const v=d.querySelector('#askres .verdict');console.log(i,v&&v.querySelector('.lvl').textContent,'|',v&&(v.querySelector('.big')||{}).textContent);
  d.getElementById('q').value='';d.getElementById('go').click()}
 console.log('errors',errs)})();
