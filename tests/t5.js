// Run the real page logic: ask each candidate question on a *different* card of the same effect pattern that has no Q&A of its own
const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.claude={use:async()=>null}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);
const data=JSON.parse(d.getElementById('data').textContent);
const U=data.units,QA=data.qa;
const byPat={};U.forEach((u,i)=>{(byPat[u[10]]=byPat[u[10]]||[]).push(i)});
const qaCards=new Set(QA.map(q=>q[0]));
function askOn(card,unitText,q){
  $('q').value=card;$('go').click();
  const btns=[...d.querySelectorAll('[data-ask]')];const units=[...d.querySelectorAll('section.unit')];
  const k=units.findIndex(s=>s.querySelector('.utext')&&s.querySelector('.utext').textContent===unitText);if(k<0)return null;
  units[k].querySelector('[data-ask]').click();
  $('askq').value=q;$('askq').dispatchEvent(new w.Event('input'));$('askgo').click();
  const v=d.querySelector('#askres .verdict');return {lvl:v.querySelector('.lvl').textContent,big:(v.querySelector('.big')||{}).textContent||''};
}
const out={sure:[],ref:[],none:[]};
let seed=7;const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647;
const cand=QA.map((q,i)=>({q,i})).filter(x=>x.q[3]>=0&&x.q[8]>=0&&x.q[1].length<120).sort(()=>rnd()-0.5);
for(const {q,i} of cand){
  if(out.sure.length>=6&&out.ref.length>=6&&out.none.length>=6)break;
  const u=U[q[3]];const others=(byPat[u[10]]||[]).filter(j=>U[j][0]!==q[0]&&!qaCards.has(U[j][0]));
  if(!others.length)continue;const t=U[others[0]];
  const r=askOn(t[0],t[3],q[1]);if(!r)continue;
  const key=r.lvl.startsWith('확정')?'sure':r.lvl.startsWith('참고')?'ref':'none';
  if(out[key].length<6)out[key].push({askCard:t[0],effect:t[3],q:q[1],srcCard:q[0],official:q[2],engine:r.big,lvl:r.lvl});
}
fs.writeFileSync('examples.json',JSON.stringify(out,null,1));
for(const k of ['sure','ref','none'])console.log(k,out[k].length,out[k].map(x=>x.askCard+' '+x.engine+' / 공식:'+x.official.slice(0,6)).join(' | '));
