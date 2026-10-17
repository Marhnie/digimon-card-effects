/* ================= v3 UI: 1 카드·효과 → 2 질문 → 판정 → 결과 ================= */
function intro(){}
const label=no=>no+' '+cname(no);
const CARD_LIST=Object.keys(D.cards).map(no=>{const nm=cname(no);return {no,nm,ty:D.cards[no][1],kno:no.toLowerCase().replace(/[-\s]/g,''),knm:nm.replace(/\s/g,'').toLowerCase()}});
function acSearch(t){
  const k=t.toLowerCase().replace(/\s/g,'');const kno=k.replace(/-/g,'').replace(/^(bt|ex|st|rb|lm|ad)0(\d)/,'$1$2');if(!k)return [];
  const sc=[];
  for(const c of CARD_LIST){let s=-1;
    if(c.kno===kno)s=0;else if(c.kno.startsWith(kno))s=1;else if(c.knm===k)s=0.5;else if(c.knm.startsWith(k))s=2;else if(c.knm.includes(k))s=3;else if(c.kno.includes(kno))s=4;
    if(s>=0)sc.push([s,c])}
  sc.sort((a,b)=>a[0]-b[0]||(a[0]>=2&&a[0]<4?a[1].nm.length-b[1].nm.length:0)||a[1].no.localeCompare(b[1].no,undefined,{numeric:true}));
  return sc.slice(0,12).map(x=>x[1]);
}
function hlm(text,q){const k=q.replace(/\s/g,'');if(!k)return esc(text);const i=text.replace(/\s/g,'').toLowerCase().indexOf(k.toLowerCase());if(i<0)return esc(text);
  let a=-1,b=-1,n=0;for(let j=0;j<text.length;j++){if(/\s/.test(text[j]))continue;if(n===i)a=j;if(n===i+k.length-1){b=j+1;break}n++}
  return a<0||b<0?esc(text):esc(text.slice(0,a))+'<mark>'+esc(text.slice(a,b))+'</mark>'+esc(text.slice(b))}
// one reusable combobox (used for the main card search and for "카드 추가")
function combobox(input,list,onPick){
  const st={items:[],act:-1};
  const hide=()=>{list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');st.items=[];st.act=-1};
  const show=()=>{const t=input.value.trim();if(!t){hide();return}
    const q=t.split(/\s+/)[0].length>=2&&/\d/.test(t)?t.split(/\s+/)[0]:t;st.items=acSearch(q);st.act=st.items.length?0:-1;
    list.innerHTML=st.items.length?st.items.map((c,i)=>`<li role="option" id="${list.id}-${i}" data-i="${i}" aria-selected="${i===0}"><span class="cno">${hlm(c.no,q)}</span><span class="cnm">${hlm(c.nm,q)}</span><span class="cty">${esc(c.ty)}</span></li>`).join(''):'<li class="hint">일치하는 카드가 없습니다</li>';
    list.hidden=false;input.setAttribute('aria-expanded','true');if(st.items.length)input.setAttribute('aria-activedescendant',list.id+'-0')};
  const move=d=>{if(!st.items.length)return;st.act=(st.act+d+st.items.length)%st.items.length;
    list.querySelectorAll('li[role=option]').forEach((li,i)=>li.setAttribute('aria-selected',i===st.act));const el=$(list.id+'-'+st.act);if(el){el.scrollIntoView({block:'nearest'});input.setAttribute('aria-activedescendant',el.id)}};
  const pick=i=>{const c=st.items[i];if(!c)return;input.value='';hide();onPick(c.no)};
  input.addEventListener('input',show);input.addEventListener('focus',()=>{if(input.value.trim())show()});input.addEventListener('blur',()=>setTimeout(hide,150));
  input.addEventListener('keydown',e=>{const open=!list.hidden&&st.items.length;
    if(e.key==='ArrowDown'&&open){e.preventDefault();move(1)}else if(e.key==='ArrowUp'&&open){e.preventDefault();move(-1)}
    else if(e.key==='Escape')hide();else if(e.key==='Enter'){e.preventDefault();if(open&&st.act>=0)pick(st.act)}});
  list.addEventListener('mousedown',e=>{const li=e.target.closest('[data-i]');if(li){e.preventDefault();pick(+li.dataset.i)}});
}

/* ---------- state ---------- */
const ST={cards:[],pasted:null,pasteOpen:false,sel:null,q:'',it:null,itManual:false,sl:new Set(),manual:new Set(),picker:false,res:null,ai:null,busy:false,ctl:null,tab:null,adding:false};
const mainUnit=()=>ST.pasted?(ST.pasted.units[ST.sel]||null):(ST.cards[0]&&ST.sel!=null?U[ST.sel]:null);
const extras=()=>ST.cards.slice(1);
const involved=()=>ST.cards.map(c=>c.no);
function resetResult(){ST.res=null;ST.ai=null;if(ST.ctl)ST.ctl.abort();renderResult()}

/* ---------- step 1: cards ---------- */
function addCard(no){
  if(ST.cards.some(c=>c.no===no))return;
  ST.pasted=null;ST.pasteOpen=false;
  ST.cards.push({no,unit:-1});
  if(ST.cards.length===1){const us=byCard[no]||[];ST.sel=us.length===1?us[0].i:null;showCard(no)}
  ST.adding=false;resetResult();renderCards();updateGo();
}
function effRow(u,on){const tm=u.timing.length?`<span class="tm">${u.timing.map(t=>'【'+esc(t)+'】').join('')}</span>`:'';
  const body=u.timing.length?u.text.replace(/^(?:[\[{〔][^\]}〕]{1,8}[\]}〕]\s*)*(?:【[^】]+】\s*)+(?:[\[{〔][^\]}〕]{1,8}[\]}〕]\s*)*/,''):u.text;
  const tg=trigOf(u);
  return `<label class="eff${on?' on':''}"><input type="radio" name="mainEff" value="${u.i}"${on?' checked':''}><span class="et">${tm}${esc(body)}${on&&strOf(u)?`<br><span style="font-size:12px;color:var(--muted)">${esc(strLine(u))}</span>`:''}</span></label>`}
