const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('card-effect-test.html','utf8');const errs=[];
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.addEventListener('error',e=>errs.push(e.message))}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);
const run=(v)=>{$('q').value=v;$('go').click();const units=d.querySelectorAll('.unit');
  return {h:(d.querySelector('.cardhead')||{}).textContent?.replace(/\s+/g,' ').slice(0,90),units:units.length,secs:[...d.querySelectorAll('details.sec summary')].slice(0,5).map(s=>s.textContent.replace(/\s+/g,' ').trim()),chips:[...d.querySelectorAll('.unit')][0]?.querySelector('.uhead')?.textContent.replace(/\s+/g,' ').slice(0,120)}};
for(const v of ['BT14-033','bt3-001','메탈그레이몬','【등장 시】【진화 시】상대의 디지몬 1마리를 레스트시킨다. 그 후, 상대의 턴 종료까지 상대의 디지몬 1마리는 액티브가 되지 않는다.','〔진화〕「아구몬」 : 코스트 2【진화 시】《1 드로우》 【자신의 턴】이 디지몬의 DP를 +2000 한다.','ZZ-999']){const t0=Date.now();const r=run(v);console.log(Date.now()-t0+'ms',JSON.stringify(r))}
run('EX8-029');d.querySelector('[data-pat]').click();console.log('pattern view',d.querySelector('.cardhead').textContent.replace(/\s+/g,' '));
console.log('errors',errs);
run('BT14-033');const g=[...d.querySelectorAll('details.sec')].find(s=>s.textContent.includes('관련 일반 판정'));console.log(g.querySelector('.qa .q').textContent.slice(0,100));
