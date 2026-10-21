/* Semantic question search (E33): the distilled student of train/distill_student.py, in plain JS.
   Query -> hashed char 2/3-grams (FNV-1a over UTF-8) -> mean of int8 embedding rows -> linear d->D -> L2 norm,
   compared with the teacher's int8 vectors of every official question. Must match prep()/grams() in distill_student.py. */
const QEMB=(()=>{
  const st={ready:false,err:null};
  // UTF-8 bytes without depending on TextEncoder (older webviews / test DOMs)
  const utf8=s=>{const u=unescape(encodeURIComponent(s));const b=new Uint8Array(u.length);for(let i=0;i<u.length;i++)b[i]=u.charCodeAt(i);return b};
  function fnv(str){const b=utf8(str);let h=0x811c9dc5;for(let i=0;i<b.length;i++){h^=b[i];h=Math.imul(h,0x01000193)>>>0}return h>>>0}
  const prep=s=>'\u0002'+String(s).trim().replace(/\s+/g,' ').toLowerCase()+'\u0003';
  function grams(s,B){const t=[...prep(s)];const out=[];for(const n of [2,3])for(let i=0;i+n<=t.length;i++)out.push(fnv(t.slice(i,i+n).join(''))%B);return out}
  async function init(get){try{
      const dec=b=>decodeURIComponent(escape(String.fromCharCode.apply(null,new Uint8Array(b))));
      const meta=JSON.parse(dec(await get('meta.json')));
      const [E,S,L,C,ids]=await Promise.all(['student_emb.i8','student_scale.f32','student_lin.f32','corpus.i8','corpus_ids.json'].map(get));
      Object.assign(st,{meta,E:new Int8Array(E),S:new Float32Array(S),L:new Float32Array(L),C:new Int8Array(C),ids:JSON.parse(dec(ids)),ready:true});
    }catch(e){st.err=String(e&&e.message||e)}return st.ready}
  function embed(text){const {buckets:B,dim:d,D}=st.meta;const g=grams(text,B);const h=new Float32Array(d);
    const gg=g.length?g:[0];for(const r of gg){const s=st.S[r],o=r*d;for(let k=0;k<d;k++)h[k]+=st.E[o+k]*s}
    for(let k=0;k<d;k++)h[k]/=gg.length;
    const v=new Float32Array(D);for(let j=0;j<D;j++)v[j]=st.L[d*D+j];
    for(let k=0;k<d;k++){const hk=h[k];if(!hk)continue;const o=k*D;for(let j=0;j<D;j++)v[j]+=hk*st.L[o+j]}
    let n=0;for(let j=0;j<D;j++)n+=v[j]*v[j];n=Math.sqrt(n)||1;for(let j=0;j<D;j++)v[j]/=n;return v}
  // top-k official questions by cosine (corpus int8 /127); filter(qaIndex) may exclude some
  function search(text,k=10,filter){if(!st.ready)return [];const v=embed(text);const D=st.meta.D,C=st.C,ids=st.ids;const sc=[];
    for(let r=0;r<ids.length;r++){if(filter&&!filter(ids[r]))continue;let s=0;const o=r*D;for(let j=0;j<D;j++)s+=C[o+j]*v[j];sc.push([s/127,ids[r]])}
    sc.sort((a,b)=>b[0]-a[0]);return sc.slice(0,k).map(([s,i])=>({i,s}))}
  return {st,init,embed,search,grams};
})();
if(typeof module!=='undefined')module.exports=QEMB;
