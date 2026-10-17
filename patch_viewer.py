t = open('sna_template.html', encoding='utf-8').read()
def rep(a, b, cnt=1):
    global t
    assert a in t, a[:70]
    t = t.replace(a, b, cnt)

rep('''  <div class="grp"><label><input type="checkbox" id="showEdges"> 전체 링크 그리기</label></div>''',
'''  <div class="grp"><label><input type="checkbox" id="showClu" checked> 클러스터 보기</label><label><input type="checkbox" id="showEdges"> 전체 링크 그리기</label></div>''')
rep('''$('sub').textContent=`카드 효과 ${N.length.toLocaleString()}개를 노드로, 링크 ${L.length.toLocaleString()}개로 이은 지도 · 커뮤니티 ${D.comms.length}개 (진화 조건·〈룰〉 등 카드 정보는 효과가 아니라 제외)`;''',
'''const C=D.clusters,CO=D.coarse;let showClu=true,selC=null;
$('sub').textContent=`카드 효과 ${N.length.toLocaleString()}개를 노드로, 링크 ${L.length.toLocaleString()}개로 이은 지도 · 대분류 ${CO.length}개 · 클러스터 ${C.length}개 (진화 조건·〈룰〉 등 카드 정보는 효과가 아니라 제외)`;''')
t = t.replace("colorOf(n.c)", "colorOf(n.cc)")
rep('''const visible=n=>clsOn.has(n.cls)&&(focusC==null||(focusC==='other'?n.c>=8:n.c===focusC));''',
'''const inFocus=cc=>focusC==null||(focusC==='other'?cc>=8:cc===focusC);
const visible=n=>clsOn.has(n.cls)&&inFocus(n.cc);''')
rep('''  ctx.clearRect(0,0,W,H);''', '''  ctx.clearRect(0,0,W,H);
  const zoomedOut=view.s<Math.min(W,H)*1.4;
  if(showClu){
    if(zoomedOut&&sel==null){ctx.strokeStyle=css('--edge');
      for(const [a,b,w] of D.clinks){const A=C[a],B=C[b];if(!inFocus(A.cc)&&!inFocus(B.cc))continue;ctx.globalAlpha=Math.min(0.5,0.05+w/400);ctx.lineWidth=Math.min(6,0.5+w/40);
        ctx.beginPath();ctx.moveTo(sx(A.x),sy(A.y));ctx.lineTo(sx(B.x),sy(B.y));ctx.stroke()}ctx.globalAlpha=1}
    for(const c of C){if(!inFocus(c.cc))continue;const r=c.r*view.s;
      ctx.globalAlpha=selC===c.id?0.28:0.12;ctx.fillStyle=colorOf(c.cc);ctx.beginPath();ctx.arc(sx(c.x),sy(c.y),r,0,6.283);ctx.fill();
      ctx.globalAlpha=selC===c.id?1:0.45;ctx.strokeStyle=colorOf(c.cc);ctx.lineWidth=selC===c.id?2.5:1;ctx.stroke()}
    ctx.globalAlpha=1}''')
rep('''  // labels when zoomed in''', '''  if(showClu&&sel==null){ctx.textAlign='center';
    for(const c of C){if(!inFocus(c.cc))continue;const r=c.r*view.s;if(r<16&&selC!==c.id)continue;
      const lab=c.name.split(' · ').slice(0,2).join(' · ');ctx.font=(r>60?13:11)+'px "IBM Plex Sans KR",sans-serif';ctx.lineWidth=3;ctx.strokeStyle=css('--surface');ctx.fillStyle=css('--ink');
      const y=sy(c.y)-r-6;ctx.strokeText(lab,sx(c.x),y);ctx.fillText(lab,sx(c.x),y);
      ctx.font='10px "IBM Plex Mono",monospace';ctx.fillStyle=css('--muted');ctx.strokeText(c.n+'개',sx(c.x),y-13);ctx.fillText(c.n+'개',sx(c.x),y-13)}
    ctx.textAlign='start'}
  // labels when zoomed in''')
