const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');const errs=[];
const dom=new JSDOM('<!doctype html><html><head></head><body>'+html+'</body></html>',{runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){
 w.addEventListener('error',e=>errs.push(e.message));w.matchMedia=()=>({matches:false,addEventListener(){}});w.ResizeObserver=class{constructor(f){this.f=f}observe(){setTimeout(()=>this.f(),0)}};
 w.HTMLElement.prototype.getBoundingClientRect=function(){return {left:0,top:0,width:900,height:600}};w.HTMLCanvasElement.prototype.getContext=function(){return new Proxy({},{get:(t,k)=>k in t?t[k]:(()=>{}),set:(t,k,v)=>{t[k]=v;return true}})};w.HTMLCanvasElement.prototype.setPointerCapture=()=>{};
 w.requestAnimationFrame=f=>setTimeout(f,0);w.cancelAnimationFrame=()=>{}}});
const w=dom.window,d=w.document;
setTimeout(()=>{console.log('sub',d.getElementById('sub').textContent.slice(0,80));console.log('legend items',d.querySelectorAll('#legend button').length);
 console.log('panel',d.getElementById('panel').textContent.replace(/\s+/g,' ').slice(0,200));
 const f=d.getElementById('find');f.value='EX8-005 고로몬';f.dispatchEvent(new w.Event('change',{bubbles:true}));
 setTimeout(()=>{console.log('selected panel',d.getElementById('panel').textContent.replace(/\s+/g,' ').slice(0,420));console.log('errors',errs)},50)},200);
