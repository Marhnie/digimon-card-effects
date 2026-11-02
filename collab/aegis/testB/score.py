import collections, json, math, re
W = 'C:/Users/Daewonmedia/aegis_q2s/'
B = 'C:/Users/Daewonmedia/card_effects_bt25jp/'
it = {str(json.loads(l)['id']): json.loads(l) for l in open(B + 'train/data_bt25/yesno_test.jsonl', encoding='utf-8')}
D = json.load(open(B + 'net/tdec_bt25.json'))
QA = json.load(open(B + 'test_data4.json', encoding='utf-8'))['qa']
page = {str(d['i']): d for d in D}
items = {}
for i in range(11, 16):
    for x in json.load(open(W + f'out/batch{i}.json', encoding='utf-8')):
        items[str(x['id'])] = x
print('items', len(items), 'missing', len(set(page) - set(items)))
R = json.load(open(W + 'out/runB.json', encoding='utf-8'))
q = {str(x['id']): x for x in json.load(open(B + 'jpbt25/r2_official.json', encoding='utf-8'))['rows']}


def cmp(a, op, b):
    return {'==': a == b, '<': a < b, '>': a > b, '<=': a <= b, '>=': a >= b}[op]


def cond(c, o):
    op = c['op']
    log = o['log']
    sd = o.get(c.get('side', 'you'), {})
    if op == 'log_has':
        return any(re.search(c['re'], l) for l in log)
    if op == 'log_not':
        return not any(re.search(c['re'], l) for l in log)
    if op == 'before':
        a = [n for n, l in enumerate(log) if re.search(c['a'], l)]
        b = [n for n, l in enumerate(log) if re.search(c['b'], l)]
        return bool(a and b and a[0] < b[0])
    if op == 'step_ok':
        return o['steps'][c['i']]['ok']
    if op == 'step_rejected':
        return not o['steps'][c['i']]['ok']
    if op == 'memory':
        return cmp(o.get('memory'), c['cmp'], c['n'])
    if op == 'field_count':
        return cmp(len(sd['field']), c['cmp'], c['n'])
    if op in ('stack_size', 'dp'):
        f = sd['field']
        if c['idx'] >= len(f):
            return False
        return cmp(len(f[c['idx']]['cards']) if op == 'stack_size' else f[c['idx']]['dp'], c['cmp'], c['n'])
    if op in ('hand_count', 'trash_count'):
        return cmp(len(sd[op.split('_')[0]]), c['cmp'], c['n'])
    if op == 'security_count':
        return cmp(sd['security'], c['cmp'], c['n'])
    if op in ('hand_has', 'trash_has'):
        return c['card'] in sd[op.split('_')[0]]
    if op == 'field_has':
        return any(c['card'] in s['cards'] for s in sd['field'])
    raise ValueError(op)


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    c = (p + z * z / 2 / n) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / 4 / n / n) / (1 + z * z / n)
    return round(c - h, 3), round(min(c + h, 1), 3)


def group(y, o):
    cs = y.get('all') if isinstance(y, dict) and 'all' in y else (y.get('any') if isinstance(y, dict) else y) or []
    rs = [cond(c, o) for c in cs]
    return (all(rs) if not (isinstance(y, dict) and 'any' in y) else any(rs)), cs


rows = []
bad = collections.Counter()
for k, x in items.items():
    if k not in page or x.get('status') != 'ok' or not x.get('job'):
        continue
    o = R.get(k)
    if o is None or 'error' in o:
        bad['engine error'] += 1
        continue
    try:
        pred, cs = group(x['verdict']['yes_if'], o)
        ctl = x.get('control') or x['verdict'].get('control') or []
        ctrl_ok = group(ctl, o)[0] if ctl else None
    except Exception as e:
        bad[repr(e)[:50]] += 1
        continue
    declared = {c.get('i') for c in cs if c['op'] in ('step_ok', 'step_rejected')} | {c.get('i') for c in (ctl if isinstance(ctl, list) else []) if c.get('op') in ('step_ok', 'step_rejected')}
    rej = [n for n, s in enumerate(o['steps']) if not s['ok'] and n not in declared]
    gold = QA[int(k)][8]
    rows.append({'id': k, 'card': it[k]['card'], 'held': not page[k]['by'], 'pred': int(pred), 'gold': gold, 'ok': int(pred == gold), 'unsure': bool(x.get('unsure')), 'rej': bool(rej), 'ctrl': ctrl_ok, 'q15': q[k]['p'] if k in q else None, 'note': x.get('note', '')})


def rep(name, r):
    k = sum(x['ok'] for x in r)
    ye = [x for x in r if x['pred']]
    no = [x for x in r if not x['pred']]
    print(name, f'{k}/{len(r)}', round(k / len(r), 3) if r else None, wilson(k, len(r)), 'yes', sum(x['ok'] for x in ye), len(ye), 'no', sum(x['ok'] for x in no), len(no))


print('converted', sum(x.get('status') == 'ok' for x in items.values() if True), 'bad', dict(bad), 'held converted', sum(1 for x in rows if x['held']))
P = [x for x in rows if not x['rej'] and x['ctrl'] is not False and not x['unsure']]
rep('primary all', P)
rep('primary held', [x for x in P if x['held']])
v = [x for x in rows if not x['rej'] and x['ctrl'] is not False]
rep('valid all', v)
rep('valid held', [x for x in v if x['held']])
rep('unsure valid', [x for x in v if x['unsure']])
rep('all run', rows)
print('ctrl false', sum(x['ctrl'] is False for x in rows), 'no control', sum(x['ctrl'] is None for x in rows), 'rej', sum(x['rej'] for x in rows))
h = [x for x in v if x['held'] and x['q15'] is not None]
print('q15 same held', sum((x['q15'] >= .5) == bool(x['gold']) for x in h), len(h))
pd = [x for x in v if not x['held']]
print('agree page', sum(x['pred'] == page[x['id']]['ans'] for x in pd), len(pd))
for x in P:
    if not x['ok']:
        print('WRONG', x['id'], x['card'], 'held', x['held'], 'gold', x['gold'], x['note'][:130])
json.dump(rows, open('C:/Users/Daewonmedia/aegis_private/scoredB.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
