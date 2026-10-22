// Distribution build, no Claude: share of newest-product yes/no questions answered decisively, and accuracy (older products only as evidence)
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-dist.html','utf8');const T=JSON.parse(fs.readFileSync('test_data4.json','utf8'));
const NEW=new Set(['BT22','BT23','BT24','EX9','EX10','ST21','ST22']);const prod=c=>((c||'').match(/^([A-Z]+\d*)-/)||[])[1];
const items=T.qa.map((r,i)=>({i,card:r[0],q:r[1],unit:r[3],y:r[8]})).filter(x=>x.y>=0&&NEW.has(prod(x.card))&&x.unit!=null&&x.unit>=0);
const N=+process.argv[2]||items.length;let calls=0;
const dom=new JSDOM('<!doctype html><html><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.__exProducts=NEW;const f=async()=>{};f.json=async()=>{calls++;return {}};w.claude={use:async n=>n==='sample'?f:null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const DUMP=[];(async()=>{await sleep(300);const by={};let n=0,dec=0,ok=0;
 for(const it of items.slice(0,N)){for(let g=0;g<8;g++){const b=[...d.querySelectorAll('button')].find(b=>/빼기/.test(b.textContent));if(!b)break;b.click()}
  await sleep(2);type($('cardq'),it.card);$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(2);
  const r=[...d.querySelectorAll('input[name=mainEff]')].find(r=>+r.value===it.unit);if(!r)continue;r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}));
  type($('askq'),it.q);$('go').click();await sleep(2);const R=w.__decTest();n++;DUMP.push({i:it.i,by:R&&R.dec?R.by:null,ans:R&&R.dec?R.ans:null});if(R&&R.dec){dec++;const b=by[R.by]=by[R.by]||[0,0];b[0]++;if(R.ans===it.y){ok++;b[1]++}}}
 if(process.env.TDEC_DUMP)fs.writeFileSync(process.env.TDEC_DUMP,JSON.stringify(DUMP));console.log('asked',n,'decisive',dec,(dec/n*100).toFixed(1)+'%','acc',(ok/dec*100).toFixed(1)+'%','claude calls',calls);console.log(JSON.stringify(by))})();
