// Review page round trip: reviewer signed out → 결과 복사 code → owner 결과 가져오기 → stored as that reviewer
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2]||'effect-review.html','utf8');const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function open(claude,errs){const ls={};return new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){
  w.scrollTo=()=>{};w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.addEventListener('error',e=>errs.push(e.message));
  Object.defineProperty(w,'localStorage',{value:{getItem:k=>ls[k]??null,setItem:(k,v)=>{ls[k]=String(v)},removeItem:k=>{delete ls[k]}}});
  Object.defineProperty(w.navigator,'clipboard',{value:{writeText:async t=>{w.__clip=t}}});
  if(claude)w.claude=claude(w)}})}
(async()=>{const errs=[];
 // 1) signed out reviewer: no claude runtime → db null
 const A=open(null,errs);const wa=A.window,da=wa.document;await sleep(300);
 const key=k=>da.dispatchEvent(new wa.KeyboardEvent('keydown',{key:k,code:/^[1-5]$/.test(k)?'Digit'+k:k,bubbles:true}));
 console.log('warn',(da.querySelector('.warn')||{}).textContent?.slice(0,30));
 key('Enter');await sleep(50);key('5');key('Enter');await sleep(50);key('Enter');await sleep(80);
 da.getElementById('exportBtn').click();await sleep(80);
 const code=wa.__clip;console.log('exported',code&&code.slice(0,12),'len',code&&code.length,'| box',da.getElementById('exportBox').textContent.slice(0,40));
 // 2) owner signed in imports it
 const store={};const mkdb=()=>({doc:p=>({set:async v=>{store[p]=v},get:async()=>({exists:!!store[p],data:()=>store[p]})}),collection:p=>({get:async()=>{const pre=p+'/';return {docs:Object.keys(store).filter(k=>k.startsWith(pre)&&!k.slice(pre.length).includes('/')).map(k=>({id:k.slice(pre.length),data:()=>store[k]}))}}})});
 const db=mkdb();const B=open(()=>({use:async n=>n==='db'?db:n==='user'?{id:async()=>'owner',isOwner:async()=>true,me:async()=>({name:'주인'}),profiles:async ids=>Object.fromEntries(ids.map(i=>[i,{name:''}]))}:null}),errs);
 const wb=B.window,db_=wb.document;await sleep(300);
 db_.querySelector('[data-view=dash]').click();await sleep(300);
 db_.getElementById('impName').value='김검수';db_.getElementById('impCode').value=code;db_.getElementById('impGo').click();await sleep(1500);
 const ids=Object.keys(store).filter(k=>/^rv\/import-[^/]+$/.test(k));
 console.log('imported docs',ids,ids.map(k=>JSON.stringify(store[k])));
 const items=Object.keys(store).filter(k=>/^rv\/import-[^/]+\/items\//.test(k));console.log('items',items.length,JSON.stringify(store[items.find(k=>k.endsWith('/2'))]||{}).slice(0,160));
 console.log('dash shows name',db_.getElementById('app').textContent.includes('김검수'));
 console.log('errors',errs)})();
