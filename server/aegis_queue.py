"""E61: rules-engine opinion on held questions, for judges only. Runs entirely on this PC: a local clone of the open-source
Aegis engine (MIT, github.com/vinicius3333/aegis-digimon-tcg) in C:/Users/Daewonmedia/aegis_engine — no Aegis server, no network.

  python server/aegis_queue.py export NN    -> aegis_q2s/in/batchNN.json  (open drafts with yes/no-shaped questions; card texts, no answers)
  (a Claude session converts them per aegis_q2s/SPEC.md into aegis_q2s/out/batchNN.json, then `bash aegis_q2s/check.sh NN` runs the engine)
  python server/aegis_queue.py import NN    -> drafts get an `aegis` field {ans, unsure, note, log}; judges see it under the draft

Only valid runs are attached: every step the scenario did not declare was accepted and the control condition held (E60 rules).
Measured on test B (E60): 61/65 without the unsure flag, 28/36 with it — a reference for judges, not an automatic answer.
"""
import json, os, re, sqlite3, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('JUDGE_DATA', HERE)
Q2S = os.environ.get('AEGIS_Q2S', 'C:/Users/Daewonmedia/aegis_q2s')
ROOT = os.path.dirname(HERE)
db = sqlite3.connect(os.path.join(DATA, 'judge.db'))


def cmp(a, op, b):
    return {'==': a == b, '<': a < b, '>': a > b, '<=': a <= b, '>=': a >= b}[op]


def cond(c, o):
    op, log = c['op'], o['log']
    sd = o.get(c.get('side', 'you'), {})
    if op == 'log_has': return any(re.search(c['re'], l) for l in log)
    if op == 'log_not': return not any(re.search(c['re'], l) for l in log)
    if op == 'before':
        a = [n for n, l in enumerate(log) if re.search(c['a'], l)]
        b = [n for n, l in enumerate(log) if re.search(c['b'], l)]
        return bool(a and b and a[0] < b[0])
    if op == 'step_ok': return o['steps'][c['i']]['ok']
    if op == 'step_rejected': return not o['steps'][c['i']]['ok']
    if op == 'memory': return cmp(o.get('memory'), c['cmp'], c['n'])
    if op == 'field_count': return cmp(len(sd['field']), c['cmp'], c['n'])
    if op in ('stack_size', 'dp'):
        f = sd['field']
        if c['idx'] >= len(f): return False
        return cmp(len(f[c['idx']]['cards']) if op == 'stack_size' else f[c['idx']]['dp'], c['cmp'], c['n'])
    if op in ('hand_count', 'trash_count'): return cmp(len(sd[op.split('_')[0]]), c['cmp'], c['n'])
    if op == 'security_count': return cmp(sd['security'], c['cmp'], c['n'])
    if op in ('hand_has', 'trash_has'): return c['card'] in sd[op.split('_')[0]]
    if op == 'field_has': return any(c['card'] in s['cards'] for s in sd['field'])
    raise ValueError(op)


def group(y, o):
    anyof = isinstance(y, dict) and 'any' in y
    cs = (y.get('any') if anyof else y.get('all')) if isinstance(y, dict) else (y or [])
    rs = [cond(c, o) for c in cs or []]
    return (any(rs) if anyof else all(rs)), cs or []


def judge(x, o):
    """the E60 rule: None when the run is not valid (undeclared rejected step, failed control, engine error)"""
    if o is None or 'error' in o: return None
    pred, cs = group(x['verdict']['yes_if'], o)
    ctl = x.get('control') or x['verdict'].get('control') or []
    if ctl and not group(ctl, o)[0]: return None
    declared = {c.get('i') for c in list(cs) + list(ctl) if c.get('op') in ('step_ok', 'step_rejected')}
    if any(not s['ok'] for n, s in enumerate(o['steps']) if n not in declared): return None
    return int(pred)


def export(nn):
    C = {c['no']: c for c in json.load(open(os.path.join(ROOT, 'cards.json'), encoding='utf-8'))}
    out = []
    for did, d in db.execute("select id, doc from drafts where status='open' order by id"):
        d = json.loads(d)
        if d.get('aegis'): continue
        cards = [d.get('card')] + [x for x in (d.get('others') or '').split(',') if x]
        cards = [c for c in cards if c in C]
        if not cards: continue
        t = lambda no: ' / '.join(x for x in (C[no].get('상단 텍스트', ''), C[no].get('하단 텍스트', '')) if x)
        out.append({'id': f'd{did}', 'card': cards[0], 'card_name': C[cards[0]]['name'], 'card_text': t(cards[0]),
                    'others': [{'card': no, 'card_name': C[no]['name'], 'card_text': t(no)} for no in cards[1:]], 'question': d['q']})
    p = os.path.join(Q2S, 'in', f'batch{nn}.json')
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(out), 'questions ->', p)


def imp(nn):
    items = json.load(open(os.path.join(Q2S, 'out', f'batch{nn}.json'), encoding='utf-8'))
    runs = json.load(open(os.path.join(Q2S, 'out', f'run{nn}.json'), encoding='utf-8'))
    n = skip = 0
    for x in items:
        did = int(str(x['id']).lstrip('d'))
        row = db.execute("select doc from drafts where id=? and status='open'", (did,)).fetchone()
        if not row or x.get('status') != 'ok' or not x.get('job'): continue
        o = runs.get(str(x['id']))
        try: ans = judge(x, o)
        except Exception: ans = None
        if ans is None: skip += 1; continue
        d = json.loads(row[0])
        d['aegis'] = {'ans': ans, 'unsure': bool(x.get('unsure')), 'note': str(x.get('note', ''))[:500],
                      'log': [l[:200] for l in o['log'] if not l.startswith('Moved')][:30], 'at': time.strftime('%Y-%m-%dT%H:%M:%S')}
        db.execute('update drafts set doc=? where id=?', (json.dumps(d, ensure_ascii=False), did)); n += 1
    db.commit(); print(n, 'engine opinions attached,', skip, 'runs not valid')


if __name__ == '__main__':
    cmd, nn = (sys.argv[1:3] + ['', ''])[:2]
    if cmd == 'export' and nn: export(nn)
    elif cmd == 'import' and nn: imp(nn)
    else: print(__doc__)
