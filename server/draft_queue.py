"""E41: queue of held questions for Claude drafts -> judge approval. Free and within the terms: the operator's own
scheduled Claude session (Claude desktop app) writes the drafts in batches; visitors never call Claude.

  python server/draft_queue.py export [--max 15]   -> server/drafts_todo.json  (held verdicts + open reports, with card texts
                                                       and the nearest official Q&A from /api/search)
  (the scheduled Claude session reads drafts_todo.json and writes server/drafts_done.json:
     [{"key": ..., "ans": 1 | 0 | null, "summary": "...", "refs": ["BT1-001 Q...", ...]}])
  python server/draft_queue.py import              -> drafts table (status open); judges approve/drop them on the page
"""
import json, os, sqlite3, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DATA = os.environ.get('JUDGE_DATA', HERE)
TODO, DONE = os.path.join(HERE, 'drafts_todo.json'), os.path.join(HERE, 'drafts_done.json')
db = sqlite3.connect(os.path.join(DATA, 'judge.db'))
db.execute("create table if not exists drafts (id integer primary key, doc text, at real, status text default 'open')")
key = lambda q, card: (q or '').strip() + '|' + (card or '')


def known():
    ks = set()
    for t in ('rulings', 'drafts'):
        for (d,) in db.execute(f'select doc from {t}'):
            d = json.loads(d); ks.add(key(d.get('q'), d.get('card')))
    return ks


import re
AL = json.load(open(os.path.join(ROOT, 'aliases.json'), encoding='utf-8'))['alias'] if os.path.exists(os.path.join(ROOT, 'aliases.json')) else []
PART = r'(?:이랑|랑|으로|로|에서|에게|에|은|는|이|가|을|를|의|도|와|과|만|하고|vs)'
def dealias(q):
    for x in sorted(AL, key=lambda x: -len(x['a'])):
        q = re.sub(r'(^|[^가-힣])' + re.escape(x['a']) + r'(?=$|[^가-힣]|' + PART + r'(?![가-힣]))', lambda m: m.group(1) + x['to'], q)
    return q
_nrm = lambda s: re.sub(r'[\s:：・·\-–—「」『』()（）\[\].,!?~]', '', s or '')
def find_cards(q, T):
    names = {}
    for no, c in T['cards'].items():
        k = _nrm(c[0])
        if len(k) >= 3: names.setdefault(k, []).append(no)
    qa_n = {}
    for r in T['qa']: qa_n[r[0]] = qa_n.get(r[0], 0) + 1
    s = _nrm(q); used = [0] * len(s); out = []
    for k in sorted(names, key=len, reverse=True):
        p = s.find(k)
        if p < 0 or any(used[p:p + len(k)]): continue
        for x in range(p, p + len(k)): used[x] = 1
        nos = names[k]; m = re.search(r'(BT|EX|ST|P)?(\d{1,2})$', s[:p])
        if m:
            f = [n for n in nos if n.startswith((m.group(1) or 'BT') + str(int(m.group(2))) + '-')]
            nos = f or nos
        out.append((p, max(nos, key=lambda n: qa_n.get(n, 0))))
    return [no for _, no in sorted(out)]


FROM = sys.argv[sys.argv.index('--from') + 1] if '--from' in sys.argv else None


def export(mx):
    T = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8')); QA = T['qa']
    C = {c['no']: c for c in json.load(open(os.path.join(ROOT, 'cards.json'), encoding='utf-8'))}
    have, items = known(), []
    for (d,) in db.execute('select doc from verdicts order by id desc'):
        d = json.loads(d)
        if d.get('level') == 'pending' and d.get('cards'):
            items.append({'kind': 'held', 'q': d['q'], 'cards': d['cards']})
    for rid, d in db.execute('select id, doc from reports where done=0 order by id'):
        d = json.loads(d)
        items.append({'kind': 'report', 'report_id': rid, 'q': d['q'], 'cards': [d['card']] + [x for x in (d.get('others') or '').split(',') if x],
                      'reported_ans': d.get('ans'), 'reported_summary': d.get('summary')})
    if FROM:
        # E47: questions collected elsewhere (one per line, kept local) — community nicknames resolved, card names detected
        items = []
        for q in [l.strip() for l in open(FROM, encoding='utf-8') if l.strip()]:
            cards = find_cards(dealias(q), T)
            if cards: items.append({'kind': 'community', 'q': q, 'cards': cards})
    out, seen = [], set()
    for it in items:
        k = key(it['q'], it['cards'][0])
        if k in have or k in seen: continue
        seen.add(k)
        r = urllib.request.Request('http://127.0.0.1:8787/api/search', json.dumps({'q': it['q'], 'k': 5}).encode(), {'Content-Type': 'application/json'})
        try: hits = json.load(urllib.request.urlopen(r, timeout=60))['hits'][:5]
        except Exception: hits = []
        it['key'] = k
        it['card_texts'] = {no: {'name': C[no]['name'], 'text': C[no].get('상단 텍스트', ''), 'inherited': C[no].get('하단 텍스트', '')} for no in it['cards'] if no in C}
        it['nearest_official_qa'] = [{'card': QA[h['i']][0], 'q': QA[h['i']][1], 'a': QA[h['i']][2]} for h in hits]
        out.append(it)
        if len(out) >= mx: break
    json.dump(out, open(TODO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(out), 'to draft ->', TODO)


def imp():
    if not os.path.exists(DONE): sys.exit('no ' + DONE)
    todo = {x['key']: x for x in json.load(open(TODO, encoding='utf-8'))} if os.path.exists(TODO) else {}
    have, n = known(), 0
    for d in json.load(open(DONE, encoding='utf-8')):
        it = todo.get(d.get('key'))
        if not it or d['key'] in have: continue
        doc = {'card': it['cards'][0], 'others': ','.join(it['cards'][1:]), 'q': it['q'], 'ans': d.get('ans') if d.get('ans') in (0, 1) else None,
               'summary': str(d.get('summary', ''))[:1000], 'note': ' / '.join(d.get('refs') or [])[:1000], 'kind': it['kind'],
               'report_id': it.get('report_id'), 'drafted_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
        db.execute('insert into drafts (doc, at) values (?, ?)', (json.dumps(doc, ensure_ascii=False), time.time())); n += 1
    db.commit(); os.replace(DONE, DONE + '.imported')
    print(n, 'drafts added')


def review_import(paths):
    """E49: attach Claude review recommendations to open drafts (rec yes/no/ex/drop/human, rec_summary, rec_why); judges apply them"""
    n = 0
    for p_ in paths:
        for r in json.load(open(p_, encoding='utf-8')):
            row = db.execute("select doc from drafts where id=? and status='open'", (r['id'],)).fetchone()
            if not row or r.get('rec') not in ('yes', 'no', 'ex', 'drop', 'human'): continue
            d = json.loads(row[0]); d.update(rec=r['rec'], rec_summary=str(r.get('summary', ''))[:1000], rec_why=str(r.get('why', ''))[:300])
            db.execute('update drafts set doc=? where id=?', (json.dumps(d, ensure_ascii=False), r['id'])); n += 1
    db.commit(); print(n, 'recommendations attached')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'export': export(int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 15)
    elif cmd == 'import': imp()
    elif cmd == 'review-import': review_import(sys.argv[2:])
    else: print(__doc__)
