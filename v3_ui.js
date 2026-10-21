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
  const EXP=window.__exProducts;const pool=QA.filter(q=>q.y>=0&&q.it===ST.it&&q.slk===key&&!(EXP&&EXP.has((q.card.match(/^([A-Z]+\d*)-/)||[])[1])));
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
  const EXP=window.__exProducts;const sc=[];QA.forEach((q,k)=>{if(EXP&&EXP.has((q.card.match(/^([A-Z]+\d*)-/)||[])[1]))return;const B=QBG[k];let x=0;for(const g of A)if(B.has(g))x++;let s=x/((A.size+B.size-x)||1);if(s<0.12)return;
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
  (ST.res&&ST.res.issues||[]).forEach(x=>{x.rules.forEach(n=>add(QIDX.byId['R'+n]));x.qa.slice(0,8).forEach(i=>add(tagQ(QA[i],'같은 룰 쟁점: '+x.name)))});
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
let sampleP=null;const getSample=async()=>{if(!sampleP)sampleP=(window.claude&&window.claude.use)?window.claude.use('sample'):Promise.resolve(null);const s=await sampleP;if(!s)sampleP=null;return s};   // never cache a null: a retry asks again
// why Claude is unavailable here, in the viewer's terms
async function whyNoClaude(){const framed=(()=>{try{return window.top!==window.self}catch(e){return true}})();
  if(!window.claude||!window.claude.use||!framed)return {msg:'이 페이지가 claude.ai 화면 밖(단독 주소·카카오톡 등 앱 안 브라우저·저장한 파일)에서 열려 있어 Claude를 부를 수 없습니다. 크롬·사파리 같은 일반 브라우저에서 claude.ai에 로그인한 뒤 claude.ai/artifact/… 주소로 열어 주세요.'};
  let st=null;try{const pm=await window.claude.use('permissions');if(pm)st=await pm.state('sample')}catch(e){}
  if(st==='denied')return {msg:'이 페이지의 Claude 사용 허락이 거절되어 있습니다. 「권한 설정 열기」에서 허용으로 바꾼 뒤 다시 시도해 주세요.',manage:true};
  return {msg:'지금 이 화면에서는 Claude를 쓸 수 없습니다. claude.ai에 로그인되어 있는지 확인해 주세요. 공개 링크로 연 경우 계정·조직 설정에 따라 Claude 호출이 막혀 있을 수 있습니다. 근거 탭의 공식 Q&A·룰 조항은 그대로 볼 수 있습니다.'}}
async function askClaude(){
  if(DIST)return;
  if(ST.busy)return;const u=mainUnit();if(!u)return;
  ST.busy=true;ST.ai={wait:true};renderResult();updateGo();
  const sample=await getSample();
  if(!sample){const w=await whyNoClaude();ST.busy=false;ST.ai={err:w.msg,manage:!!w.manage};renderResult();updateGo();return}
  const ev=evidenceFor();ST.ai.ev=ev;
  const card=ST.cards[0];
  const cardText=card?(byCard[card.no]||[]).map(x=>x.text).join('\n'):ST.pasted.text;
  const prompt=`당신은 디지몬 카드게임(한국어판) 룰 판정 보조입니다. 카드의 「효과(상단 텍스트)」·「진화원 효과」·「시큐리티 효과」는 서로 다른 효과입니다(종합 룰 15-3) — 질문이 「진화원 효과에 ~를 가진 카드」처럼 어느 쪽을 가리키는지 먼저 확인하세요. 아래 상황에 대해 [자료]의 공식 Q&A와 종합 룰 Ver.4.3만 근거로 판정하세요. [자료]는 공식 카드 Q&A(같은 상황 선례 → 문구가 비슷한 질문 → 고른 카드의 Q&A → 같은 효과 패턴 순)가 먼저 오고 종합 룰 조항이 뒤에 옵니다. 상황이 같은 공식 Q&A가 있으면 그 판정을 최우선 근거로 삼아 반드시 cite하고, 카드나 조건이 달라 그대로 적용할 수 없으면 무엇이 다른지 밝히세요. 자료에 없는 룰을 지어내지 말고, 근거가 부족하면 "판단 불가"로 하고 무엇이 더 필요한지 쓰세요.
[카드] ${card?card.no+' '+cname(card.no):'(붙여 넣은 효과)'}
[카드 텍스트]
${cardText}
[질문 대상 효과] ${u.text}${(ST.res&&ST.res.issues||[]).map(x=>`\n[이 질문의 룰 쟁점] ${x.name}: ${x.desc} (종합 룰 ${x.rules.join(', ')})`).join('')}
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


/* ---------- rule issues (룰 쟁점): rulebook points that decide a question whatever the card ---------- */
const ISS=(D.issues||[]).map(x=>({...x,re:new RegExp(x.cue),ask:new RegExp(x.ask||'.'),not:x.not?new RegExp(x.not):null}));
function detectIssues(){const q=ST.q||'';const trig=involvedUnits().some(u=>{const s=strOf(u);return s&&(s[0]==='유발형'||s[0]==='즉시형'||s[1].length)});
  return ISS.filter(x=>x.re.test(q)&&x.ask.test(q)&&!(x.not&&x.not.test(q))&&(!x.needs_trigger||trig))}
function involvedUnits(){const out=[];const u=mainUnit();if(u)out.push(u);for(const x of extras()){if(x.unit>=0)out.push(U[x.unit]);else(byCard[x.no]||[]).forEach(v=>out.push(v))}return out}
function issueVerdict(iss){if(!iss)return null;const myneg=ST.sl.has(NEGI)?1:0;const EXP=window.__exProducts;const ys=iss.qa.map(i=>QA[i]).filter(q=>!(EXP&&EXP.has((q.card.match(/^([A-Z]+\d*)-/)||[])[1]))).filter(q=>q.y>=0).map(q=>q.y^(q.neg^myneg));
  if(ys.length<3)return null;const yes=ys.filter(v=>v===1).length;if(yes!==0&&yes!==ys.length)return null;return {ans:yes?1:0,n:ys.length,iss}}


/* ---------- engine lite (E19b): Claude-free answer + calibrated confidence from page-computable signals ---------- */
const ENG=D.eng||null,RGOF=(D.rg&&D.rg.of)||{},RGG=(D.rg&&D.rg.g)||[];
const sigm=x=>1/(1+Math.exp(-x));
window.__decTest=()=>{const R=ST.res;if(!R)return null;const d=decisive();let ans=null,by=null;
  if(ST.pickQ!=null){by='official';ans=QA[ST.pickQ].y}else if(R.xref){by='explain';ans=R.xref.q.i}else if(R.level==='sure'){by='precedent';ans=R.ans}else if(R.cr){by='ruling';ans=R.cr.ans}else if(R.iv){by='issue';ans=R.iv.ans}else if(R.eng&&R.eng.sure){by='engine';ans=R.eng.ans}
  return {dec:d,by,ans}};
window.__crefTest=()=>({auto:ST.res&&ST.res.auto,cref:ST.res&&ST.res.cref?{ans:ST.res.cref.ans,qi:ST.res.cref.q.i}:null});
window.__engTest=()=>({card:ST.cards[0]&&ST.cards[0].no,eng:engineLite(similarQA(30))});   // test hook (tests/teng.js)
function engineLite(sim){if(!ENG||!sim||!sim.length)return null;const u=mainUnit();const main=ST.cards[0]?ST.cards[0].no:'';
  const top=sim.filter(x=>x.y>=0).slice(0,10);if(!top.length)return null;
  const t5=top.slice(0,5);let yes=0,no=0;t5.forEach(x=>{const w=x.s**3;if(x.y)yes+=w;else no+=w});const vote=(yes-no)/((yes+no)||1);const ans=yes>=no?1:0;
  const agree=t5.filter(x=>x.y===ans).length/t5.length;const nhi=top.filter(x=>x.s>=0.45).length;
  const myneg=ST.sl.has(NEGI)?1:0;const acc={};
  top.forEach(x=>{const g=RGOF[x.q.i];if(g==null)return;const G=RGG[g];if(!G||G[1]==null||G[3]<3||G[2]<0.9||x.s<=0.3)return;acc[g]=(acc[g]||0)+x.s*x.s});
  let rv=0,rs=0,rgBest=null;const gs=Object.keys(acc);if(gs.length){const g=gs.reduce((a,b)=>acc[a]>=acc[b]?a:b);const G=RGG[g];const gy=G[1]>=0.5?1:0;rv=(2*(gy^myneg)-1)*G[2];rs=acc[g];rgBest={name:G[0],n:G[3],cons:G[2],ans:gy^myneg}}
  const cu=u&&strOf(u)?strOf(u)[6]:-1;const cw=top.filter(x=>cu>=0&&x.q.unit>=0&&STR[x.q.unit]&&STR[x.q.unit][6]===cu);let cv=0;
  if(cw.length){let a=0,b=0,tw=0;cw.forEach(x=>{const w=x.s*x.s;tw+=w;if(x.y)a+=w;else b+=w});cv=(a-b)/(tw||1)}
  const sw=top.filter(x=>x.q.card===main);const scv=sw.length?(sw.filter(x=>x.y).length-sw.filter(x=>!x.y).length)/sw.length:0;
  const f=[vote,top[0].s,2*top[0].y-1,agree,nhi,rv,rs,cv,scv];const z=f.map((v,k)=>(v-ENG.mu[k])/ENG.sd[k]);
  const pA=sigm(z.reduce((s,v,k)=>s+v*ENG.A.w[k],ENG.A.b));const d=Math.abs(pA-0.5);const cf=[...z,d,d*z[1],d*z[3],d*z[6]];
  const conf=sigm(cf.reduce((s,v,k)=>s+v*ENG.C.w[k],ENG.C.b));
  return {ans:pA>0.5?1:0,pA,conf,sure:conf>=ENG.thr,top:top.slice(0,5),rg:rgBest,f}}


/* ---------- confirmed rulings (확인 판정): a judge confirms or corrects a verdict → shared db → reused without Claude ---------- */
const DIST=window.__DIST__===1;   // public distribution build: Claude on request, viewers send report codes
const SRV=window.__SERVER_API||null;   // E34: page served by server/app.py (this PC) — rulings/reports/search via its API
const jkey=()=>{try{return localStorage.getItem('judgeKey')||''}catch(e){return ''}};
const api=(path,opt={})=>fetch(SRV+path,{...opt,headers:{'content-type':'application/json','x-judge-key':jkey(),...(opt.headers||{})}}).then(async r=>{if(r.status===403){const e=new Error('denied');e.code='permission_denied';throw e}if(!r.ok)throw new Error(String(r.status));return r.json()});
const srvDB={collection:()=>({onSnapshot:(cb,err)=>{const pull=()=>api('rulings').then(L=>cb({docs:L.map(d=>({id:String(d.id),data:()=>d}))})).catch(e=>err&&err(e));pull();setInterval(pull,20000);return ()=>{}},
  add:d=>api('rulings',{method:'POST',body:JSON.stringify(d)})})};
const CR={list:[],db:null,me:null,state:'loading',saving:false,msg:'',done:false,canWrite:null,code:''};
window.__rulings=CR;   // test hook (tests/tcr.js)
(async()=>{try{const use=SRV?(async n=>n==='db'?srvDB:n==='user'?{id:async()=>{try{return (await api('whoami')).judge}catch(e){return null}},can:async()=>{try{return !!(await api('whoami')).judge}catch(e){return false}}}:null):(window.claude&&window.claude.use);if(!use){CR.state='off';return}
  const db=await use('db');if(!db){CR.state='off';if(ST.res)renderResult();return}
  CR.db=db;try{const user=await use('user');if(user){CR.me=await user.id();CR.canWrite=await user.can('data.write')}}catch(e){}
  renderImport();
  db.collection('rulings').onSnapshot(s=>{CR.list=s.docs.map(d=>({id:d.id,...d.data()}));{const st=document.getElementById('crstats');if(st&&st.open)renderStats()}const was=CR.state;CR.state='on';if(ST.res){const m=ST.res.level==='sure'?null:crMatch();const had=ST.res.cr;ST.res.cr=m;if(was!=='on'||!!m!==!!had)renderResult()}},
    e=>{CR.state='off';CR.msg='확인 판정을 불러오지 못했습니다.'})}catch(e){CR.state='off'}})();
const crKey=()=>extras().map(x=>x.no).sort().join(',');
// same main card + same other cards; question worded alike (2-gram Jaccard >=0.6, or >=0.45 on the same effect)
function crMatch(){const c=ST.cards[0];if(!c||!ST.q.trim()||!CR.list.length)return null;const u=mainUnit();const myneg=ST.sl.has(NEGI)?1:0;const key=crKey();
  let best=null;for(const r of CR.list){if(r.card!==c.no||(r.others||'')!==key||(r.ans!==0&&r.ans!==1))continue;
    const s=simQ(ST.q,r.q||'');const need=(u&&r.unit===u.i)?0.45:0.6;if(s<need)continue;
    if(!best||s>best.s)best={r,s,ans:r.ans^((r.neg?1:0)^myneg)}}
  return best}
function crCandidate(){const R=ST.res,A=ST.ai;if(!R||ST.pickQ!=null||R.xref)return null;
  if(A&&A.r){const v=A.r.verdict;return {ans:v==='네'?1:v==='아니요'?0:null,src:'claude',summary:String(A.r.summary||'')}}
  if(A&&(A.wait||A.err))return null;
  if(R.cr||R.level==='sure')return null;
  if(R.iv)return {ans:R.iv.ans,src:'issue',summary:R.iv.iss.name};
  if(R.cref)return {ans:R.cref.ans,src:'combo',summary:'Q'+R.cref.q.i};
  if(R.eng&&R.eng.sure)return {ans:R.eng.ans,src:'engine',summary:''};
  if(R.level==='ref')return {ans:R.ans,src:'precedent',summary:''};
  if(R.gv)return {ans:R.gv.ans,src:'group',summary:''};
  if(R.est)return {ans:R.est.ans,src:'estimate',summary:''};
  return {ans:null,src:'none',summary:''}}
const SRCN={combo:'관련 카드 공식 Q&A',report:'이용자 제보',claude:'Claude 판정',issue:'룰 쟁점',engine:'엔진 판정',precedent:'선례 참고',group:'쟁점 그룹',estimate:'비슷한 질문 추정',none:'직접 판정'};
function crPanel(){const c=crCandidate();if(!c||!ST.cards[0])return '';
  if(CR.state==='loading')return '';
  if(CR.state!=='on'||CR.canWrite===false)return reportPanel(c);
  if(CR.done)return `<div class="crbar ok"><b>저장했습니다.</b> 같은 카드·비슷한 질문이 다시 오면 Claude 없이 이 판정으로 답합니다.</div>`;
  const b=(a,l,cls)=>`<button class="btn2${cls?' '+cls:''}" type="button" data-crsave="${a}"${CR.saving?' disabled':''}>${l}</button>`;
  return `<div class="crbar"><div class="crq"><b>판정 확인</b> ${c.ans==null?'이 질문의 정답을 알고 있다면 저장해 주세요.':`위 ${esc(SRCN[c.src])} 「${yn(c.ans)}」가 맞나요?`} 확인한 판정은 저장되어, 같은 질문이 다시 오면 Claude 없이 바로 답합니다.</div>
    <div class="row">${c.ans==null?b(1,'정답은 네','pri')+b(0,'정답은 아니요','pri'):b(c.ans,'맞음 · 저장','pri')+b(1-c.ans,`틀림 · 「${yn(1-c.ans)}」로 저장`)}<input id="crnote" type="text" maxlength="300" placeholder="메모(선택): 근거·상황" aria-label="확인 판정 메모"></div>${CR.msg?`<div class="sub">${esc(CR.msg)}</div>`:''}</div>`}

// viewers without write access: build a report code (JD1:base64 JSON) to send to an operator, who imports it
const b64e=s=>{const b=new TextEncoder().encode(s);let x='';for(let i=0;i<b.length;i+=8192)x+=String.fromCharCode.apply(null,b.subarray(i,i+8192));return btoa(x)};
const b64d=s=>new TextDecoder().decode(Uint8Array.from(atob(s),ch=>ch.charCodeAt(0)));
function crDoc(ans,c,note){const u=mainUnit();return {card:ST.cards[0].no,others:crKey(),unit:u?u.i:-1,q:ST.q.slice(0,1000),neg:ST.sl.has(NEGI)?1:0,it:ST.it,slots:[...ST.sl].sort((a,b)=>a-b),
  ans,src:c.src,agreed:c.ans==null?null:(c.ans===ans),summary:(c.summary||'').slice(0,500),note:(note||'').slice(0,300),by:CR.me||'',at:new Date().toISOString()}}
function reportPanel(c){
  if(CR.code&&SRV)return `<div class="crbar ok"><b>${esc(CR.msg||'보냈습니다.')}</b></div>`;
  if(CR.code)return `<div class="crbar ok"><b>코드를 만들었습니다.</b> 아래 코드를 복사해 운영자(심판)에게 보내 주세요. 운영자가 확인하면 같은 질문에 Claude 없이 바로 답하게 됩니다.<textarea class="crcode" readonly rows="3" aria-label="보낼 코드">${esc(CR.code)}</textarea><div class="row"><button class="btn2 pri" type="button" data-crcopy="1">코드 복사</button></div>${CR.msg?`<div class="sub">${esc(CR.msg)}</div>`:''}</div>`;
  const b=(a,l,cls)=>`<button class="btn2${cls?' '+cls:''}" type="button" data-crrep="${a}">${l}</button>`;
  return `<div class="crbar"><div class="crq"><b>정답을 알고 계신가요?</b> ${c.ans==null?'':`위 판정은 「${yn(c.ans)}」입니다. `}맞는지 틀리는지 알려 주시면 운영자가 확인해 판정으로 쌓습니다.</div>
    <div class="row">${c.ans==null?b(1,'정답은 네','pri')+b(0,'정답은 아니요','pri'):b(c.ans,'맞아요','pri')+b(1-c.ans,`틀려요 · 정답은 「${yn(1-c.ans)}」`)}<input id="crnote" type="text" maxlength="300" placeholder="근거(선택): 공식 Q&A·대회 판정 등" aria-label="근거 메모"></div></div>`}
function crReport(ans){const c=crCandidate();if(!c||!ST.cards[0])return;const note=(document.getElementById('crnote')||{}).value||'';
  if(SRV){api('reports',{method:'POST',body:JSON.stringify(crDoc(ans,c,note))}).then(()=>{CR.code=' ';CR.msg='보냈습니다. 심판이 확인하면 판정으로 쌓입니다.';renderResult()}).catch(()=>{CR.msg='보내지 못했습니다. 잠시 뒤 다시 시도해 주세요.';renderResult()});return}
  CR.code='JD1:'+b64e(JSON.stringify(crDoc(ans,c,note)));CR.msg='';renderResult()}
// operators: paste report codes → saved as confirmed rulings
function judgeBox(){if(!SRV||document.getElementById('jbox'))return;const el=document.createElement('details');el.id='jbox';el.className='browse';
  el.innerHTML=`<summary>심판 로그인</summary><div class="crbar"><div class="sub">운영자가 준 심판 키를 넣으면 판정 확인·저장과 제보 검토를 할 수 있습니다(이 브라우저에만 저장).</div><div class="row"><input id="jkey" type="password" aria-label="심판 키" placeholder="심판 키"><button class="btn2 pri" type="button" id="jkeyset">확인</button><button class="btn2" type="button" id="jkeyout">로그아웃</button></div><div class="sub" id="jkeymsg"></div></div>`;
  const anchor=document.getElementById('browse');anchor.parentNode.insertBefore(el,anchor)}
if(SRV)setTimeout(judgeBox,0);
// artifact build: the claude.ai sandbox cannot call the server, so link to it (E35) — the GitHub Pages page forwards to its current address
if(DIST&&!SRV&&window.__SERVER_LINK)setTimeout(()=>{const ex=document.getElementById('exs');if(!ex||document.getElementById('srvlink'))return;const d=document.createElement('div');d.id='srvlink';d.className='crbar';
  d.innerHTML=`<b>말투가 달라도 비슷한 공식 Q&amp;A를 찾아 주는 「의미 검색」</b>과 심판 확인·제보 기능은 서버판에서 쓸 수 있습니다. <a href="${window.__SERVER_LINK}" target="_blank" rel="noopener">서버판 열기 →</a>`;ex.parentNode.insertBefore(d,ex)},0);
function renderImport(){if(!CR.db||CR.canWrite===false)return;if(document.getElementById('crimport'))return;
  const el=document.createElement('details');el.id='crimport';el.className='browse';
  el.innerHTML=`<summary>받은 판정 코드 가져오기 (운영자)</summary><div class="crbar"><div class="sub">이용자가 보낸 「JD1:」 코드를 한 줄에 하나씩 붙여 넣고 내용을 확인한 뒤 저장하세요. 저장한 판정은 같은 질문에 Claude 없이 답하는 데 쓰입니다.</div><textarea id="crin" rows="4" aria-label="받은 코드"></textarea><div class="row">${SRV?'<button class="btn2" type="button" id="crpull">받은 제보 불러오기</button>':''}<button class="btn2" type="button" id="crpreview">내용 보기</button><button class="btn2 pri" type="button" id="crimp" disabled>확인 판정으로 저장</button></div><div id="crprev"></div></div>`;
  const anchor=document.getElementById('browse');anchor.parentNode.insertBefore(el,anchor);
  const st=document.createElement('details');st.id='crstats';st.className='browse';st.innerHTML='<summary>판정 현황 (운영자)</summary><div id="crstatsb"></div>';
  anchor.parentNode.insertBefore(st,anchor);st.addEventListener('toggle',()=>{if(st.open)renderStats()})}
// how many confirmed rulings came from which first verdict, and how often that first verdict was right
function renderStats(){const el=document.getElementById('crstatsb');if(!el)return;const L=CR.list;
  if(!L.length){el.innerHTML='<div class="crbar"><div class="sub">아직 저장된 확인 판정이 없습니다.</div></div>';return}
  const by={};L.forEach(r=>{const k=r.src||'none';const b=by[k]=by[k]||{n:0,ok:0,bad:0};b.n++;if(r.agreed===true)b.ok++;else if(r.agreed===false)b.bad++});
  const rows=Object.entries(by).sort((a,b)=>b[1].n-a[1].n).map(([k,b])=>`<tr><td>${esc(SRCN[k]||k)}</td><td>${b.n}</td><td>${b.ok+b.bad?Math.round(b.ok/(b.ok+b.bad)*100)+'% ('+b.ok+'/'+(b.ok+b.bad)+')':'—'}</td></tr>`).join('');
  const cards=new Set(L.map(r=>r.card)).size;const recent=L.slice().sort((a,b)=>String(b.at).localeCompare(String(a.at))).slice(0,15);
  el.innerHTML=`<div class="crbar"><div class="sub">확인 판정 ${L.length}건 · 카드 ${cards}장. 「처음 판정 정확도」는 심판이 확인했을 때 처음 판정(엔진·룰 쟁점 등)이 맞았던 비율입니다.</div>
    <table class="struct"><tr><th>처음 판정</th><th>건수</th><th>처음 판정 정확도</th></tr>${rows}</table>
    <div class="sub" style="margin-top:8px">최근 확인 판정</div>${recent.map(r=>`<div class="item"><div class="src"><span class="cno">${esc(r.card)}</span><span>${esc(cname(r.card))}</span><span class="yn">답: ${yn(r.ans)}</span><span>· ${esc(SRCN[r.src]||'')}${r.agreed===false?' → 바로잡음':''}</span><span>${esc(String(r.at||'').slice(0,10))}</span></div><div class="q"><b>Q</b><span>${esc(r.q||'')}</span></div>${r.note?`<div class="a"><b>메모</b><span>${esc(r.note)}</span></div>`:''}</div>`).join('')}</div>`}
let CRIN=[],CRREP=[];
function parseCodes(txt){const out=[],bad=[];for(const line of txt.split(/\s+/).filter(Boolean)){try{if(!line.startsWith('JD1:'))throw 0;const d=JSON.parse(b64d(line.slice(4)));
  if(typeof d.card!=='string'||typeof d.q!=='string'||(d.ans!==0&&d.ans!==1))throw 0;
  out.push({card:d.card.slice(0,20),others:String(d.others||'').slice(0,200),unit:Number.isInteger(d.unit)?d.unit:-1,q:d.q.slice(0,1000),neg:d.neg?1:0,it:d.it==null?null:d.it,slots:Array.isArray(d.slots)?d.slots.filter(Number.isInteger).slice(0,30):[],
    ans:d.ans,src:'report',agreed:typeof d.agreed==='boolean'?d.agreed:null,summary:String(d.summary||'').slice(0,500),note:String(d.note||'').slice(0,300),reporter:String(d.by||'').slice(0,80),reported_at:String(d.at||'').slice(0,40),by:CR.me||'',at:new Date().toISOString()})}catch(e){bad.push(line.slice(0,24))}}
  return {out,bad}}
async function crSave(ans){const c=crCandidate();const u=mainUnit();if(!CR.db||!c||!ST.cards[0]||CR.saving)return;
  const note=(document.getElementById('crnote')||{}).value||'';
  CR.saving=true;CR.msg='';renderResult();
  const doc={card:ST.cards[0].no,others:crKey(),unit:u?u.i:-1,q:ST.q.slice(0,1000),neg:ST.sl.has(NEGI)?1:0,it:ST.it,slots:[...ST.sl].sort((a,b)=>a-b),
    ans,src:c.src,agreed:c.ans==null?null:(c.ans===ans),summary:c.summary.slice(0,500),note:note.slice(0,300),by:CR.me||'',at:new Date().toISOString()};
  try{await CR.db.collection('rulings').add(doc);CR.done=true}
  catch(e){if(e&&e.code==='permission_denied'){CR.canWrite=false;CR.msg='저장 권한이 없어 운영자에게 보낼 코드로 바꿨습니다.'}else CR.msg='저장하지 못했습니다. 잠시 뒤 다시 시도해 주세요.'}
  finally{CR.saving=false;renderResult()}}


/* ---------- cards named in the question text + the other card's own official Q&A (E24) ---------- */
const nrm=s=>String(s||'').replace(/[\s:：・·\-–—「」『』()（）\[\].,!?~]/g,'');
const QACNT={};QA.forEach(q=>{QACNT[q.card]=(QACNT[q.card]||0)+1});
const NAMEIDX=(()=>{const m={};for(const no of Object.keys(D.cards)){const k=nrm(cname(no));if(k.length<3)continue;(m[k]=m[k]||[]).push(no)}
  return Object.entries(m).map(([k,nos])=>({k,no:nos.slice().sort((a,b)=>(QACNT[b]||0)-(QACNT[a]||0))[0]})).sort((a,b)=>b.k.length-a.k.length)})();
function qCards(){const q=nrm(ST.q);if(!q)return [];const main=ST.cards[0]?nrm(cname(ST.cards[0].no)):'';const have=new Set(ST.cards.map(c=>nrm(cname(c.no))));
  const used=new Array(q.length).fill(false);const out=[];
  for(const e of NAMEIDX){const skip=e.k===main||have.has(e.k);if(!skip&&main.includes(e.k))continue;let i=q.indexOf(e.k);
    while(i>=0){let free=true;for(let j=i;j<i+e.k.length;j++)if(used[j]){free=false;break}
      if(free){for(let j=i;j<i+e.k.length;j++)used[j]=true;if(!skip){out.push(e.no);break}}i=q.indexOf(e.k,i+1)}}
  return out}
// the other card's official Q&A that asks about the timing the main effect has (e.g. 【등장 시】) — strongest single hint for combo questions
function comboRef(){const u=mainUnit();const xs=extras();if(!u||!xs.length)return null;const myneg=ST.sl.has(NEGI)?1:0;
  const tms=(u.timing||[]).map(x=>'【'+x+'】');const mn=ST.cards[0]?cname(ST.cards[0].no):'';let best=null;
  const EXP=window.__exProducts;
  for(const x of xs)for(const q of QA){if(q.card!==x.no||q.y<0)continue;if(EXP&&EXP.has((q.card.match(/^([A-Z]+\d*)-/)||[])[1]))continue;
    const tm=tms.some(t=>q.q.includes(t)&&!q.q.includes('이 카드의 '+t));const nm=mn&&q.q.includes(mn);if(!tm&&!nm)continue;
    const s=simQ(ST.q,q.q)+(tm?0.25:0)+(nm?0.3:0);if(!best||s>best.s)best={q,s,ans:q.y^(q.neg^myneg),via:x.no}}
  return best&&best.s>=0.27?best:null}


/* ---------- semantic search (E33): distilled student, files under window.__QEMB_BASE (absent → feature off) ---------- */
const SEM_ON=!!SRV||(typeof QEMB!=='undefined'&&!!window.__QEMB_BASE);const SEMC=new Map();
if(SEM_ON&&!SRV)QEMB.init(n=>fetch(window.__QEMB_BASE+n).then(r=>{if(!r.ok)throw new Error(n+' '+r.status);return r.arrayBuffer()})).then(ok=>{if(ok){if(ST.res)renderResult();renderSugg()}});
function semQA(text,k){const EXP=window.__exProducts;const key=String(text||'').trim();if(!SEM_ON||!key)return [];
  if(SRV){const c=SEMC.get(key);if(c)return c.slice(0,k);if(!SEMC.has('#'+key)){SEMC.set('#'+key,1);
      api('search',{method:'POST',body:JSON.stringify({q:key,k:Math.max(k,10)})}).then(j=>{SEMC.set(key,(j.hits||[]).filter(h=>QA[h.i]&&!(EXP&&EXP.has((QA[h.i].card.match(/^([A-Z]+\d*)-/)||[])[1]))).map(h=>({q:QA[h.i],s:h.cos!=null?h.cos:h.s})));
        renderSugg();if(ST.res&&ST.q.trim()===key)renderResult()}).catch(()=>{})}
    return []}
  if(!QEMB.st.ready)return [];
  return QEMB.search(text,k,i=>QA[i]&&!(EXP&&EXP.has((QA[i].card.match(/^([A-Z]+\d*)-/)||[])[1]))).map(x=>({q:QA[x.i],s:x.s}))}
/* ---------- question autocomplete (E25): official question wording for this card / same effect pattern ---------- */
let SUGG=[],SUGI=-1;
function suggestions(limit=8){const u=mainUnit();const c=ST.cards[0];if(!u||!c)return [];const typed=ST.q.trim();
  const own=QA.filter(q=>q.card===c.no&&(q.unit===u.i||q.unit<0||U[q.unit]&&U[q.unit].card===c.no));
  const pat=u.p==null?[]:QA.filter(q=>q.card!==c.no&&q.unit>=0&&U[q.unit]&&U[q.unit].p===u.p&&q.y>=0);
  const sc=q=>typed?simQ(typed,q.q):0;
  const ownR=own.map(q=>({q,s:sc(q)+0.15,src:'이 카드 공식 질문'}));
  // same effect pattern: one representative per (asked, situation) template, the most frequent templates first
  const by=new Map();for(const q of pat){const k=intentOf(q.q)+'|'+slotsOf(q.q).sort((a,b)=>a-b).join(',');const g=by.get(k)||{n:0,best:null,bs:-1};g.n++;const s=sc(q);if(s>g.bs){g.bs=s;g.best=q}by.set(k,g)}
  const patR=[...by.values()].map(g=>({q:g.best,s:g.bs+Math.min(0.1,g.n*0.01),n:g.n,src:'같은 효과 패턴 질문'}));
  const all=[...ownR,...patR].filter(x=>!typed||x.s>=0.08||x.src==='이 카드 공식 질문').sort((a,b)=>b.s-a.s).slice(0,limit);
  // meaning-alike official questions (any card) — catches colloquial wording the character overlap misses
  if(typed.length>=4){const seen=new Set(all.map(x=>x.q.i));for(const x of semQA(typed,8)){if(seen.has(x.q.i))continue;seen.add(x.q.i);all.push({q:x.q,s:x.s,src:'의미가 비슷한 공식 질문'});if(all.length>=limit+3)break}}
  return all}
function renderSugg(){const el=document.getElementById('sugg');if(!el)return;SUGG=(document.activeElement===$('askq')||ST.suggOpen)?suggestions():[];
  if(!SUGG.length){el.innerHTML='';el.hidden=true;return}el.hidden=false;
  el.innerHTML=`<div class="sugg-h">비슷한 공식 질문 문장으로 고르면 Claude 없이 더 정확하게 답합니다 · ↑↓ Enter</div>`+SUGG.map((x,k)=>`<button type="button" class="sg${k===SUGI?' on':''}" role="option" aria-selected="${k===SUGI}" data-sg="${k}"><span class="sg-src">${esc(x.src)}${x.q.card!==(ST.cards[0]||{}).no?` · ${esc(x.q.card)}`:''}${x.n>1?` · 같은 틀 ${x.n}건`:''}</span>${esc(x.q.q)}</button>`).join('')}
function pickSugg(k){const x=SUGG[k];if(!x)return;const q=x.q;
  // keep the official wording; another card's question keeps its template (asked + situation) even if the user edits names
  ST.q=q.q;$('askq').value=q.q;ST.it=intentOf(q.q);ST.itManual=true;ST.sl=new Set(slotsOf(q.q));ST.manual=new Set(SLOT.map(s=>s.i));ST.pickQ=q.card===(ST.cards[0]||{}).no?q.i:null;
  ST.suggOpen=false;SUGI=-1;renderSugg();renderMeta();updateGo();judge()}


/* ---------- explanation questions (E26): reuse the official answer of the same question asked about another card ---------- */
const YN_INT=new Set(['가능 여부','유발·발휘 여부','대상 선택 가능','포함·해당 여부','지속·종료','횟수 제한','여부(그 밖)']);
const qTerms=s=>new Set((String(s).match(/「[^「」]{2,40}」/g)||[]));
const SPECIFIC=/이 (?:카드|테이머|디지몬|옵션)/;
let EXQB=null;
function explainRef(){if(!ST.q.trim())return null;const nm=INT[ST.it]&&INT[ST.it].n;if(YN_INT.has(nm))return null;
  if(!EXQB)EXQB=QA.map(q=>q.y<0&&q.card?bg(q.q):null);const A=bg(ST.q);const mt=qTerms(ST.q);const spec=SPECIFIC.test(ST.q);
  const EXP=window.__exProducts;let best=null;
  QA.forEach((q,k)=>{const B=EXQB[k];if(!B)return;if(EXP&&EXP.has((q.card.match(/^([A-Z]+\d*)-/)||[])[1]))return;
    let x=0;for(const g of A)if(B.has(g))x++;let s=x/((A.size+B.size-x)||1);if(s<0.45)return;
    const shared=[...qTerms(q.q)].some(t=>mt.has(t));if(q.it!==ST.it)s-=0.1;if(shared)s+=0.1;
    // a question about "this card" only carries over when it names the same quoted term (otherwise the answer is card-specific)
    if(spec&&!shared&&!(ST.cards[0]&&q.card===ST.cards[0].no))return;
    if(!best||s>best.s)best={q,s}});
  return best&&best.s>=0.6?best:null}
// card-specific "what does this effect do": a deterministic restatement from the rulebook-structure decomposition
function structExplain(){const u=mainUnit();if(!u||!/어떤 효과|무슨 효과|어떻게 (?:처리|발휘)/.test(ST.q))return null;const s=strOf(u);if(!s)return null;
  const parts=[];parts.push(`분류: ${s[0]}`);if(u.timing&&u.timing.length)parts.push(`타이밍: ${u.timing.map(x=>'【'+x+'】').join('')}`);
  if(s[1].length)parts.push(`유발 조건: ${s[1].join(' / ')}`);if(s[2].length)parts.push(`처리 조건: ${s[2].join(' / ')}`);if(s[3].length)parts.push(`임의 처리 조건: ${s[3].join(' / ')}`);
  return {parts,steps:s[4].map(p=>`${p[4]?'(임의) ':''}${stepTxt(p)}`),text:u.text}}

/* ---------- result ---------- */
const yn=a=>a?'네':'아니요';
const itemQA=(q,extra)=>`<div class="item" id="it-Q${q.i}"><div class="src"><span class="cno">${esc(q.card)}</span><span>${esc(cname(q.card))}</span>${extra||''}</div><div class="q"><b>Q</b><span>${esc(q.q)}</span></div><div class="a"><b>A</b><span>${esc(q.a)}</span></div></div>`;
const itemRule=n=>`<div class="item" id="it-R${esc(n)}"><div class="src"><span class="cno">종합 룰 ${esc(n)}</span></div><div class="tx">${esc(D.rules[n]||'')}${(()=>{const kids=RULE_KEYS.filter(k=>k.startsWith(n+'-')&&k.split('-').length===n.split('-').length+1).slice(0,4);return (D.rules[n]||'').length<40&&kids.length?'\n'+kids.map(k=>k+' '+(D.rules[k].length>120?D.rules[k].slice(0,120)+'…':D.rules[k])).join('\n'):''})()}</div></div>`;
function judge(){
  if(!mainUnit()||!ST.q.trim())return;
  CR.done=false;CR.msg='';CR.code='';ST.xref=null;ST.sx=null;if(ST.pickQ!=null&&QA[ST.pickQ]&&QA[ST.pickQ].q!==ST.q)ST.pickQ=null;ST.cards=ST.cards.filter(c=>!c.auto);const auto=qCards();auto.forEach(no=>ST.cards.push({no,unit:-1,auto:true}));if(auto.length)renderCards();ST.res=precedents();ST.res.auto=auto;ST.res.cref=comboRef();ST.res.xref=explainRef();ST.res.sx=ST.res.xref?null:structExplain();ST.res.cr=ST.res.level==='sure'?null:crMatch();ST.res.issues=detectIssues();ST.res.iv=ST.res.level==='sure'?null:issueVerdict(ST.res.issues[0]);ST.res.similar=similarQA(30);ST.res.est=similarEstimate(ST.res.similar);ST.res.eng=(ST.res.level==='sure'||ST.res.iv||extras().length)?null:engineLite(ST.res.similar);ST.res.groups=issueGroups(ST.res.similar);ST.res.gv=groupVerdict(ST.res.groups);ST.ai=null;
  ST.tab=ST.res.iv?'issue':ST.res.list.length?'prec':(ST.res.similar.length?'sim':(ST.res.combo.length?'combo':'own'));
  renderResult();
  if(!DIST&&(ST.res.level==='none'||extras().length)&&!ST.res.cr&&!ST.res.iv&&!ST.res.xref&&!(ST.res.eng&&ST.res.eng.sure))askClaude();
  $('result').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}
function autoNote(){const a=ST.res&&ST.res.auto||[];return a.length?`<div class="sub" style="padding:0 4px 8px">질문에서 ${a.map(no=>`「${esc(cname(no))}」(${esc(no)})`).join(', ')}를 찾아 함께 판단했습니다. 다른 카드라면 1단계에서 빼거나 바꿔 주세요.</div>`:''}
function verdictHTML(){const R=ST.res,A=ST.ai;let h='';
  if(A&&(A.r||A.wait||A.err)){
    if(A.wait)h+=`<div class="verdict v-ai"><span class="badge">Claude 판정</span><div class="why"><span class="spin"></span>근거 자료를 모아 판정하고 있습니다… 보통 30초~1분</div><div class="sub">처음 한 번은 Claude 사용 허락을 묻습니다. 이 페이지를 연 사람의 Claude 사용량을 씁니다.</div><div class="row"><button class="btn2" type="button" id="aistop">중지</button></div></div>`;
    else if(A.err)h+=`<div class="verdict v-none"><span class="badge">Claude 판정</span><div class="why">${esc(A.err)}</div><div class="row"><button class="btn2 pri" type="button" data-askai="1">다시 시도</button>${A.manage?'<button class="btn2" type="button" id="pmmanage">권한 설정 열기</button>':''}</div></div>`;
    else{const r=A.r||{};const byId=Object.fromEntries((A.ev||[]).map(it=>[it.id,it]));
      const cite=ids=>(ids||[]).filter(id=>byId[id]).map(id=>`<button class="cite" type="button" data-cite="${esc(id)}">${esc(id[0]==='R'?id.slice(1):(byId[id].qa?byId[id].qa.card:id))}</button>`).join('');
      const rs=(Array.isArray(r.reasons)?r.reasons:[]).map(x=>`<li>${esc(x.text||'')} ${cite(x.cite)}</li>`).join('');
      h+=`<div class="verdict v-ai"><span class="badge">Claude 판정 · 근거 ${(A.ev||[]).length}건 검토</span><div class="ans">${esc(r.verdict||'?')}</div>${(()=>{const c=Number(r.conf);if(!isFinite(c))return '';const hi=c>=0.8;return `<div class="conf ${hi?'hi':'lo'}">${hi?'확신 높음':'확신 낮음 · 심판이나 운영자 확인 권장'} <b>${Math.round(c*100)}%</b><span>${hi?'시험 200문항에서 확신 80% 이상 판정은 모두 공식 답과 같았습니다':'시험에서 확신 80% 미만 판정은 약 91%만 맞았습니다'}</span></div>`})()}<div class="why">${esc(r.summary||'')}</div>${rs?`<ol class="reasons">${rs}</ol>`:''}${r.caution?`<div class="sub">주의: ${esc(r.caution)}</div>`:''}<div class="sub">공식 판정이 아닌 근거 정리입니다. 대회에서는 저지 확인을 거쳐 주세요.</div></div>`}
  }
  if(R&&ST.pickQ!=null&&!(A&&A.r)){const q=QA[ST.pickQ];
    h=`<div class="verdict v-sure"><span class="badge">공식 Q&amp;A · ${esc(q.card)} ${esc(cname(q.card))}</span><div class="ans">${q.y>=0?yn(q.y):'공식 답'}</div><div class="why">${esc(q.a)}</div><div class="sub">고른 질문이 이 카드의 공식 Q&amp;A와 같습니다.</div></div>`;return h}
  if(R&&R.xref&&!(A&&A.r)){const X=R.xref,q=X.q;
    h=`<div class="verdict v-sure"><span class="badge">공식 답변 · 같은 질문 · ${esc(q.card)} ${esc(cname(q.card))}</span><div class="why" style="font-size:16px;color:var(--ink)">${esc(q.a)}</div><div class="sub">거의 같은 질문(문구 유사도 ${Math.round(Math.min(1,X.s)*100)}%)에 대한 공식 답변입니다: ${esc(q.q)}</div></div>`;return h}
  if(R&&R.sx&&!(A&&A.r)&&!R.cr){const S=R.sx;
    h=`<div class="verdict v-ref"><span class="badge">효과 구조 설명 · 카드 텍스트에서 자동 정리</span><div class="why">${S.parts.map(esc).join('<br>')}${S.steps.length?'<br>처리 순서:<ol style="margin:4px 0 0 18px;padding:0">'+S.steps.map(x=>`<li>${esc(x)}</li>`).join('')+'</ol>':''}</div><div class="sub">카드 텍스트를 종합 룰 15장 구조로 나눈 것입니다(판정이 아니라 정리). 원문: ${esc(S.text)}</div></div>`}
  if(R&&R.cr&&!(A&&A.r)){const M=R.cr,r=M.r;const d=String(r.at||'').slice(0,10);
    h=`<div class="verdict v-sure"><span class="badge">확인된 판정 · Claude 없이 · 질문 유사도 ${Math.round(M.s*100)}%</span><div class="ans">${yn(M.ans)}</div><div class="why">같은 카드에 대해 사람이 확인한 판정입니다${r.src&&SRCN[r.src]?` (처음 판정: ${esc(SRCN[r.src])}${r.agreed===false?' → 확인 때 바로잡음':''})`:''}.</div><div class="sub">확인한 질문: ${esc(r.q||'')}${r.note?`<br>메모: ${esc(r.note)}`:''}${d?` · ${esc(d)}`:''}${(r.neg?1:0)!==(ST.sl.has(NEGI)?1:0)?' · 반대로 물은 질문이라 뒤집음':''}</div><div class="row"><button class="btn2" type="button" data-askai="1">Claude에게도 묻기</button></div></div>`;return h}
  if(R&&R.iv&&!(A&&A.r)){const V=R.iv;
    h=`<div class="verdict v-sure"><span class="badge">룰 쟁점 · ${esc(V.iss.name)} · 공식 Q&amp;A ${V.n}건 일치</span><div class="ans">${yn(V.ans)}</div><div class="why">${esc(V.iss.desc)}</div><div class="sub">근거 룰 ${V.iss.rules.map(esc).join(' · ')} · 같은 쟁점의 공식 Q&amp;A가 모두 「${yn(V.ans)}」입니다. 상황이 쟁점과 다르면(예: 그 카드가 실제로는 자리를 벗어나지 않음) 결론이 바뀝니다.</div><div class="row"><button class="btn2" type="button" data-askai="1">Claude에게도 묻기</button></div></div>`;return h}
  if(R&&R.cref&&!(A&&A.r)){const C=R.cref;
    h=`<div class="verdict v-ref"><span class="badge">참고 · 함께 관련된 카드의 공식 Q&amp;A · ${esc(C.via)} ${esc(cname(C.via))}</span><div class="ans">${yn(C.ans)}?</div><div class="why">${esc(C.q.a)}</div><div class="sub">공식 Q&amp;A: ${esc(C.q.q)}${C.q.neg!==(ST.sl.has(NEGI)?1:0)?' · 반대로 물은 질문이라 뒤집음':''}<br>상황이 이 Q&amp;A와 같을 때만 같은 답입니다(예: 실제로 DP가 0이 되는 경우). 최신 팩 시험에서 이런 참고 답은 9건 중 5건만 맞았으니 Claude나 심판에게 확인하세요.</div>${DIST?'':'<div class="row"><button class="btn2" type="button" data-askai="1">Claude에게도 묻기</button></div>'}</div>`;return h+autoNote()}
  if(R&&R.eng&&R.eng.sure&&R.level!=='sure'&&!(A&&A.r)){const E=R.eng;
    h=`<div class="verdict v-sure"><span class="badge">엔진 판정 · Claude 없이 · 확신 ${Math.round(E.conf*100)}%</span><div class="ans">${yn(E.ans)}</div><div class="why">문구가 가장 가까운 공식 Q&amp;A(유사도 ${Math.round(Math.min(1,E.top[0].s)*100)}%)${E.rg?` 와 같은 이유 묶음 「${esc(E.rg.name.length>70?E.rg.name.slice(0,70)+'…':E.rg.name)}」(Q&amp;A ${E.rg.n}건)`:''}을 근거로 냈습니다.</div><div class="sub">최신 팩 질문 시험(이전 팩만 보고 판정)에서 이 확신 이상인 판정 48%를 정확도 99%로 맞혔습니다. 「쟁점별 비슷한 질문」 탭에서 근거를 확인하세요.</div><div class="row"><button class="btn2" type="button" data-askai="1">Claude에게도 묻기</button></div></div>`;
    return h}
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
  const tabs=[(R.issues||[]).length?['issue','같은 룰 쟁점',R.issues.reduce((s,x)=>s+x.qa.length+x.rules.length,0)]:null,['prec','같은 상황 선례',R.list.length],['sim','쟁점별 비슷한 질문',(R.groups||[]).length],['own',involved().length>1?'고른 카드 Q&A':'이 카드 Q&A',own.length],extras().length?['combo','조합 Q&A',R.combo.length]:null,trigOf(u)?['trig','같은 유발 조건 Q&A',triggerQA(u,40,ST.cards[0]&&ST.cards[0].no).length]:null,['struct','룰북 구조',strOf(u)?strOf(u)[4].length:0],strOf(u)&&strOf(u)[6]>=0?['clu','같은 효과 무리 Q&A',clusterQA(u,40,ST.cards[0]&&ST.cards[0].no).length]:null,['rule','룰 조항',u.rules.length],['pat','같은 패턴 Q&A',patternQA(u,30,ST.cards[0]&&ST.cards[0].no).length],A&&A.ev?['ai','Claude 근거',A.ev.length]:null].filter(Boolean);
  const crl=CR.list.filter(r=>involved().includes(r.card));if(crl.length)tabs.splice(1,0,['cr','확인된 판정',crl.length]);
  const sem=semQA(ST.q,10);if(sem.length)tabs.splice(2,0,['sem','의미 검색',sem.length]);
  if(!tabs.some(t=>t&&t[0]===ST.tab))ST.tab=tabs.find(Boolean)[0];
  let body='';const myneg=ST.sl.has(NEGI)?1:0;
  if(ST.tab==='issue')body=(R.issues||[]).map(x=>`<div class="empty" style="padding:0 2px"><b>${esc(x.name)}</b> — ${esc(x.desc)}</div>`+x.rules.map(itemRule).join('')+x.qa.map(i=>itemQA(QA[i],'<span>· 같은 룰 쟁점</span>')).join('')).join('');
  else if(ST.tab==='prec')body=R.list.length?R.list.slice(0,20).map(x=>itemQA(x.q,`<span>· ${TIERNAME[R.tier]}</span><span class="yn">답: ${yn(x.y)}</span>${x.q.neg!==myneg?'<span>(반대로 물은 질문이라 뒤집음)</span>':''}`)).join(''):'<div class="empty">묻는 것과 상황이 완전히 같은 선례가 없습니다. 상황 태그를 줄이면 찾을 수도 있습니다.</div>';
  else if(ST.tab==='sim'){const gs=(R.groups||[]).slice(0,12);const myneg=ST.sl.has(NEGI)?1:0;
    body=gs.length?gs.map((G,k)=>{const shown=G.mem.slice().sort((a,b)=>(G.hits.find(h=>h.q===b)?.s||0)-(G.hits.find(h=>h.q===a)?.s||0));
      const row=q=>itemQA(q,`${q.y>=0?`<span class="yn">답: ${yn(q.y^(q.neg^myneg))}</span>`:''}${q.y>=0&&q.neg!==myneg?'<span>(반대로 물은 질문이라 뒤집음)</span>':''}`);
      return `<div class="grp"><div class="grp-h"><b>쟁점 ${k+1}</b><span>유사도 ${Math.round(Math.min(1,G.best)*100)}%</span><span>Q&amp;A ${G.mem.length}건 · 카드 ${G.cards}장</span>${G.yes+G.no?`<span class="yn">네 ${G.yes} · 아니요 ${G.no}${G.cons===1&&G.yes+G.no>1?' · 일치':''}</span>`:''}</div>
        <div class="grp-q">${esc(G.lead.q)}</div>${shown.slice(0,3).map(row).join('')}${shown.length>3?`<details><summary>같은 쟁점 ${shown.length-3}건 더</summary>${shown.slice(3,40).map(row).join('')}</details>`:''}</div>`}).join(''):'<div class="empty">문구가 비슷한 공식 Q&amp;A가 없습니다.</div>'}
  else if(ST.tab==='own')body=own.length?own.map(q=>itemQA(q,'')).join(''):'<div class="empty">고른 카드에 등록된 Q&amp;A가 없습니다. 「같은 패턴 Q&amp;A」와 「비슷한 질문」을 보세요.</div>';
  else if(ST.tab==='trig'){const l=triggerQA(u,40,ST.cards[0]&&ST.cards[0].no);const t=trigOf(u);const n=(BY_TRIG[t]||[]).length;
    body=`<div class="empty" style="padding:0 2px">${esc(t.replace('유발 · ','유발 조건: '))} · 같은 조건으로 발동하는 효과 ${n}개</div>`+(l.length?l.map(q=>itemQA(q,'')).join(''):'<div class="empty">같은 유발 조건 효과에 연결된 Q&amp;A가 없습니다.</div>')}
  else if(ST.tab==='combo')body=R.combo.length?R.combo.map(q=>itemQA(q,'')).join(''):'<div class="empty">함께 고른 카드 이름이 같이 나오는 Q&amp;A가 없습니다.</div>';
  else if(ST.tab==='cr')body=crl.slice().sort((a,b)=>String(b.at).localeCompare(String(a.at))).map(r=>`<div class="item"><div class="src"><span class="cno">${esc(r.card)}</span><span>${esc(cname(r.card))}</span>${r.others?`<span>+ ${esc(r.others)}</span>`:''}<span class="yn">답: ${yn(r.ans)}</span><span>· ${esc(SRCN[r.src]||'')}${r.agreed===false?' → 바로잡음':''}</span><span>${esc(String(r.at||'').slice(0,10))}</span></div><div class="q"><b>Q</b><span>${esc(r.q||'')}</span></div>${r.note?`<div class="a"><b>메모</b><span>${esc(r.note)}</span></div>`:''}</div>`).join('');
  else if(ST.tab==='sem')body=`<div class="empty" style="padding:0 2px">문장 뜻이 가까운 공식 Q&amp;A입니다(학습한 검색 모델, 판정에는 쓰지 않음). 상황이 같은지 직접 확인하세요.</div>`+sem.map(x=>itemQA(x.q,`<span>· 의미 유사 ${Math.round(x.s*100)}%</span>${x.q.y>=0?`<span class="yn">답: ${yn(x.q.y^(x.q.neg^(ST.sl.has(NEGI)?1:0)))}</span>`:''}`)).join('');
  else if(ST.tab==='struct')body=structHTML(u);
  else if(ST.tab==='clu'){const l=clusterQA(u,40,ST.cards[0]&&ST.cards[0].no);const c=CLU[strOf(u)[6]];
    body=`<div class="empty" style="padding:0 2px">같은 효과 무리: ${esc(c[0])} · 효과 ${c[3]}개 (효과 네트워크 클러스터)</div>`+(l.length?l.map(q=>itemQA(q,'')).join(''):'<div class="empty">같은 무리 효과에 연결된 Q&amp;A가 없습니다.</div>')}
  else if(ST.tab==='rule')body=u.rules.map(itemRule).join('')||'<div class="empty">연결된 룰 조항이 없습니다.</div>';
  else if(ST.tab==='pat'){const l=patternQA(u,30,ST.cards[0]&&ST.cards[0].no);body=l.length?l.map(q=>itemQA(q,'')).join(''):'<div class="empty">같은 패턴의 다른 카드 Q&amp;A가 없습니다.</div>'}
  else if(ST.tab==='ai')body=A.ev.map(it=>it.qa?itemQA(it.qa,''):itemRule(it.id.slice(1))).join('');
  return `<div class="ev"><div class="tabs" role="tablist">${tabs.map(([k,n,c])=>`<button type="button" role="tab" data-tab="${k}" aria-selected="${ST.tab===k}">${n}<span class="n">${c}</span></button>`).join('')}</div><div class="tabp" role="tabpanel">${body}</div></div>`}
function decisive(){const R=ST.res;return !!R&&(ST.pickQ!=null||!!R.xref||R.level==='sure'||!!R.cr||!!R.iv||!!(R.eng&&R.eng.sure))}
function aiOffer(){const R=ST.res,A=ST.ai;if(!DIST||!R||A||decisive())return '';
  return `<div class="verdict v-none"><span class="badge">판정 보류 · 심판 확인 필요</span><div class="why">공식 Q&amp;A·확인된 판정·룰 쟁점 가운데 이 질문에 확실히 맞는 근거가 없습니다. 아래 참고 자료는 정답이 아닐 수 있습니다.</div><div class="sub">질문 칸의 추천 문장으로 다시 물으면 맞는 근거를 찾을 수 있습니다. 정답을 아는 분은 아래에서 알려 주세요 — 심판이 확인하면 판정으로 쌓여 다음부터 바로 답합니다.</div></div>`}
function renderResult(){const v=ST.res||ST.ai?verdictHTML():'';$('result').innerHTML=ST.res||ST.ai?(DIST?aiOffer()+v:v+aiOffer())+(v.includes('질문에서 「')?'':autoNote())+crPanel()+tabsHTML():''}

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
$('askq').addEventListener('input',e=>{ST.q=e.target.value;ST.pickQ=null;syncMeta();renderMeta();updateGo();if(ST.res||ST.ai)resetResult();SUGI=-1;renderSugg()});
(()=>{const s=document.createElement('div');s.id='sugg';s.className='sugg';s.setAttribute('role','listbox');s.hidden=true;$('askq').insertAdjacentElement('afterend',s)})();
$('askq').addEventListener('focus',()=>{renderSugg()});
$('askq').addEventListener('blur',()=>{setTimeout(()=>{if(!(document.activeElement&&document.activeElement.closest&&document.activeElement.closest('#sugg')))renderSugg()},150)});
$('askq').addEventListener('keydown',e=>{
  if(SUGG.length&&(e.key==='ArrowDown'||e.key==='ArrowUp')){e.preventDefault();const n=SUGG.length+1;SUGI=((SUGI+1+(e.key==='ArrowDown'?1:-1))%n+n)%n-1;renderSugg();return}
  if(e.key==='Escape'){SUGG=[];const s=$('sugg');if(s){s.hidden=true}return}
  if(e.key==='Enter'&&!e.shiftKey&&SUGI>=0&&SUGG[SUGI]){e.preventDefault();pickSugg(SUGI);return}
  if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();if(!$('go').disabled)judge()}});
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
  const sg=t.closest('[data-sg]');if(sg){pickSugg(+sg.dataset.sg);return}
  if(t.closest('[data-askai]')){askClaude();return}
  const cs=t.closest('[data-crsave]');if(cs){crSave(+cs.dataset.crsave);return}
  const cr=t.closest('[data-crrep]');if(cr){crReport(+cr.dataset.crrep);return}
  if(t.closest('[data-crcopy]')){const ta=document.querySelector('.crcode');const done=()=>{CR.msg='복사했습니다.';renderResult()};
    if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(CR.code).then(done,()=>{if(ta){ta.select();CR.msg='자동 복사가 막혀 있습니다. 코드를 길게 눌러 복사해 주세요.';renderResult()}});else{if(ta)ta.select();CR.msg='코드를 길게 눌러 복사해 주세요.';renderResult()}return}
  if(t.id==='jkeyset'){const v=($('jkey')||{}).value||'';try{localStorage.setItem('judgeKey',v.trim())}catch(e){}
    api('whoami').then(j=>{$('jkeymsg').textContent=j.judge?`${j.judge} 님으로 로그인했습니다. 새로고침하면 확인·저장 버튼이 보입니다.`:'키가 맞지 않습니다.';if(j.judge)location.reload()}).catch(()=>{$('jkeymsg').textContent='서버에 연결하지 못했습니다.'});return}
  if(t.id==='jkeyout'){try{localStorage.removeItem('judgeKey')}catch(e){}location.reload();return}
  if(t.id==='crpull'){api('reports').then(L=>{CRREP=L;$('crin').value=L.map(d=>'JD1:'+b64e(JSON.stringify({...d,by:d.by||''}))).join('\n');$('crpreview').click()}).catch(()=>{$('crprev').innerHTML='<div class="sub">제보를 불러오지 못했습니다(심판 로그인 확인).</div>'});return}
  if(t.id==='crpreview'){const r=parseCodes(($('crin')||{}).value||'');CRIN=r.out;
    $('crprev').innerHTML=(r.out.map(d=>`<div class="item"><div class="src"><span class="cno">${esc(d.card)}</span><span>${esc(cname(d.card))}</span>${d.others?`<span>+ ${esc(d.others)}</span>`:''}<span class="yn">답: ${yn(d.ans)}</span></div><div class="q"><b>Q</b><span>${esc(d.q)}</span></div>${d.note?`<div class="a"><b>근거</b><span>${esc(d.note)}</span></div>`:''}</div>`).join('')||'')+(r.bad.length?`<div class="sub">읽지 못한 코드 ${r.bad.length}개</div>`:'')+(!r.out.length&&!r.bad.length?'<div class="sub">붙여 넣은 코드가 없습니다.</div>':'');
    $('crimp').disabled=!r.out.length;return}
  if(t.id==='crimp'){if(!CRIN.length||!CR.db)return;t.disabled=true;let n=0,fail=0;
    (async()=>{for(const d of CRIN){try{await CR.db.collection('rulings').add(d);n++}catch(e){fail++}}
      if(SRV&&CRREP.length){for(const r of CRREP){try{await api('reports/'+r.id+'/done',{method:'POST'})}catch(e){}}CRREP=[]}
      $('crprev').innerHTML=`<div class="sub">${n}건 저장했습니다.${fail?` ${fail}건은 저장하지 못했습니다(권한 확인).`:''}</div>`;$('crin').value='';CRIN=[]})();return}
  if(t.id==='aistop'&&ST.ctl){ST.ctl.abort();return}
  if(t.id==='pmmanage'){(async()=>{try{const pm=await window.claude.use('permissions');if(pm)await pm.manage()}catch(e){}})();return}
  const ex=t.closest('[data-ex]');if(ex){loadExample(+ex.dataset.ex);return}
  // legacy browse view
  const ask=t.closest('[data-ask]');if(ask){const u=ASKU[+ask.dataset.ask];if(u&&!u.pasted&&ST.cards[0]&&u.card===ST.cards[0].no){ST.sel=u.i;renderCards();updateGo();$('askq').focus();window.scrollTo(0,0)}return}
  const c=t.closest('[data-card]');if(c&&D.cards[c.dataset.card]){ST.cards=[];ST.sel=null;addCard(c.dataset.card);window.scrollTo(0,0);return}
  const p=t.closest('[data-pat]');if(p){showPattern(+p.dataset.pat);return}
  const m=t.closest('[data-more]');if(m){$(m.dataset.more).hidden=false;m.remove()}
});
renderExamples();renderCards();renderMeta();updateGo();
