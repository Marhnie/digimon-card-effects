const {JSDOM}=require('jsdom');const fs=require('fs');
let html=fs.readFileSync(process.argv[2],'utf8');const d3src=fs.readFileSync('node_modules/d3/dist/d3.min.js','utf8');
html=html.replace(/<script src="https:\/\/cdnjs[^"]+"><\/script>/,()=>'<script>'+d3src+'</script>');
const errs=[];const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){
  w.addEventListener('error',e=>errs.push(e.message));w.matchMedia=()=>({matches:true});Object.defineProperty(w.HTMLElement.prototype,'clientWidth',{get(){return 900}});Object.defineProperty(w.HTMLElement.prototype,'clientHeight',{get(){return 600}})}});
const w=dom.window,d=w.document;
setTimeout(()=>{
  console.log('A circles',d.querySelectorAll('#svg circle').length,'lines',d.querySelectorAll('#svg line').length,'labels',d.querySelectorAll('#svg text').length);
  console.log('legend',d.getElementById('legend').textContent.replace(/\s+/g,' ').slice(0,160));
  const c=d.querySelector('#svg circle');c.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));console.log('panel',d.getElementById('panel').textContent.replace(/\s+/g,' ').slice(0,160));
  d.querySelector('[data-view=B]').click();
  setTimeout(()=>{console.log('B circles',d.querySelectorAll('#svg circle').length,'lines',d.querySelectorAll('#svg line').length);
    d.querySelector('[data-lt=e]').click();d.querySelector('[data-lt=e]').dispatchEvent(new w.Event('change',{bubbles:true}));
    console.log('B lines without elem links',d.querySelectorAll('#svg line').length);
    d.querySelector('#svg circle').dispatchEvent(new w.MouseEvent('click',{bubbles:true}));console.log('B panel',d.getElementById('panel').textContent.replace(/\s+/g,' ').slice(0,200));
    d.querySelector('[data-comm="0"]').click();console.log('comm focus ok');
    const xs=[...d.querySelectorAll('#svg circle')].map(c=>+c.getAttribute('cx'));console.log('x range',Math.min(...xs).toFixed(0),Math.max(...xs).toFixed(0));
    console.log('errors',errs)},300)},500);
