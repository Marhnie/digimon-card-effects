// comboRef accuracy on newest-product Q&A whose question names another card (that card's Q&A from older products only)
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');const T=JSON.parse(fs.readFileSync('test_data4.json','utf8'));
const NEW=new Set(['BT22','BT23','BT24','EX9','EX10','ST21','ST22']);const prod=c=>((c||'').match(/^([A-Z]+\d*)-/)||[])[1];
const items=T.qa.map((r,i)=>({i,card:r[0],q:r[1],unit:r[3],y:r[8]})).filter(x=>x.y>=0&&NEW.has(prod(x.card))&&x.unit!=null&&x.unit>=0&&/「[^」]+」|[A-Z]{1,3}\d{0,2}-\d{2,3}/.test(x.q));
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.__exProducts=NEW;const f=async()=>{};f.json=async()=>({verdict:'x',conf:0.5});w.claude={use:async n=>n==='sample'?f:null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};const key=(el,k)=>el.dispatchEvent(new w.KeyboardEvent('keydown',{key:k,bubbles:true}));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{await sleep(300);let n=0,auto=0,fired=0,ok=0;
 for(const it of items){for(let g=0;g<8;g++){const b=[...d.querySelectorAll('button')].find(b=>/빼기/.test(b.textContent));if(!b)break;b.click()}
  await sleep(3);type($('cardq'),it.card);key($('cardq'),'Enter');await sleep(3);
  const r=[...d.querySelectorAll('input[name=mainEff]')].find(r=>+r.value===it.unit);if(!r)continue;r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}));
  type($('askq'),it.q);$('go').click();await sleep(3);const R=w.__crefTest();n++;if(R.auto&&R.auto.length)auto++;if(R.cref){fired++;if(R.cref.ans===it.y)ok++}}
 console.log('items',n,'auto-added other card',auto,'combo ref fired',fired,'correct',ok,fired?(ok/fired*100).toFixed(1)+'%':'')})();
