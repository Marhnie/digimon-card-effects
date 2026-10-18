// Explanation questions (not yes/no) on newest products, distribution build: share answered with an official answer, and answer agreement (char-bigram Jaccard >= 0.5 with the true official answer)
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-dist.html','utf8');const T=JSON.parse(fs.readFileSync('test_data4.json','utf8'));
const NEW=new Set(['BT22','BT23','BT24','EX9','EX10','ST21','ST22']);const prod=c=>((c||'').match(/^([A-Z]+\d*)-/)||[])[1];
const items=T.qa.map((r,i)=>({i,card:r[0],q:r[1],a:r[2],unit:r[3],y:r[8]})).filter(x=>x.y<0&&NEW.has(prod(x.card)));
const cq=s=>s.replace(/\s*\d{4}\/\d{2}\/\d{2}\s*업데이트\s*/g,' ').trim();const bg=s=>{s=s.replace(/\s+/g,'');const o=new Set();for(let i=0;i<s.length-1;i++)o.add(s.slice(i,i+2));return o};
const jac=(a,b)=>{const A=bg(a),B=bg(b);let x=0;for(const g of A)if(B.has(g))x++;return x/((A.size+B.size-x)||1)};
const dom=new JSDOM('<!doctype html><html><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.__exProducts=NEW;w.claude={use:async()=>null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{await sleep(300);let n=0,dec=0,agree=0,sx=0;const bad=[];
 for(const it of items){for(let g=0;g<8;g++){const b=[...d.querySelectorAll('button')].find(b=>/빼기/.test(b.textContent));if(!b)break;b.click()}
  await sleep(2);type($('cardq'),it.card);$('cardq').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await sleep(2);
  const rs=[...d.querySelectorAll('input[name=mainEff]')];const r=rs.find(r=>+r.value===it.unit)||rs[0];if(r){r.checked=true;r.dispatchEvent(new w.Event('change',{bubbles:true}))}
  if(!d.querySelector('input[name=mainEff]:checked')&&!rs.length){}
  type($('askq'),it.q);$('go').click();await sleep(2);n++;const R=w.__decTest();if(/효과 구조 설명/.test($('result').textContent))sx++;
  if(R&&R.dec){dec++;const a=R.by==='explain'?T.qa[R.ans][2]:null;const B=(globalThis.BY=globalThis.BY||{});B[R.by]=(B[R.by]||0)+1;if(a!=null){const s=jac(cq(a),cq(it.a));if(s>=0.5)agree++;else bad.push([it.i,R.ans,s.toFixed(2)])}else agree+=0}}
 console.log('explanation questions',n,'answered (official answer reuse)',dec,(dec/n*100).toFixed(1)+'%','agree',agree,(agree/dec*100).toFixed(1)+'%','| structure explanation shown',sx);
 console.log('by',JSON.stringify(globalThis.BY));console.log('disagree',JSON.stringify(bad.slice(0,10)))})();