function renderCards(){
  const el=$('cardsec');
  if(ST.pasteOpen){
    el.innerHTML=`<div class="paste"><textarea id="pastebox" placeholder="카드 효과 문구를 그대로 붙여 넣으세요">${esc(ST.pasted?ST.pasted.text:'')}</textarea></div>
      ${ST.pasted&&ST.pasted.units.length?`<div class="cardbox main"><div class="cb-h"><span class="role">질문 대상</span><span class="cnm">붙여 넣은 효과</span><span class="cty">효과 ${ST.pasted.units.length}개 · 질문할 효과를 고르세요</span></div><div class="effs" role="radiogroup">${ST.pasted.units.map((u,k)=>effRow(Object.assign({},u,{i:k}),ST.sel===k)).join('')}</div></div>`:''}`;
    const pb=$('pastebox');pb.oninput=()=>{const t=pb.value.trim();ST.pasted=t?{text:pb.value,units:analyseText(t)}:null;ST.sel=ST.pasted&&ST.pasted.units.length===1?0:null;resetResult();renderCardsKeepFocus('pastebox');updateGo()};
    return;
  }
  const blocks=ST.cards.map((c,k)=>{const us=byCard[c.no]||[];const main=k===0;const ty=(D.cards[c.no]||['',''])[1];
    const head=`<div class="cb-h"><span class="role">${main?'질문 대상':'관련 카드'}</span><span class="cno">${esc(c.no)}</span><span class="cnm">${esc(cname(c.no))}</span><span class="cty">${esc(ty)}</span><span class="acts">${main?'<button class="linkbtn" type="button" data-browse="1">근거 전체 보기</button>':''}<button class="linkbtn" type="button" data-remove="${k}">빼기</button></span></div>`;
    if(!us.length)return `<div class="cardbox${main?' main':''}">${head}<div class="extra-sel">효과 텍스트가 없는 카드입니다.</div></div>`;
    if(main)return `<div class="cardbox main">${head}<div class="effs" role="radiogroup" aria-label="질문할 효과">${us.map(u=>effRow(u,ST.sel===u.i)).join('')}</div></div>`;
    return `<div class="cardbox">${head}<div class="extra-sel">관련 효과 <select data-xunit="${k}"><option value="-1">전체 효과</option>${us.map(u=>`<option value="${u.i}"${c.unit===u.i?' selected':''}>${esc(u.text.length>70?u.text.slice(0,70)+'…':u.text)}</option>`).join('')}</select></div></div>`});
  const search=`<div class="combo"><input class="field" id="cardq" placeholder="${ST.cards.length?'함께 얽힌 카드 번호나 이름':'카드 번호나 이름 (예: BT14-033, 파닥몬)'}" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="ac1" autocomplete="off" aria-label="카드 검색"><ul class="ac" id="ac1" role="listbox" hidden></ul></div>`;
  el.innerHTML=(ST.cards.length?`<div class="cards">${blocks.join('')}</div>`:'')+
    (!ST.cards.length||ST.adding?search:`<button class="addbtn" type="button" id="addcard">+ 함께 얽힌 카드 추가 <span style="color:var(--faint)">(상대 카드·조합 질문일 때)</span></button>`);
  if($('cardq')){combobox($('cardq'),$('ac1'),addCard);if(ST.adding)$('cardq').focus()}
  if($('addcard'))$('addcard').onclick=()=>{ST.adding=true;renderCards()};
}
function renderCardsKeepFocus(id){const a=document.activeElement&&document.activeElement.id===id?document.activeElement.selectionStart:null;renderCards();if(a!=null&&$(id)){$(id).focus();$(id).setSelectionRange(a,a)}}

/* ---------- step 2: question meta ---------- */
const F=D.form;
const SLOT=F.slots.map(([g,n,p],i)=>({i,g,n,re:new RegExp(p)}));
const INT=F.intents.map(([n,p])=>({n,re:p?new RegExp(p):null}));
const INT_SHOW=['가능 여부','유발·발휘 여부','대상 선택 가능','포함·해당 여부','지속·종료','횟수 제한','처리 순서','결과(어떻게 되나)','수치 결과','정의·의미','여부(그 밖)','기타'];
const INT_LABEL={'여부(그 밖)':'그 밖의 여부','기타':'기타'};
const intentOf=q=>{for(let k=0;k<INT.length;k++)if(INT[k].re&&INT[k].re.test(q))return k;return INT.length-1};
const slotsOf=q=>SLOT.filter(s=>s.re.test(q)).map(s=>s.i);
const NEGI=SLOT.findIndex(s=>s.g==='부정');
function syncMeta(){if(!ST.itManual)ST.it=intentOf(ST.q);const auto=new Set(slotsOf(ST.q));for(const s of SLOT){if(ST.manual.has(s.i))continue;if(auto.has(s.i))ST.sl.add(s.i);else ST.sl.delete(s.i)}}
function renderMeta(){
  const el=$('meta');if(!ST.q.trim()&&!ST.sl.size){el.innerHTML='<div class="mrow"><span class="k"></span><span style="color:var(--faint);font-size:13px">문장을 쓰면 묻는 것과 상황이 자동으로 정리됩니다</span></div>';return}
  const pills=[...ST.sl].sort((a,b)=>a-b).map(i=>`<span class="pill">${esc(SLOT[i].n)}<button type="button" data-unslot="${i}" aria-label="${esc(SLOT[i].n)} 빼기">×</button></span>`).join('')||'<span class="pill g">없음</span>';
  const groups=[...new Set(SLOT.map(s=>s.g))];
  el.innerHTML=`<div class="mrow"><span class="k">묻는 것</span><select class="it" id="itsel" aria-label="묻는 것">${INT_SHOW.map(n=>{const k=INT.findIndex(x=>x.n===n);return `<option value="${k}"${k===ST.it?' selected':''}>${esc(INT_LABEL[n]||n)}</option>`}).join('')}</select></div>
    <div class="mrow"><span class="k">상황</span>${pills}<button class="linkbtn" type="button" id="pickt">${ST.picker?'닫기':'고치기'}</button></div>
    ${ST.picker?`<div class="picker">${groups.map(g=>`<div class="prow"><b>${esc(g)}</b><div class="chips">${SLOT.filter(s=>s.g===g).map(s=>`<button type="button" data-slot="${s.i}" aria-pressed="${ST.sl.has(s.i)}">${esc(s.n)}</button>`).join('')}</div></div>`).join('')}<div style="font-size:12px;color:var(--muted)">선례는 묻는 것과 상황이 <b>완전히 같은</b> Q&amp;A만 씁니다.</div></div>`:''}`;
  $('itsel').onchange=e=>{ST.it=+e.target.value;ST.itManual=true;resetResult()};
  $('pickt').onclick=()=>{ST.picker=!ST.picker;renderMeta()};
}
function updateGo(){const u=mainUnit();const g=$('go');let hint='';
  if(!ST.cards.length&&!ST.pasted)hint='카드를 먼저 고르세요';else if(!u)hint='질문할 효과를 고르세요';else if(!ST.q.trim())hint='질문을 적어 주세요';
  g.disabled=!!hint||ST.busy;$('gohint').textContent=ST.busy?'판정 중…':hint}

