import collections, glob, json, math, re
W = 'C:/Users/Daewonmedia/aegis_q2s/'
N = 'C:/Users/Daewonmedia/card_effects_next/'
it = {str(json.loads(l)['id']): json.loads(l) for l in open(N + 'train/data_next/yesno_test.jsonl', encoding='utf-8')}
items = {}
for i in range(1, 8):
    for x in json.load(open(W + f'out/batch{i:02d}.json', encoding='utf-8')):
        items[str(x['id'])] = x
held = set()
for i in range(1, 8):
    held |= {str(x['id']) for x in json.load(open(W + f'in/batch{i:02d}.json', encoding='utf-8'))}
print('held', len(held), 'items', len(items), 'missing', len(held - set(items)), 'extra', len(set(items) - held))
R = json.load(open(W + 'out/run_all.json', encoding='utf-8'))
r2 = {str(x['id']): x for x in json.load(open('C:/Users/Daewonmedia/card_effects/paper/results/testT_r2.json', encoding='utf-8'))['rows']}


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


rows = []
bad = collections.Counter()
for k, x in items.items():
    if k not in held or x.get('status') != 'ok' or not x.get('job'):
        continue
    o = R.get(k)
    if o is None or 'error' in o:
        bad['engine error'] += 1
        rows.append({'id': k, 'state': 'error', 'err': (o or {}).get('error', 'no result')[:120]})
        continue
    y = x['verdict']['yes_if']
    cs = y.get('all') or y.get('any') or []
    try:
        rs = [cond(c, o) for c in cs]
    except Exception as e:
        bad['verdict error'] += 1
        rows.append({'id': k, 'state': 'error', 'err': repr(e)[:120]})
        continue
    if not cs:
        bad['empty verdict'] += 1
        continue
    pred = int(all(rs) if 'all' in y else any(rs))
    expected_rej = {c['i'] for c in cs if c['op'] in ('step_rejected', 'step_ok')}
    rej = [n for n, s in enumerate(o['steps']) if not s['ok'] and n not in expected_rej]
    gold = int(it[k]['label'])
    rows.append({'id': k, 'card': it[k]['card'], 'state': 'run', 'pred': pred, 'gold': gold, 'ok': int(pred == gold), 'unsure': bool(x.get('unsure')), 'rej': bool(rej), 'r2_p': r2[k]['p'] if k in r2 else None, 'note': x.get('note', '')})


def rep(name, r):
    k = sum(x['ok'] for x in r)
    ye = [x for x in r if x['pred']]
    no = [x for x in r if not x['pred']]
    print(name, f'{k}/{len(r)}', round(k / len(r), 3) if r else None, wilson(k, len(r)), 'pred yes', sum(x['ok'] for x in ye), len(ye), 'pred no', sum(x['ok'] for x in no), len(no))


run = [x for x in rows if x['state'] == 'run']
print('converted', len([x for x in items.values() if x.get('status') == 'ok']), 'bad', dict(bad))
rep('primary (no rej, not unsure)', [x for x in run if not x['rej'] and not x['unsure']])
rep('no rej', [x for x in run if not x['rej']])
rep('all run', run)
rep('unsure no rej', [x for x in run if not x['rej'] and x['unsure']])
T = .9873
a = [x for x in run if x['r2_p'] is not None and max(x['r2_p'], 1 - x['r2_p']) >= T and not x['rej']]
print('R2 answered overlap', len(a), 'agree', sum(x['pred'] == (x['r2_p'] >= .5) for x in a), 'aegis ok', sum(x['ok'] for x in a), 'r2 ok', sum((x['r2_p'] >= .5) == x['gold'] for x in a))
for x in run:
    if not x['rej'] and not x['unsure'] and not x['ok']:
        print('WRONG', x['id'], x['card'], 'gold', x['gold'], x['note'][:120])
json.dump(rows, open(W + 'scored.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
