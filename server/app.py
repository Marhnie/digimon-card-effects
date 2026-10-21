"""Judge-helper server (E34): serves the Claude-free judge helper page and the APIs it needs, from this PC.

  GET  /                      the page (built by `python build_v3.py --server` into server/static/index.html)
  POST /api/search            {"q": text, "k": 10}  -> [{"i": qa_index, "s": cosine}]   semantic question search (retriever)
  GET  /api/rulings           confirmed rulings (everyone)
  POST /api/rulings           add a confirmed ruling            (header X-Judge-Key required)
  GET  /api/whoami            {"judge": name | null}            (checks X-Judge-Key)
  POST /api/reports           a viewer reports the correct answer (anyone; stored for judges to review)
  GET  /api/reports           pending reports                    (judges)
  POST /api/reports/{id}/done mark a report handled              (judges)

Run:  python server/app.py            (port 8787; model = env QEMB_MODEL or train/runs/retriever_cpu/model)
Judges: server/judges.json  {"<key>": "<name>"}   — keep this file private (it is git-ignored).
No LLM is called anywhere: search returns official Q&A indices only; answers come from the official Q&A / judges.
"""
import json, os, re, sqlite3, time, threading, secrets
import numpy as np
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MODEL = os.environ.get('QEMB_MODEL', os.path.join(ROOT, 'train', 'runs', 'retriever_cpu', 'model'))
DB = os.path.join(HERE, 'judge.db')
JUDGES_F = os.path.join(HERE, 'judges.json')
PAGE = os.path.join(HERE, 'static', 'index.html')

T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))
QA = T['qa']; DOC = [i for i, r in enumerate(QA) if r[0]]
import sys; sys.path.insert(0, ROOT)
from qfuse import Fuser          # E31: model cosine + 2-gram fused by RRF (colloquial @1 0.816 -> 0.874)
FUSE = Fuser(QA, DOC)

app = FastAPI(docs_url=None, redoc_url=None)
lock = threading.Lock()


def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute('create table if not exists rulings (id integer primary key, doc text, at real)')
    c.execute('create table if not exists reports (id integer primary key, doc text, at real, done integer default 0, ip text)')
    return c


def judges():
    if not os.path.exists(JUDGES_F):
        k = secrets.token_urlsafe(12)
        json.dump({k: '운영자'}, open(JUDGES_F, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('created', JUDGES_F, '— first judge key:', k)
    return json.load(open(JUDGES_F, encoding='utf-8'))


def judge_of(req):
    return judges().get(req.headers.get('x-judge-key', ''))


# ---------------- semantic search ----------------
SEM = {'model': None, 'E': None, 'err': None}


def load_model():
    try:
        if not os.path.exists(MODEL):
            SEM['err'] = f'model not found: {MODEL}'; print(SEM['err']); return
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(MODEL, device='cpu')
        cache = os.path.join(HERE, 'corpus_emb.npy'); stamp = os.path.join(HERE, 'corpus_emb.stamp')
        key = f"{os.path.getmtime(MODEL)}|{len(DOC)}"
        if os.path.exists(cache) and os.path.exists(stamp) and open(stamp).read() == key:
            E = np.load(cache)
        else:
            t0 = time.time(); E = m.encode([QA[i][1] for i in DOC], normalize_embeddings=True, batch_size=64, show_progress_bar=False)
            np.save(cache, E); open(stamp, 'w').write(key); print(f'corpus encoded in {time.time() - t0:.0f}s')
        SEM.update(model=m, E=E.astype(np.float32)); print('semantic search ready', E.shape)
    except Exception as e:
        SEM['err'] = str(e); print('model load failed', e)


threading.Thread(target=load_model, daemon=True).start()


@app.post('/api/search')
async def search(req: Request):
    b = await req.json(); q = str(b.get('q', ''))[:500]; k = max(1, min(int(b.get('k', 10)), 30))
    if SEM['model'] is None:
        return JSONResponse({'ready': False, 'err': SEM['err'], 'hits': []}, status_code=503)
    if not q.strip():
        return {'ready': True, 'hits': []}
    v = SEM['model'].encode([q], normalize_embeddings=True, show_progress_bar=False)[0]
    s = SEM['E'] @ v
    return {'ready': True, 'hits': FUSE.hits(q, s, k * 3)}


# ---------------- rulings & reports ----------------
def clean_doc(d):
    keep = ('card', 'others', 'unit', 'q', 'neg', 'it', 'slots', 'ans', 'src', 'agreed', 'summary', 'note', 'reporter', 'reported_at')
    d = {k: d.get(k) for k in keep if k in d}
    if not isinstance(d.get('card'), str) or not isinstance(d.get('q'), str) or d.get('ans') not in (0, 1):
        raise HTTPException(400, 'bad ruling')
    for k in ('card', 'others', 'q', 'summary', 'note', 'reporter', 'reported_at', 'src'):
        if k in d and d[k] is not None: d[k] = str(d[k])[:1000]
    return d


@app.get('/api/whoami')
def whoami(req: Request):
    return {'judge': judge_of(req)}


@app.get('/api/rulings')
def rulings():
    with lock, db() as c:
        return [{**json.loads(r['doc']), 'id': r['id']} for r in c.execute('select * from rulings order by id')]


@app.post('/api/rulings')
async def add_ruling(req: Request):
    j = judge_of(req)
    if not j: raise HTTPException(403, 'judge key required')
    d = clean_doc(await req.json()); d['by'] = j; d['at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    with lock, db() as c:
        cur = c.execute('insert into rulings (doc, at) values (?, ?)', (json.dumps(d, ensure_ascii=False), time.time()))
        return {'id': cur.lastrowid}


LAST = {}


@app.post('/api/reports')
async def add_report(req: Request):
    ip = req.headers.get('cf-connecting-ip') or (req.client.host if req.client else '')
    now = time.time()
    if now - LAST.get(ip, 0) < 5: raise HTTPException(429, 'too many reports')
    LAST[ip] = now
    d = clean_doc(await req.json()); d['at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    with lock, db() as c:
        if c.execute('select count(*) from reports where done=0').fetchone()[0] > 2000: raise HTTPException(503, 'report box full')
        cur = c.execute('insert into reports (doc, at, ip) values (?, ?, ?)', (json.dumps(d, ensure_ascii=False), now, ip))
        return {'id': cur.lastrowid}


@app.get('/api/reports')
def reports(req: Request):
    if not judge_of(req): raise HTTPException(403, 'judge key required')
    with lock, db() as c:
        return [{**json.loads(r['doc']), 'id': r['id']} for r in c.execute('select * from reports where done=0 order by id')]


@app.post('/api/reports/{rid}/done')
def report_done(rid: int, req: Request):
    if not judge_of(req): raise HTTPException(403, 'judge key required')
    with lock, db() as c:
        c.execute('update reports set done=1 where id=?', (rid,)); return {'ok': True}


@app.get('/')
def page():
    if not os.path.exists(PAGE): raise HTTPException(503, 'page not built: python build_v3.py --server')
    return FileResponse(PAGE, media_type='text/html; charset=utf-8')


@app.get('/health')
def health():
    return {'semantic': SEM['model'] is not None, 'err': SEM['err'], 'qa': len(DOC)}


if __name__ == '__main__':
    judges()
    uvicorn.run(app, host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 8787)))