/* ---------- engine: precedents ---------- */
const simQ=(a,b)=>{const A=bg(a),B=bg(b);let x=0;for(const g of A)if(B.has(g))x++;return x/((A.size+B.size-x)||1)};
function comboQA(){const cs=involved();if(cs.length<2)return [];
  const names=cs.map(c=>({c,nm:cname(c)})).filter(x=>x.nm.length>=2);const hits=[];
  for(const q of QA){const own=cs.includes(q.card);const m=names.filter(x=>x.c!==q.card&&(q.q.includes(x.nm)||q.q.includes(x.c)));
    if((own&&m.length)||m.length>=2)hits.push({q,s:simQ(ST.q,q.q)+m.length})}
  return hits.sort((a,b)=>b.s-a.s).slice(0,10).map(x=>x.q)}
function precedents(){
  const u=mainUnit();const key=[...ST.sl].sort((a,b)=>a-b).join(',');const myneg=ST.sl.has(NEGI)?1:0;
  const pool=QA.filter(q=>q.y>=0&&q.it===ST.it&&q.slk===key);
  const tierOf=q=>{const v=q.unit>=0?U[q.unit]:null;if(!v||u.p==null)return 2;if(v.p===u.p)return 0;if(v.types.some(t=>u.types.includes(t)))return 1;return 2};
  const combo=comboQA();
  for(let t=0;t<3;t++){const c=pool.filter(q=>tierOf(q)===t);if(!c.length)continue;
    let yes=0,no=0;const list=c.map(q=>{const w=0.05+simQ(ST.q,q.q);const y=q.y^(q.neg^myneg);if(y)yes+=w;else no+=w;return {q,w,y}}).sort((a,b)=>b.w-a.w);
    const ans=yes>=no?1:0;const unanimous=list.every(x=>x.y===ans);
    return {tier:t,ans,unanimous,list,combo,level:(t===0&&unanimous&&!extras().length)?'sure':'ref'}}
  return {tier:-1,level:'none',list:[],combo};
}
const TIERNAME=['같은 효과 패턴','같은 효과 유형','효과는 다르지만 같은 상황'];
// questions worded like this one, across all official card Q&A (the strongest signal in the accuracy test)
let QBG=null;
function similarQA(limit=15){if(!ST.q.trim())return [];
  if(!QBG)QBG=QA.map(q=>bg(q.q));const A=bg(ST.q);const u=mainUnit();const cs=involved();const myneg=ST.sl.has(NEGI)?1:0;
  const sc=[];QA.forEach((q,k)=>{const B=QBG[k];let x=0;for(const g of A)if(B.has(g))x++;let s=x/((A.size+B.size-x)||1);if(s<0.12)return;
    if(cs.includes(q.card))s+=0.12;const v=q.unit>=0?U[q.unit]:null;if(u&&v&&u.p!=null&&v.p===u.p)s+=0.08;
    sc.push({q,s,y:q.y>=0?(q.y^(q.neg^myneg)):-1})});
  return sc.sort((a,b)=>b.s-a.s).slice(0,limit)}
// issue groups (tight Q&A clusters: same thing asked, across cards); a new question joins the groups of its closest questions
const GROUP={};QA.forEach(q=>{(GROUP[q.g]=GROUP[q.g]||[]).push(q)});
function issueGroups(sim){const myneg=ST.sl.has(NEGI)?1:0;const seen=new Map();
  for(const x of sim){if(!seen.has(x.q.g))seen.set(x.q.g,{g:x.q.g,best:x.s,lead:x.q,hits:[]});seen.get(x.q.g).hits.push(x)}
  return [...seen.values()].map(G=>{const mem=GROUP[G.g]||[];const ys=mem.filter(q=>q.y>=0).map(q=>q.y^(q.neg^myneg));
    const yes=ys.filter(y=>y===1).length,no=ys.length-yes;const ans=yes>=no?1:0;
    return {...G,mem,yes,no,ans,cons:ys.length?Math.max(yes,no)/ys.length:0,cards:new Set(mem.map(q=>q.card)).size}})}
function groupVerdict(groups){const G=groups[0];if(!G||G.best<0.4||G.mem.filter(q=>q.y>=0).length<2||G.cons<1)return null;
  return {...G,acc:G.best>=0.6?'약 96%':'약 80%'}}
// effects that fire on the same trigger condition (e.g. '이 카드 · 진화원에서 · 효과로 · 파기됨'), across cards and patterns
const trigOf=u=>u&&(u.types||[]).find(t=>t.startsWith('유발 · '));
const BY_TRIG={};U.forEach(v=>{const t=trigOf(v);if(t)(BY_TRIG[t]=BY_TRIG[t]||[]).push(v)});
function triggerQA(u,limit,exceptCard){const t=trigOf(u);if(!t)return [];
  return (BY_TRIG[t]||[]).filter(v=>v.card!==exceptCard).flatMap(v=>v.qa).map(i=>({i,s:simQ(ST.q,QA[i].q)})).sort((a,b)=>b.s-a.s).slice(0,limit).map(x=>QA[x.i])}
