import docx,json,sys
d=docx.Document(sys.argv[1])
cnt=[0]*6; out=[]; mode='body'; hist=[]
for p in d.paragraphs:
    t=p.text.strip()
    pPr=p._p.pPr
    if pPr is not None and pPr.numPr is not None and pPr.numPr.ilvl is not None:
        lv=pPr.numPr.ilvl.val
        cnt[lv]+=1
        for k in range(lv+1,6): cnt[k]=0
        if not t: continue
        out.append({'n':'-'.join(str(x) for x in cnt[:lv+1]),'l':lv,'t':t})
    else:
        if not t: continue
        if out: hist.append(t)
        else: out.append({'n':'','l':-1,'t':t})
json.dump({'rules':out,'hist':hist},open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)
print(len(out),len(hist))
