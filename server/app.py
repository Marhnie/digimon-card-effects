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
# E38: optional second retriever trained on under-specified questions, fused in by RRF (skipped when absent or QEMB_MODEL2=none)
MODEL2 = os.environ.get('QEMB_MODEL2', os.path.join(ROOT, 'train', 'runs', 'retriever_cpu_vague', 'model'))
DATA = os.environ.get('JUDGE_DATA', HERE)          # judge keys, DB and the corpus-embedding cache (a volume in Docker)
os.makedirs(DATA, exist_ok=True)
DB = os.path.join(DATA, 'judge.db')
JUDGES_F = os.path.join(DATA, 'judges.json')
PAGE = os.path.join(HERE, 'static', 'index.html')

T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))
QA = T['qa']; DOC = [i for i, r in enumerate(QA) if r[0]]
import sys; sys.path.insert(0, ROOT)
from qfuse import Fuser          # E31: model cosine + 2-gram fused by RRF (colloquial @1 0.816 -> 0.874)
FUSE = Fuser(QA, DOC)

app = FastAPI(docs_url=None, redoc_url=None)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
# the claude.ai artifact build calls this API cross-origin (E35); judge writes still need X-Judge-Key
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['GET', 'POST'], allow_headers=['content-type', 'x-judge-key'])   # the page is ~9 MB of JSON data; ~1.5 MB gzipped
lock = threading.Lock()


def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute('create table if not exists rulings (id integer primary key, doc text, at real)')
    c.execute('create table if not exists reports (id integer primary key, doc text, at real, done integer default 0, ip text)')
    c.execute('create table if not exists verdicts (id integer primary key, doc text, at real)')
    # E41: Claude drafts for held questions (made by the operator's scheduled Claude session, never by a visitor's request); a judge approves or drops them
    c.execute("create table if not exists drafts (id integer primary key, doc text, at real, status text default 'open')")
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
SEM = {'model': None, 'E': None, 'err': None, 'model2': None, 'E2': None}


def encode_corpus(path, tag):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(path, device='cpu')
    cache = os.path.join(DATA, f'corpus_emb{tag}.npy'); stamp = os.path.join(DATA, f'corpus_emb{tag}.stamp')
    key = f"{os.path.getmtime(path)}|{len(DOC)}"
    if os.path.exists(cache) and os.path.exists(stamp) and open(stamp).read() == key:
        E = np.load(cache)
    else:
        t0 = time.time(); E = m.encode([QA[i][1] for i in DOC], normalize_embeddings=True, batch_size=64, show_progress_bar=False)
        np.save(cache, E); open(stamp, 'w').write(key); print(f'corpus{tag} encoded in {time.time() - t0:.0f}s')
    return m, E.astype(np.float32)


def load_model():
    try:
        if not os.path.exists(MODEL):
            SEM['err'] = f'model not found: {MODEL}'; print(SEM['err']); return
        m, E = encode_corpus(MODEL, '')
        if MODEL2 != 'none' and os.path.exists(MODEL2):
            try:
                m2, E2 = encode_corpus(MODEL2, '_2'); SEM.update(model2=m2, E2=E2); print('second retriever ready', MODEL2)
            except Exception as e:
                print('second retriever skipped', e)
        SEM.update(model=m, E=E); print('semantic search ready', E.shape)
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
    return {'ready': True, 'hits': fused_hits(q, k * 3)}


def fused_hits(q, k):
    # the server's retrieval (both models + 2-gram, RRF) — also the evidence search of the AI opinion (E51)
    v = SEM['model'].encode([q], normalize_embeddings=True, show_progress_bar=False)[0]
    s = SEM['E'] @ v
    extra = [SEM['E2'] @ SEM['model2'].encode([q], normalize_embeddings=True, show_progress_bar=False)[0]] if SEM['model2'] is not None else []
    return FUSE.hits(q, s, k, extra)


# ---------------- rulings & reports ----------------
def clean_doc(d):
    keep = ('card', 'others', 'unit', 'q', 'neg', 'it', 'slots', 'ans', 'src', 'agreed', 'summary', 'note', 'reporter', 'reported_at')
    d = {k: d.get(k) for k in keep if k in d}
    # E48: ans 1/0 = yes/no ruling; ans None = explanation ruling (the confirmed answer is the summary text itself)
    if not isinstance(d.get('card'), str) or not isinstance(d.get('q'), str) or d.get('ans') not in (0, 1, None)             or (d.get('ans') is None and not str(d.get('summary') or '').strip()):
        raise HTTPException(400, 'bad ruling')
    d.setdefault('ans', None)
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