function ownQA(){return involved().flatMap(c=>QA.filter(q=>q.card===c))}
// estimate from similar questions when there is no exact precedent: weighted vote of the closest yes/no answers
function similarEstimate(list){const yn=list.filter(x=>x.y>=0).slice(0,5);if(!yn.length)return null;
  let yes=0,no=0;yn.forEach(x=>{const w=x.s**3;if(x.y)yes+=w;else no+=w});const ans=yes>=no?1:0;
  const agree=yn.filter(x=>x.y===ans).length;return {ans,top:yn[0].s,agree,n:yn.length,strong:yn[0].s>=0.45&&agree/yn.length>=0.8}}

/* ---------- Claude ---------- */
let QIDX=null;
function buildQIdx(){const items=[];QA.forEach(q=>items.push({id:'Q'+q.i,text:'Q. '+q.q+'\nA. '+q.a,label:`카드 Q&A · ${q.card} ${cname(q.card)}`,card:q.card,bg:bg(q.q+q.a),qa:q}));
  Object.entries(D.rules).forEach(([n,t])=>items.push({id:'R'+n,text:t,label:'종합 룰 '+n,bg:bg(t)}));
  const post=new Map();items.forEach((it,k)=>{for(const g of it.bg){let a=post.get(g);if(!a)post.set(g,a=[]);a.push(k)}});
  const idf=new Map();for(const [g,a] of post)idf.set(g,Math.log(1+items.length/a.length));QIDX={items,post,idf,byId:Object.fromEntries(items.map(it=>[it.id,it]))}}
function retrieveEv(query,card,limit){if(!QIDX)buildQIdx();const sc=new Map();const N=QIDX.items.length;
  for(const g of bg(query)){const a=QIDX.post.get(g);if(!a||a.length>N*0.25)continue;const w=QIDX.idf.get(g);for(const k of a)sc.set(k,(sc.get(k)||0)+w)}
  QIDX.items.forEach((it,k)=>{if(card&&it.card===card)sc.set(k,(sc.get(k)||0)+40);if(it.id[0]==='R'&&it.text.length<25&&sc.has(k))sc.set(k,sc.get(k)*0.55)});
  return [...sc.entries()].sort((a,b)=>b[1]-a[1]).slice(0,limit).map(([k])=>QIDX.items[k])}
function patternQA(u,limit,exceptCard){if(!u||u.p==null)return [];return (byPat[u.p]||[]).filter(x=>x.card!==exceptCard).flatMap(x=>x.qa).map(i=>({i,s:simQ(ST.q,QA[i].q)})).sort((a,b)=>b.s-a.s).slice(0,limit).map(x=>QA[x.i])}
function evidenceFor(){const u=mainUnit();const card=ST.cards[0]?ST.cards[0].no:'';const out=[],seen=new Set();const add=it=>{if(it&&!seen.has(it.id)){seen.add(it.id);out.push(it)}};
  if(!QIDX)buildQIdx();
  const tagQ=(q,why)=>{const it=QIDX.byId['Q'+q.i];return it&&Object.assign({},it,{label:it.label+' · '+why})};
  (ST.res&&ST.res.list||[]).slice(0,4).forEach(x=>add(tagQ(x.q,'같은 상황 선례')));
  (ST.res&&ST.res.similar||similarQA(15)).slice(0,12).forEach(x=>add(tagQ(x.q,'비슷한 질문 '+Math.round(Math.min(1,x.s)*100)+'%')));
  (ST.res&&ST.res.groups||[]).slice(0,2).forEach((G,k)=>G.mem.slice(0,5).forEach(q=>add(tagQ(q,'같은 쟁점 그룹 '+(k+1)))));
  ownQA().slice(0,10).forEach(q=>add(tagQ(q,'고른 카드의 Q&A')));
  patternQA(u,5,card).forEach(q=>add(tagQ(q,'같은 효과 패턴')));
  triggerQA(u,5,card).forEach(q=>add(tagQ(q,'같은 유발 조건')));
  clusterQA(u,5,card).forEach(q=>add(tagQ(q,'같은 효과 무리')));
  u.rules.slice(0,6).forEach(n=>add(QIDX.byId['R'+n]));
  retrieveEv(card+' '+ST.q,card,14).filter(it=>it.id[0]==='R').slice(0,6).forEach(add);
  for(const x of extras()){const us=x.unit>=0?[U[x.unit]]:(byCard[x.no]||[]);
    retrieveEv(x.no+' '+cname(x.no)+' '+ST.q,x.no,6).forEach(add);
    us.forEach(v=>{patternQA(v,2,x.no).forEach(q=>add(QIDX.byId['Q'+q.i]));v.rules.slice(0,3).forEach(n=>add(QIDX.byId['R'+n]))})}
  (ST.res&&ST.res.combo||comboQA()).slice(0,6).forEach(q=>add(QIDX.byId['Q'+q.i]));
  return out.slice(0,extras().length?56:44)}