rep('''  if(view.s>1600||sel!=null){''', '''  if(view.s>Math.min(W,H)*6||sel!=null){''')
rep('''cv.addEventListener('pointerup',e=>{const r=cv.getBoundingClientRect();if(!moved){const k=hit(e.clientX-r.left,e.clientY-r.top);select(k)}drag=null});''',
'''function hitC(mx,my){let best=null,bd=1e9;for(const c of C){if(!inFocus(c.cc))continue;const d=Math.hypot(sx(c.x)-mx,sy(c.y)-my),r=c.r*view.s;if(d<=r&&r<bd){bd=r;best=c.id}}return best}
cv.addEventListener('pointerup',e=>{const r=cv.getBoundingClientRect();if(!moved){const mx=e.clientX-r.left,my=e.clientY-r.top;const k=hit(mx,my);
  if(k!=null)select(k);else if(showClu)selectC(hitC(mx,my));else select(null)}drag=null});
function selectC(c){selC=c;sel=null;if(c!=null){const cl=C[c];const span=cl.r*2.6;view.s=Math.min(W,H)/span;view.x=W/2-cl.x*view.s;view.y=H/2-cl.y*view.s}draw();panel()}''')
rep('''function select(k){sel=k;draw();panel()}''', '''function select(k){sel=k;if(k!=null)selC=null;draw();panel()}''')
rep('''  if(k==null){t.style.display='none';return}const n=N[k];''',
'''  if(k==null){const c=showClu?hitC(e.clientX-r.left,e.clientY-r.top):null;if(c==null){t.style.display='none';return}const cl=C[c];
    t.innerHTML=`<b>클러스터 #${c+1}</b> · 효과 ${cl.n} · 카드 ${cl.cards}<br>${esc(cl.name)}<br><span style="opacity:.8">대분류 ${cl.cc+1}: ${esc(CO[cl.cc].name)} · 누르면 안으로</span>`;
    t.style.display='block';t.style.left=Math.min(e.clientX-r.left+12,W-330)+'px';t.style.top=(e.clientY-r.top+12)+'px';return}
  const n=N[k];''')
rep('''function legend(){const shown=D.comms.slice(0,8).map((nm,k)=>`<button type="button" data-c="${k}" aria-pressed="${focusC===k}"><i style="background:${colorOf(k)}"></i>${k+1}. ${esc(nm)} <span style="color:var(--faint)">${D.csize[k]}</span></button>`).join('');
  $('legend').innerHTML=`<div style="font-weight:700;color:var(--muted)">효과 커뮤니티 · 누르면 강조</div>${shown}<button type="button" data-c="other" aria-pressed="${focusC==='other'}"><i style="background:${COL.other}"></i>그 밖의 커뮤니티 ${D.comms.length-8}개</button>`}''',
'''function legend(){const shown=CO.slice(0,8).map((g,k)=>`<button type="button" data-c="${k}" aria-pressed="${focusC===k}"><i style="background:${colorOf(k)}"></i>${k+1}. ${esc(g.name)} <span style="color:var(--faint)">${g.n} · ${g.fine.length}클러스터</span></button>`).join('');
  $('legend').innerHTML=`<div style="font-weight:700;color:var(--muted)">대분류 · 누르면 강조 (거품 = 클러스터)</div>${shown}${CO.length>8?`<button type="button" data-c="other" aria-pressed="${focusC==='other'}"><i style="background:${COL.other}"></i>그 밖의 대분류 ${CO.length-8}개</button>`:''}`}''')
rep('''      <details><summary>커뮤니티 표</summary><table><tr><th>#</th><th>커뮤니티(많이 나오는 요소)</th><th>효과</th></tr>${D.comms.map((c,k)=>`<tr><td class="n">${k+1}</td><td>${esc(c)}</td><td class="n">${D.csize[k]}</td></tr>`).join('')}</table></details>`;return}''',
'''      <div class="k">큰 클러스터 (누르면 안으로)</div><div class="lst">${C.slice(0,12).map(c=>`<button type="button" data-cl="${c.id}"><span class="cno">#${c.id+1}</span>${esc(c.name)}<span class="why">효과 ${c.n} · 카드 ${c.cards} · Q&amp;A ${c.nqa}</span></button>`).join('')}</div>
      <details><summary>클러스터 표 (${C.length}개)</summary><table><tr><th>#</th><th>대분류</th><th>클러스터(많이 나오는 요소)</th><th>효과</th><th>Q&amp;A</th></tr>${C.map(c=>`<tr><td class="n">${c.id+1}</td><td class="n">${c.cc+1}</td><td><button type="button" data-cl="${c.id}" style="border:0;background:none;padding:0;color:inherit;text-align:left;cursor:pointer;text-decoration:underline">${esc(c.name)}</button></td><td class="n">${c.n}</td><td class="n">${c.nqa}</td></tr>`).join('')}</table></details>`;return}''')
