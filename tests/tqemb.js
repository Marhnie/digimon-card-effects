// JS student == Python student (probe vectors) for an exported model dir: node tests/tqemb.js train/export_qemb_tiny
const fs=require('fs'),path=require('path');const dir=process.argv[2]||'train/export_qemb_tiny';
globalThis.TextEncoder=require('util').TextEncoder;globalThis.TextDecoder=require('util').TextDecoder;
const Q=require('../v3_qemb.js');
(async()=>{const ok=await Q.init(async n=>{const b=fs.readFileSync(path.join(dir,n));return b.buffer.slice(b.byteOffset,b.byteOffset+b.length)});
  if(!ok){console.log('FAIL init',Q.st.err);process.exit(1)}
  const P=JSON.parse(fs.readFileSync(path.join(dir,'probe.json'),'utf8'));let worst=0;
  P.texts.forEach((t,k)=>{const v=Q.embed(t);const cos=P.vec[k].reduce((s,x,j)=>s+x*v[j],0);worst=Math.max(worst,1-cos);console.log('probe',k,'cos(js,py)=',cos.toFixed(5))});
  const t0=Date.now();const r=Q.search('파피몬 등장시 1드로 쓸수있어?',5);console.log('search ms',Date.now()-t0,r.map(x=>x.i+':'+x.s.toFixed(3)).join(' '));
  console.log(worst<0.01?'PASS js matches python (int8 rounding)':'FAIL mismatch');process.exit(worst<0.01?0:1)})();