let sampleP=null;const getSample=()=>sampleP||(sampleP=(window.claude&&window.claude.use)?window.claude.use('sample'):Promise.resolve(null));
async function askClaude(){
  if(ST.busy)return;const u=mainUnit();if(!u)return;
  ST.busy=true;ST.ai={wait:true};renderResult();updateGo();
  const sample=await getSample();
  if(!sample){ST.busy=false;ST.ai={err:'이 화면에서는 Claude를 부를 수 없습니다. claude.ai에서 이 페이지를 열어 주세요.'};renderResult();updateGo();return}
  const ev=evidenceFor();ST.ai.ev=ev;
  const card=ST.cards[0];
  const cardText=card?(byCard[card.no]||[]).map(x=>x.text).join('\n'):ST.pasted.text;
  const prompt=`당신은 디지몬 카드게임(한국어판) 룰 판정 보조입니다. 카드의 「효과(상단 텍스트)」·「진화원 효과」·「시큐리티 효과」는 서로 다른 효과입니다(종합 룰 15-3) — 질문이 「진화원 효과에 ~를 가진 카드」처럼 어느 쪽을 가리키는지 먼저 확인하세요. 아래 상황에 대해 [자료]의 공식 Q&A와 종합 룰 Ver.4.3만 근거로 판정하세요. [자료]는 공식 카드 Q&A(같은 상황 선례 → 문구가 비슷한 질문 → 고른 카드의 Q&A → 같은 효과 패턴 순)가 먼저 오고 종합 룰 조항이 뒤에 옵니다. 상황이 같은 공식 Q&A가 있으면 그 판정을 최우선 근거로 삼아 반드시 cite하고, 카드나 조건이 달라 그대로 적용할 수 없으면 무엇이 다른지 밝히세요. 자료에 없는 룰을 지어내지 말고, 근거가 부족하면 "판단 불가"로 하고 무엇이 더 필요한지 쓰세요.
[카드] ${card?card.no+' '+cname(card.no):'(붙여 넣은 효과)'}
[카드 텍스트]
${cardText}
[질문 대상 효과] ${u.text}
[효과 구조(종합 룰 15장)] ${structText(u)}${extras().map(x=>`\n[함께 관련된 카드] ${x.no} ${cname(x.no)}\n  카드 텍스트: ${(byCard[x.no]||[]).map(v=>v.text).join(' / ')}${x.unit>=0?`\n  관련 효과: ${U[x.unit].text}`:''}`).join('')}
[묻는 것] ${INT[ST.it].n}
[상황 항목] ${[...ST.sl].map(i=>SLOT[i].g+':'+SLOT[i].n).join(', ')||'없음'}
[질문] ${ST.q}
[자료]
${ev.map(it=>`[${it.id}] (${it.label}) ${it.text}`).join('\n\n')}

JSON 하나로만 답하세요: {"verdict":"네" | "아니요" | "조건부" | "판단 불가","summary":"한두 문장 결론","reasons":[{"text":"처리 순서대로 한 단계","cite":["Q123","R4-15"]}],"caution":"판단이 갈릴 수 있는 점(없으면 빈 문자열)","conf":0.0~1.0 사이 숫자(이 판정이 공식 답과 같을 확신)}
cite에는 [자료]에 실제로 있는 ID만 쓰세요.`;
  ST.ctl=new AbortController();
  try{const r=await sample.json(prompt,{modelTier:'complex',signal:ST.ctl.signal});ST.ai={r,ev};ST.tab='ai'}
  catch(e){if(e&&e.code==='cancelled'){ST.ai=null}else{const m={not_granted:'Claude 사용이 허락되지 않았습니다.',rate_limited:'요청이 많거나 사용량 한도에 닿았습니다. 잠시 뒤 다시 시도해 주세요.',invalid_json:'답을 읽지 못했습니다. 다시 시도해 주세요.',session_expired:'다시 로그인해 주세요.',sampling_disabled:'이 계정에서는 Claude를 쓸 수 없습니다.'}[e&&e.code]||'연결이 끊겼습니다. 다시 시도해 주세요.';ST.ai={err:m,ev}}}
  finally{ST.busy=false;ST.ctl=null;renderResult();updateGo()}
}


/* ---------- v4: rulebook structure (종합 룰 15장) + effect-network cluster ---------- */
const STR=D.st||[],CLU=D.clu||[];const byClu={};U.forEach(u=>{const s=STR[u.i];if(s&&s[6]>=0)(byClu[s[6]]=byClu[s[6]]||[]).push(u)});
const strOf=u=>u?STR[u.i]:null;
const stepTxt=p=>`${p[0]||'(처리 미상)'}${p[2]?` → ${p[1]?p[1]+'의 ':''}${p[2]}`:''}${p[3]?` (${p[3]})`:''}`;
function strLine(u){const s=strOf(u);if(!s)return '';return [s[0],s[1].length?'유발 조건: '+s[1].join(' / '):'',s[4][0]?'처리: '+stepTxt(s[4][0])+(s[4].length>1?` 외 ${s[4].length-1}단계`:''):''].filter(Boolean).join(' · ')}
function structText(u){const s=strOf(u);if(!s)return '없음';const c=s[6]>=0?CLU[s[6]]:null;
  return `분류(15-8): ${s[0]} / 타이밍: ${u.timing.length?u.timing.map(x=>'【'+x+'】').join(''):'없음'} / 유발 조건(15-5): ${s[1].join(', ')||'없음'} / 처리 조건(15-6): ${s[2].join(', ')||'없음'} / 임의 처리 조건(15-7): ${s[3].join(', ')||'없음'} / 처리 단계: ${s[4].map((p,k)=>`${k+1}) ${p[4]?'임의':'강제'}${p[5]?'·'+p[5]:''}${p[6]?'·'+p[6]:''} ${stepTxt(p)}`).join(' ')||'없음'}${c?` / 같은 효과 무리: ${c[0]} (대분류 ${c[1]+1} ${c[2]})`:''}`}
function clusterQA(u,limit,exceptCard){const s=strOf(u);if(!s||s[6]<0)return [];const seen=new Set();
  return (byClu[s[6]]||[]).filter(x=>x.card!==exceptCard&&x.i!==u.i).flatMap(x=>x.qa).filter(i=>!seen.has(i)&&seen.add(i)).map(i=>({i,s:simQ(ST.q,QA[i].q)})).sort((a,b)=>b.s-a.s).slice(0,limit).map(x=>QA[x.i])}
function structHTML(u){const s=strOf(u);if(!s)return '<div class="empty">구조 정보가 없습니다.</div>';const c=s[6]>=0?CLU[s[6]]:null;
  const row=(k,ref,v)=>`<tr><th>${k}${ref?`<span class="ref">${ref}</span>`:''}</th><td>${v}</td></tr>`;const none='<span class="no">없음</span>';
  return `<table class="struct">${row('분류','15-8',esc(s[0]))}${row('타이밍·아이콘','15-14·15-16',u.timing.length?u.timing.map(x=>'【'+esc(x)+'】').join(''):none)}
    ${row('유발 조건','15-5',s[1].length?s[1].map(esc).join('<br>'):none)}${row('처리 조건','15-6',s[2].length?s[2].map(esc).join('<br>'):none)}
    ${row('임의 처리 조건','15-7',s[3].length?s[3].map(esc).join('<br>'):none)}
    ${row('처리 단계','15-1-2',s[4].length?'<ol>'+s[4].map(p=>`<li><b>${p[4]?'임의':'강제'}${p[5]?' · '+esc(p[5]):''}${p[6]?' · '+esc(p[6]):''}</b> ${esc(stepTxt(p))}</li>`).join('')+'</ol>':none)}
    ${row('구조 그룹','',esc(s[5]))}${c?row('같은 효과 무리','',`${esc(c[0])} <span class="no">· 대분류 ${c[1]+1} ${esc(c[2])} · 효과 ${c[3]}개</span>`):''}</table>`}