rep('''  if(sel==null){const top=''', '''  if(sel==null&&selC!=null){const c=C[selC];const mem=N.filter(n=>n.c===selC).sort((a,b)=>b.pr-a.pr);const nb=D.clinks.filter(l=>l[0]===selC||l[1]===selC).sort((a,b)=>b[2]-a[2]).slice(0,10);
    p.innerHTML=`<div class="k">대분류 ${c.cc+1}: ${esc(CO[c.cc].name)}</div><h2>클러스터 #${c.id+1}</h2><div class="tx">${esc(c.name)}</div>${c.auto&&c.auto!==c.name?`<div class="k">자동 요약: ${esc(c.auto)}</div>`:''}
      <div class="stats"><div><b>${c.n}</b><span>효과</span></div><div><b>${c.cards}</b><span>카드</span></div><div><b>${c.nqa}</b><span>Q&amp;A</span></div></div>
      <div class="k">많은 구조 그룹</div><div class="lst">${c.groups.map(g=>`<div style="background:var(--bg);border-radius:7px;padding:5px 8px;font-size:12.5px">${esc(g[0])} <b>${g[1]}</b></div>`).join('')}</div>
      <div class="k">가까운 클러스터 (사이 링크 강도 합, 크기 보정)</div><div class="lst">${nb.map(l=>{const o=C[l[0]===selC?l[1]:l[0]];return `<button type="button" data-cl="${o.id}"><span class="cno">#${o.id+1}</span>${esc(o.name)}<span class="sbar"><s><i style="width:${Math.min(100,l[2])}%"></i></s><b>${l[2]}</b></span></button>`}).join('')||'<div class="k">없음</div>'}</div>
      <div class="k">효과 (중심성 순, 앞 40개)</div><div class="lst">${mem.slice(0,40).map(n=>`<button type="button" data-k="${n.k}"><span class="cno">${esc(n.card)}</span>${esc(n.name)}<span class="why">${esc(n.text.slice(0,70))}…</span></button>`).join('')}</div>
      <button type="button" style="border:0;background:none;color:var(--muted);text-decoration:underline;cursor:pointer;justify-self:start" data-cl="">클러스터 선택 해제</button>`;return}
  if(sel==null){const top=''')
rep('''  p.innerHTML=`<div class="k">커뮤니티 ${n.c+1}: ${esc(D.comms[n.c]||'')}</div>''',
'''  p.innerHTML=`<div class="k"><button type="button" data-cl="${n.c}" style="border:0;background:none;padding:0;color:var(--accent);cursor:pointer;text-decoration:underline">클러스터 #${n.c+1}</button> · ${esc(C[n.c].name)}</div>''')
rep('''document.addEventListener('click',e=>{const c=e.target.closest('[data-c]');''',
'''document.addEventListener('click',e=>{const cl=e.target.closest('[data-cl]');if(cl){selectC(cl.dataset.cl===''?null:+cl.dataset.cl);return}
  const c=e.target.closest('[data-c]');''')
rep('''  if(e.target.id==='showEdges'){showEdges=e.target.checked;draw()}''',
'''  if(e.target.id==='showEdges'){showEdges=e.target.checked;draw()}
  if(e.target.id==='showClu'){showClu=e.target.checked;if(!showClu)selC=null;draw();panel()}''')
rep('''<div class="hint">끌어서 이동 · 휠/버튼으로 확대 · 점을 누르면 오른쪽에 자세히</div>''',
'''<div class="hint">끌어서 이동 · 휠/버튼으로 확대 · 거품(클러스터)이나 점(효과)을 누르면 오른쪽에 자세히</div>''')
rep('''<div><b>${D.comms.length}</b><span>커뮤니티</span></div>''', '''<div><b>${CO.length} / ${C.length}</b><span>대분류 / 클러스터</span></div>''')
rep("m:'카드 이름 언급'};", "m:'카드 이름 언급',p:'같은 처리(대상·조건)'};")
open('sna_template2.html', 'w', encoding='utf-8').write(t)
print('ok')