def clean_verdict(d):
    # every verdict the page shows (E36): the question, the cards, the level and the top precedents
    if not isinstance(d, dict) or not str(d.get('q', '')).strip(): raise HTTPException(400, 'bad verdict')
    top = [{'card': str(t.get('card', ''))[:40], 'q': str(t.get('q', ''))[:1000], 'y': t.get('y')} for t in (d.get('top') or [])[:3] if isinstance(t, dict)]
    return {'q': str(d['q'])[:1000], 'cards': [str(x)[:40] for x in (d.get('cards') or [])][:10], 'level': str(d.get('level', ''))[:20],
            'ans': d.get('ans') if d.get('ans') in (0, 1, None) else None, 'top': top, 'at': str(d.get('at', ''))[:40]}


@app.post('/api/verdicts')
async def add_verdict(req: Request):
    body = await req.json()
    items = body if isinstance(body, list) else [body]
    if len(items) > 50: raise HTTPException(400, 'too many')
    ids = []
    with lock, db() as c:
        for it in items:
            d = clean_verdict(it); d['saved_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
            ids.append(c.execute('insert into verdicts (doc, at) values (?, ?)', (json.dumps(d, ensure_ascii=False), time.time())).lastrowid)
    return {'ids': ids}


@app.get('/api/verdicts')
def verdicts(req: Request):
    if not judge_of(req): raise HTTPException(403, 'judge key required')
    with lock, db() as c:
        return [{**json.loads(r['doc']), 'id': r['id']} for r in c.execute('select * from verdicts order by id')]


# ---------------- Claude drafts (E41) ----------------
@app.get('/api/drafts')
def drafts(req: Request):
    if not judge_of(req): raise HTTPException(403, 'judge key required')
    with lock, db() as c:
        return [{**json.loads(r['doc']), 'id': r['id']} for r in c.execute("select * from drafts where status='open' order by id")]


@app.post('/api/drafts/{did}/approve')
async def draft_approve(did: int, req: Request):
    # the judge may correct the answer or the summary; the ruling keeps src 'claude' so Claude-free measurements can leave it out
    j = judge_of(req)
    if not j: raise HTTPException(403, 'judge key required')
    b = await req.json() if (await req.body()) else {}
    with lock, db() as c:
        r = c.execute("select doc from drafts where id=? and status='open'", (did,)).fetchone()
        if not r: raise HTTPException(404, 'no such open draft')
        d = json.loads(r['doc'])
        orig = d.get('ans')
        for k in ('ans', 'summary', 'note'):
            if k in b and b[k] is not None or k == 'ans' and 'ans' in b: d[k] = b[k]
        # agreed: the judge kept Claude's answer (same yes/no, or both explanation) — for measuring draft accuracy
        doc = clean_doc({**d, 'src': 'claude', 'agreed': d.get('ans') == orig})
        doc.update(by=j, at=time.strftime('%Y-%m-%dT%H:%M:%S'), drafted_at=d.get('drafted_at', ''), origin='draft')
        if b.get('reviewed') == 'claude': doc['review'] = 'claude-rec'   # E49: judge applied a Claude review recommendation (bulk)
        rid = c.execute('insert into rulings (doc, at) values (?, ?)', (json.dumps(doc, ensure_ascii=False), time.time())).lastrowid
        c.execute("update drafts set status='approved' where id=?", (did,))
        if d.get('report_id'): c.execute('update reports set done=1 where id=?', (d['report_id'],))
        return {'ruling': rid}


@app.post('/api/drafts/{did}/drop')
def draft_drop(did: int, req: Request):
    if not judge_of(req): raise HTTPException(403, 'judge key required')
    with lock, db() as c:
        c.execute("update drafts set status='dropped' where id=? and status='open'", (did,))
    return {'ok': True}


# ---------------- AI opinion (E51, user decision 2026-10-23): Claude's reference opinion on request, shown as 「AI 의견 · 비공식」 ----------------
def insert_draft(d):
    d = {**d, 'kind': 'ai', 'drafted_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    with lock, db() as c:
        c.execute('insert into drafts (doc, at) values (?, ?)', (json.dumps(d, ensure_ascii=False), time.time()))


try:
    sys.path.insert(0, HERE)
    from ai_opinion import register as register_ai
    register_ai(app, dict(db_path=DB, QA=QA, search=lambda q, k: [h['i'] for h in fused_hits(q, k)] if SEM['model'] is not None else [],
                          cards={c['no']: c for c in json.load(open(os.path.join(ROOT, 'cards.json'), encoding='utf-8'))},
                          rules=json.load(open(os.path.join(ROOT, 'rules2.json'), encoding='utf-8'))['rules'], queue_draft=insert_draft))
except Exception as e:
    print('AI opinion not available', e)


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
    return {'semantic': SEM['model'] is not None, 'retrievers': 1 + (SEM['model2'] is not None), 'err': SEM['err'], 'qa': len(DOC)}


if __name__ == '__main__':
    judges()
    uvicorn.run(app, host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 8787)))