/* ---------- result ---------- */
const yn=a=>a?'네':'아니요';
const itemQA=(q,extra)=>`<div class="item" id="it-Q${q.i}"><div class="src"><span class="cno">${esc(q.card)}</span><span>${esc(cname(q.card))}</span>${extra||''}</div><div class="q"><b>Q</b><span>${esc(q.q)}</span></div><div class="a"><b>A</b><span>${esc(q.a)}</span></div></div>`;
const itemRule=n=>`<div class="item" id="it-R${esc(n)}"><div class="src"><span class="cno">종합 룰 ${esc(n)}</span></div><div class="tx">${esc(D.rules[n]||'')}${(()=>{const kids=RULE_KEYS.filter(k=>k.startsWith(n+'-')&&k.split('-').length===n.split('-').length+1).slice(0,4);return (D.rules[n]||'').length<40&&kids.length?'\n'+kids.map(k=>k+' '+(D.rules[k].length>120?D.rules[k].slice(0,120)+'…':D.rules[k])).join('\n'):''})()}</div></div>`;
function judge(){
  if(!mainUnit()||!ST.q.trim())return;
  ST.res=precedents();ST.res.similar=similarQA(30);ST.res.est=similarEstimate(ST.res.similar);ST.res.groups=issueGroups(ST.res.similar);ST.res.gv=groupVerdict(ST.res.groups);ST.ai=null;
  ST.tab=ST.res.list.length?'prec':(ST.res.similar.length?'sim':(ST.res.combo.length?'combo':'own'));
  renderResult();
  if(ST.res.level!=='sure'||extras().length)askClaude();
  $('result').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}
function verdictHTML(){const R=ST.res,A=ST.ai;let h='';
  if(A&&(A.r||A.wait||A.err)){
    if(A.wait)h+=`<div class="verdict v-ai"><span class="badge">Claude 판정</span><div class="why"><span class="spin"></span>근거 자료를 모아 판정하고 있습니다… 보통 30초~1분</div><div class="sub">처음 한 번은 Claude 사용 허락을 묻습니다. 이 페이지를 연 사람의 Claude 사용량을 씁니다.</div><div class="row"><button class="btn2" type="button" id="aistop">중지</button></div></div>`;
    else if(A.err)h+=`<div class="verdict v-none"><span class="badge">Claude 판정</span><div class="why">${esc(A.err)}</div><div class="row"><button class="btn2 pri" type="button" data-askai="1">다시 시도</button></div></div>`;
    else{const r=A.r||{};const byId=Object.fromEntries((A.ev||[]).map(it=>[it.id,it]));
      const cite=ids=>(ids||[]).filter(id=>byId[id]).map(id=>`<button class="cite" type="button" data-cite="${esc(id)}">${esc(id[0]==='R'?id.slice(1):(byId[id].qa?byId[id].qa.card:id))}</button>`).join('');
      const rs=(Array.isArray(r.reasons)?r.reasons:[]).map(x=>`<li>${esc(x.text||'')} ${cite(x.cite)}</li>`).join('');
      h+=`<div class="verdict v-ai"><span class="badge">Claude 판정 · 근거 ${(A.ev||[]).length}건 검토</span><div class="ans">${esc(r.verdict||'?')}</div>${(()=>{const c=Number(r.conf);if(!isFinite(c))return '';const hi=c>=0.8;return `<div class="conf ${hi?'hi':'lo'}">${hi?'확신 높음':'확신 낮음 · 심판이나 운영자 확인 권장'} <b>${Math.round(c*100)}%</b><span>${hi?'시험 200문항에서 확신 80% 이상 판정은 모두 공식 답과 같았습니다':'시험에서 확신 80% 미만 판정은 약 91%만 맞았습니다'}</span></div>`})()}<div class="why">${esc(r.summary||'')}</div>${rs?`<ol class="reasons">${rs}</ol>`:''}${r.caution?`<div class="sub">주의: ${esc(r.caution)}</div>`:''}<div class="sub">공식 판정이 아닌 근거 정리입니다. 대회에서는 저지 확인을 거쳐 주세요.</div></div>`}
  }
  if(R){
    if(R.level==='sure')h=`<div class="verdict v-sure"><span class="badge">확정 · 선례 ${R.list.length}건 일치</span><div class="ans">${yn(R.ans)}</div><div class="why">${TIERNAME[R.tier]}에서 묻는 것과 상황이 같은 공식 Q&amp;A가 모두 「${yn(R.ans)}」입니다.</div><div class="sub">Claude 없이 낸 판정 · 이 단계 과거 정확도 약 97%</div>${A?'':'<div class="row"><button class="btn2" type="button" data-askai="1">Claude로 한 번 더 확인</button></div>'}</div>`+h;
    else if(R.level==='ref'&&!(A&&A.r))h=`<div class="verdict v-ref"><span class="badge">참고 · 선례 ${R.list.length}건${R.unanimous?'':' · 답이 갈림'}</span><div class="ans">${yn(R.ans)}?</div><div class="why">${extras().length?'여러 카드가 얽힌 질문이라 선례는 참고로만 씁니다.':TIERNAME[R.tier]+'의 선례로 본 추정입니다.'}</div><div class="sub">과거 정확도 약 89~92%</div>${A?'':'<div class="row"><button class="btn2 pri" type="button" data-askai="1">Claude로 확인</button></div>'}</div>`+h;
    else if(R.level==='ref')h+=`<div class="sub" style="padding:0 4px">같은 상황 선례 추정: ${yn(R.ans)} (${TIERNAME[R.tier]} ${R.list.length}건) — 「선례」 탭에서 볼 수 있습니다.</div>`;
    else if(!(A&&A.r)&&R.gv){const G=R.gv;
      h=`<div class="verdict v-ref"><span class="badge">같은 쟁점 그룹 · Q&amp;A ${G.mem.length}건 · 카드 ${G.cards}장</span><div class="ans">${yn(G.ans)}</div><div class="why">문구가 가장 가까운 질문(유사도 ${Math.round(G.best*100)}%)이 속한 쟁점의 공식 답이 모두 「${yn(G.ans)}」입니다.</div><div class="sub">쟁점: ${esc(G.lead.q.length>90?G.lead.q.slice(0,90)+'…':G.lead.q)}</div><div class="sub">이 유사도 구간의 과거 정확도 ${G.acc} · 「쟁점별 질문」 탭에서 상황이 같은지 확인하세요.</div>${A?'':'<div class="row"><button class="btn2 pri" type="button" data-askai="1">Claude로 확인</button></div>'}</div>`+h}
    else if(!(A&&A.r)){const E=R.est;
      h=`<div class="verdict v-none"><span class="badge">같은 상황 선례 없음${E?' · 비슷한 질문 추정':''}</span>${E?`<div class="ans" style="color:var(--ink)">${yn(E.ans)}?</div><div class="why">문구가 가장 비슷한 공식 Q&amp;A ${E.n}건 중 ${E.agree}건이 「${yn(E.ans)}」 · 가장 가까운 질문 유사도 ${Math.round(E.top*100)}%</div><div class="sub">${E.strong?'비슷한 질문들의 답이 한쪽으로 모입니다(이런 경우 과거 정확도 약 87%). 「비슷한 질문」 탭에서 상황이 정말 같은지 확인하세요.':'비슷한 질문이 충분히 가깝지 않습니다(이런 경우 과거 정확도 약 65%). 참고만 하세요.'}</div>`:'<div class="why">묻는 것과 상황이 같은 공식 Q&amp;A도, 문구가 비슷한 Q&amp;A도 없습니다.</div>'}</div>`+h}
  }
  return h}
