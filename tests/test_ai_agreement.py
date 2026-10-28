import json, os, sqlite3, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))
import ai_agreement as A

p = os.path.join(tempfile.mkdtemp(), 'j.db')
c = sqlite3.connect(p)
c.execute('create table ai_cache (key text primary key, doc text, at real)')
c.execute('create table ai_spend (id integer primary key, at real, ip text, usd real, key text)')
c.execute("create table drafts (id integer primary key, doc text, at real, status text default 'open')")
c.execute('create table rulings (id integer primary key, doc text, at real)')


def op(q, cards, model, ans, conf):
    c.execute('insert into ai_cache values (?,?,?)', (f'{q}|{cards}|{model}', json.dumps({'ans': ans, 'confidence': conf, 'model': model}), 0))


op('q1', 'A-1', 'm1', 1, 'high'); op('q2', 'A-1', 'm1', 0, 'high'); op('q3', 'A-1', 'm1', None, 'low'); op('q4', 'B-2,C-3', 'm1', 1, 'medium')
c.execute("insert into ai_spend (at, ip, usd, key) values (0,'x',0.02,'k')")
for st in ('open', 'approved', 'approved', 'dropped'):
    c.execute('insert into drafts (doc, at, status) values (?,?,?)', (json.dumps({'kind': 'ai'}), 0, st))


def rl(q, card, others, agreed):
    c.execute('insert into rulings (doc, at) values (?,?)', (json.dumps({'q': q, 'card': card, 'others': others, 'origin': 'draft', 'src': 'claude',
                                                                       'note': 'AI 의견(이용자 요청)', 'agreed': agreed}), 0))


rl('q1', 'A-1', '', True); rl('q2', 'A-1', '', False); rl('q4', 'B-2', 'C-3', True); rl('zz', 'A-1', '', True)
c.commit(); c.close()
r = A.report(p)
assert r['opinions'] == 4 and r['unsure_share'] == 0.25 and r['drafts'] == {'open': 1, 'approved': 2, 'dropped': 1}, r
assert r['judge_reviewed_with_answer'] == 3 and r['agree'] == 2 and r['rulings_unmatched_to_cache'] == 1 and r['spend_usd'] == 0.02, r
hi = [x for x in r['by_model_confidence'] if x['confidence'] == 'high'][0]
assert hi['reviewed'] == 2 and hi['agree'] == 1
print('ok', r['agree_rate'], r['agree_ci95'])
