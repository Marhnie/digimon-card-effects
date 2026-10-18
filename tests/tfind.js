// Does the judge helper surface a given official Q&A? node tests/tfind.js <main> <other|-> "<question>" <qaIndex> [--dist]
const {JSDOM}=require('jsdom');const fs=require('fs');
const [main,other,q,need]=process.argv.slice(2);const dist=process.argv.includes('--dist');
const html=fs.readFileSync(dist?'card-effect-dist.html':'card-effect-test.html','utf8');let prompt=null;const errs=[];
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.addEventListener('error',e=>errs.push(e.message));
  const f=async()=>{};f.json=async p=>{prompt=p;return {verdict:'(모의)',summary:'',reasons:[],caution:'',conf:0.5}};w.claude={use:async n=>n==='sample'?f:null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};const key=(el,k)=>el.dispatchEvent(new w.KeyboardEvent('keydown',{key:k,bubbles:true}));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{await sleep(300);
  type($('cardq'),main);key($('cardq'),'Enter');await sleep(10);
  if(other&&other!=='-'){$('addcard').click();type($('cardq'),other);key($('cardq'),'Enter');await sleep(10)}
  const rs=[...d.querySelectorAll('input[name=mainEff]')];if(rs.length){const r=rs.find(r=>/등장 시/.test(r.closest('label').textContent))||rs[0];r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}))}
  type($('askq'),q);await sleep(5);$('go').click();await sleep(60);
  const res=$('result');const badge=(res.querySelector('.verdict .badge')||{}).textContent;const ans=(res.querySelector('.verdict .ans')||{}).textContent;
  console.log('cards',[...d.querySelectorAll('.cno')].slice(0,4).map(x=>x.textContent).join(' '),'| verdict:',badge,'|',ans);
  console.log('claude asked',!!prompt,'| Q'+need+' in Claude evidence:',!!(prompt&&prompt.includes('[Q'+need+']')));
  const keys=[...d.querySelectorAll('[data-tab]')].map(b=>b.dataset.tab);const where=[];
  for(const k of keys){const b=d.querySelector(`[data-tab="${k}"]`);if(!b)continue;b.click();await sleep(5);if(d.getElementById('it-Q'+need))where.push(d.querySelector(`[data-tab="${k}"]`).textContent)}
  console.log('Q'+need+' shown in tabs:',where.join(' / ')||'none');console.log('errors',errs.slice(0,2))})();