function tabsHTML(){const R=ST.res,A=ST.ai;if(!R)return '';const u=mainUnit();
  const own=ownQA();
  const tabs=[['prec','같은 상황 선례',R.list.length],['sim','쟁점별 비슷한 질문',(R.groups||[]).length],['own',involved().length>1?'고른 카드 Q&A':'이 카드 Q&A',own.length],extras().length?['combo','조합 Q&A',R.combo.length]:null,trigOf(u)?['trig','같은 유발 조건 Q&A',triggerQA(u,40,ST.cards[0]&&ST.cards[0].no).length]:null,['struct','룰북 구조',strOf(u)?strOf(u)[4].length:0],strOf(u)&&strOf(u)[6]>=0?['clu','같은 효과 무리 Q&A',clusterQA(u,40,ST.cards[0]&&ST.cards[0].no).length]:null,['rule','룰 조항',u.rules.length],['pat','같은 패턴 Q&A',patternQA(u,30,ST.cards[0]&&ST.cards[0].no).length],A&&A.ev?['ai','Claude 근거',A.ev.length]:null].filter(Boolean);
  if(!tabs.some(t=>t[0]===ST.tab))ST.tab=tabs[0][0];
  let body='';const myneg=ST.sl.has(NEGI)?1:0;
  if(ST.tab==='prec')body=R.list.length?R.list.slice(0,20).map(x=>itemQA(x.q,`<span>· ${TIERNAME[R.tier]}</span><span class="yn">답: ${yn(x.y)}</span>${x.q.neg!==myneg?'<span>(반대로 물은 질문이라 뒤집음)</span>':''}`)).join(''):'<div class="empty">묻는 것과 상황이 완전히 같은 선례가 없습니다. 상황 태그를 줄이면 찾을 수도 있습니다.</div>';
  else if(ST.tab==='sim'){const gs=(R.groups||[]).slice(0,12);const myneg=ST.sl.has(NEGI)?1:0;
    body=gs.length?gs.map((G,k)=>{const shown=G.mem.slice().sort((a,b)=>(G.hits.find(h=>h.q===b)?.s||0)-(G.hits.find(h=>h.q===a)?.s||0));
      const row=q=>itemQA(q,`${q.y>=0?`<span class="yn">답: ${yn(q.y^(q.neg^myneg))}</span>`:''}${q.y>=0&&q.neg!==myneg?'<span>(반대로 물은 질문이라 뒤집음)</span>':''}`);
      return `<div class="grp"><div class="grp-h"><b>쟁점 ${k+1}</b><span>유사도 ${Math.round(Math.min(1,G.best)*100)}%</span><span>Q&amp;A ${G.mem.length}건 · 카드 ${G.cards}장</span>${G.yes+G.no?`<span class="yn">네 ${G.yes} · 아니요 ${G.no}${G.cons===1&&G.yes+G.no>1?' · 일치':''}</span>`:''}</div>
        <div class="grp-q">${esc(G.lead.q)}</div>${shown.slice(0,3).map(row).join('')}${shown.length>3?`<details><summary>같은 쟁점 ${shown.length-3}건 더</summary>${shown.slice(3,40).map(row).join('')}</details>`:''}</div>`}).join(''):'<div class="empty">문구가 비슷한 공식 Q&amp;A가 없습니다.</div>'}
  else if(ST.tab==='own')body=own.length?own.map(q=>itemQA(q,'')).join(''):'<div class="empty">고른 카드에 등록된 Q&amp;A가 없습니다. 「같은 패턴 Q&amp;A」와 「비슷한 질문」을 보세요.</div>';
  else if(ST.tab==='trig'){const l=triggerQA(u,40,ST.cards[0]&&ST.cards[0].no);const t=trigOf(u);const n=(BY_TRIG[t]||[]).length;
    body=`<div class="empty" style="padding:0 2px">${esc(t.replace('유발 · ','유발 조건: '))} · 같은 조건으로 발동하는 효과 ${n}개</div>`+(l.length?l.map(q=>itemQA(q,'')).join(''):'<div class="empty">같은 유발 조건 효과에 연결된 Q&amp;A가 없습니다.</div>')}
  else if(ST.tab==='combo')body=R.combo.length?R.combo.map(q=>itemQA(q,'')).join(''):'<div class="empty">함께 고른 카드 이름이 같이 나오는 Q&amp;A가 없습니다.</div>';
  else if(ST.tab==='struct')body=structHTML(u);
  else if(ST.tab==='clu'){const l=clusterQA(u,40,ST.cards[0]&&ST.cards[0].no);const c=CLU[strOf(u)[6]];
    body=`<div class="empty" style="padding:0 2px">같은 효과 무리: ${esc(c[0])} · 효과 ${c[3]}개 (효과 네트워크 클러스터)</div>`+(l.length?l.map(q=>itemQA(q,'')).join(''):'<div class="empty">같은 무리 효과에 연결된 Q&amp;A가 없습니다.</div>')}
  else if(ST.tab==='rule')body=u.rules.map(itemRule).join('')||'<div class="empty">연결된 룰 조항이 없습니다.</div>';
  else if(ST.tab==='pat'){const l=patternQA(u,30,ST.cards[0]&&ST.cards[0].no);body=l.length?l.map(q=>itemQA(q,'')).join(''):'<div class="empty">같은 패턴의 다른 카드 Q&amp;A가 없습니다.</div>'}
  else if(ST.tab==='ai')body=A.ev.map(it=>it.qa?itemQA(it.qa,''):itemRule(it.id.slice(1))).join('');
  return `<div class="ev"><div class="tabs" role="tablist">${tabs.map(([k,n,c])=>`<button type="button" role="tab" data-tab="${k}" aria-selected="${ST.tab===k}">${n}<span class="n">${c}</span></button>`).join('')}</div><div class="tabp" role="tabpanel">${body}</div></div>`}
