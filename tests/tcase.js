// Reproduce one judge-helper case: node tests/tcase.js <main card> <other card> "<question>"
const {JSDOM}=require('jsdom');const fs=require('fs');
const [main,other,q]=process.argv.slice(2);
const html=fs.readFileSync('card-effect-test.html','utf8');const errs=[];let prompt=null;
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){};w.matchMedia=()=>({matches:false});w.addEventListener('error',e=>errs.push(e.message));
 const f=async()=>{};f.json=async(p)=>{prompt=p;return {verdict:'(모의)',summary:'',reasons:[],caution:'',conf:0.5}};w.claude={use:async()=>f}}});
const w=dom.window,d=w.document,$=i=>d.getElementById(i);
const type=(el,v)=>{el.value=v;el.dispatchEvent(new w.Event('input',{bubbles:true}))};const key=(el,k)=>el.dispatchEvent(new w.KeyboardEvent('keydown',{key:k,bubbles:true}));
setTimeout(()=>{type($('cardq'),main);key($('cardq'),'Enter');
 setTimeout(()=>{if(other){$('addcard').click();type($('cardq'),other);key($('cardq'),'Enter')}
  setTimeout(()=>{const rs=[...d.querySelectorAll('input[name=mainEff]')];
   const pick=rs.find(r=>/파기되었을 때/.test(r.closest('label').textContent))||rs[rs.length-1];pick.checked=true;pick.dispatchEvent(new w.Event('change',{bubbles:true}));
   console.log('effect',d.querySelector('.eff.on').textContent.replace(/\s+/g,' ').slice(0,90));
   type($('askq'),q);$('go').click();
   setTimeout(()=>{const v=d.querySelector('.verdict');console.log('verdict',v?v.textContent.replace(/\s+/g,' ').slice(0,260):'none');
    console.log('claude called',!!prompt);
    if(prompt){const ev=prompt.slice(prompt.indexOf('\n[자료]\n'));const lines=ev.split(/\n/).filter(l=>/^\[[QR]/.test(l));
     if(process.env.DUMP)console.log(lines.map(l=>l.slice(0,80)).join('\n'));
     console.log('evidence has EX10-058',/EX10-058/.test(ev),'| 15-4-4-3',/15-4-4-3/.test(ev),'| 4-17-5',/4-17-5/.test(ev),'| items',lines.length)}
    console.log('tabs',[...d.querySelectorAll('.tabs button')].map(b=>b.textContent).join(' | '));
    console.log('errors',errs)},500)},300)},300)},300);