function renderResult(){$('result').innerHTML=ST.res||ST.ai?verdictHTML()+tabsHTML():''}

/* ---------- examples ---------- */
const EXQ=__EXQ__;
function loadExample(i){const x=EXQ[i];
  ST.cards=[];ST.pasted=null;ST.pasteOpen=false;ST.adding=false;addCard(x.ask_card);
  const u=(byCard[x.ask_card]||[]).find(v=>v.text===x.effect);if(u)ST.sel=u.i;
  ST.q=x.q;$('askq').value=x.q;ST.itManual=false;ST.manual=new Set();ST.sl=new Set();syncMeta();renderCards();renderMeta();updateGo();judge()}
function renderExamples(){const pick=lv=>EXQ.map((x,i)=>({x,i})).filter(o=>o.x.level===lv);
  const show=[...pick('확정').slice(0,2),...pick('참고').slice(0,1),...pick('선례 없음').slice(0,2)];
  $('exs').innerHTML='예시:'+show.map(({x,i})=>`<button type="button" data-ex="${i}"><span class="lv lv-${x.level.split(' ')[0]}">${esc(x.level)}</span>${esc(x.ask_name)}</button>`).join('')}

/* ---------- events ---------- */
$('askq').addEventListener('input',e=>{ST.q=e.target.value;syncMeta();renderMeta();updateGo();if(ST.res||ST.ai)resetResult()});
$('askq').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();if(!$('go').disabled)judge()}});
$('go').onclick=judge;
$('pastetoggle').onclick=()=>{ST.pasteOpen=!ST.pasteOpen;if(ST.pasteOpen){ST.cards=[];ST.sel=null}else{ST.pasted=null;ST.sel=null}
  $('pastetoggle').textContent=ST.pasteOpen?'카드로 고르기':'카드 대신 효과 문구로';resetResult();renderCards();updateGo();if(ST.pasteOpen)$('pastebox').focus()};
document.addEventListener('change',e=>{
  if(e.target.name==='mainEff'){ST.sel=+e.target.value;resetResult();renderCardsKeepFocus('');updateGo()}
  const xs=e.target.closest('[data-xunit]');if(xs){ST.cards[+xs.dataset.xunit].unit=+xs.value;resetResult()}
});
document.addEventListener('click',e=>{const t=e.target;
  const rm=t.closest('[data-remove]');if(rm){const k=+rm.dataset.remove;ST.cards.splice(k,1);if(k===0){ST.sel=null;const nx=ST.cards[0];if(nx){const us=byCard[nx.no]||[];ST.sel=us.length===1?us[0].i:null;showCard(nx.no)}else $('out').innerHTML=''}resetResult();renderCards();updateGo();return}
  if(t.closest('[data-browse]')){$('browse').open=true;$('browse').scrollIntoView({block:'start'});return}
  const us=t.closest('[data-unslot]');if(us){const k=+us.dataset.unslot;ST.sl.delete(k);ST.manual.add(k);renderMeta();resetResult();return}
  const sl=t.closest('[data-slot]');if(sl){const k=+sl.dataset.slot;ST.manual.add(k);if(ST.sl.has(k))ST.sl.delete(k);else ST.sl.add(k);renderMeta();resetResult();return}
  const tb=t.closest('[data-tab]');if(tb){ST.tab=tb.dataset.tab;renderResult();return}
  const ci=t.closest('[data-cite]');if(ci){ST.tab='ai';renderResult();const el=$('it-'+ci.dataset.cite);if(el){el.classList.add('flash');el.scrollIntoView({block:'center'})}return}
  if(t.closest('[data-askai]')){askClaude();return}
  if(t.id==='aistop'&&ST.ctl){ST.ctl.abort();return}
  const ex=t.closest('[data-ex]');if(ex){loadExample(+ex.dataset.ex);return}
  // legacy browse view
  const ask=t.closest('[data-ask]');if(ask){const u=ASKU[+ask.dataset.ask];if(u&&!u.pasted&&ST.cards[0]&&u.card===ST.cards[0].no){ST.sel=u.i;renderCards();updateGo();$('askq').focus();window.scrollTo(0,0)}return}
  const c=t.closest('[data-card]');if(c&&D.cards[c.dataset.card]){ST.cards=[];ST.sel=null;addCard(c.dataset.card);window.scrollTo(0,0);return}
  const p=t.closest('[data-pat]');if(p){showPattern(+p.dataset.pat);return}
  const m=t.closest('[data-more]');if(m){$(m.dataset.more).hidden=false;m.remove()}
});
renderExamples();renderCards();renderMeta();updateGo();
