"""Aggregate the question->scenario->engine pipeline against the official gold answers.
usage: python -X utf8 q2s_eval.py   (reads q2s/merged.json, jobs/q2s/*.out.json, pilot_set.json)"""
import json, os, re, math, collections
H = os.path.dirname(os.path.abspath(__file__))
items = json.load(open(os.path.join(H, 'q2s', 'merged.json'), encoding='utf-8'))
pilot = {i['id']: i for i in json.load(open(os.path.join(H, 'pilot_set.json'), encoding='utf-8'))['items']}


def norm_log(out):
    return [re.sub(r'\n+', ' / ', l.strip('\n')).strip() for l in out.get('log', [])]


def cmp(a, op, b):
    return {'==': a == b, '<': a < b, '>': a > b, '<=': a <= b, '>=': a >= b}[op]


def cond(c, out, log):
    op = c['op']
    side = out.get(c.get('side', 'you'), {}) if 'side' in c else {}
    if op == 'log_has':
        return any(re.search(c['re'], l) for l in log)
    if op == 'log_not':
        return not any(re.search(c['re'], l) for l in log)
    if op == 'field_count':
        return cmp(len(side.get('field', [])), c['cmp'], c['n'])
    if op in ('stack_size', 'dp'):
        f = side.get('field', [])
        if c['idx'] >= len(f):
            return False
        v = len(f[c['idx']]['cards']) if op == 'stack_size' else f[c['idx']]['dp']
        return cmp(v, c['cmp'], c['n'])
    if op in ('hand_count', 'trash_count'):
        return cmp(len(side.get(op.split('_')[0], [])), c['cmp'], c['n'])
    if op == 'security_count':
        return cmp(side.get('security', 0), c['cmp'], c['n'])
    if op in ('hand_has', 'trash_has'):
        return c['card'] in side.get(op.split('_')[0], [])
    if op == 'field_has':
        return any(c['card'] in s['cards'] for s in side.get('field', []))
    raise ValueError(op)


def verdict(it, out):
    log = norm_log(out)
    y = it['verdict']['yes_if']
    conds = y['all'] if 'all' in y else y['any']
    rs = [cond(c, out, log) for c in conds]
    return '네' if (all(rs) if 'all' in y else any(rs)) else '아니요'


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


rows = []
reasons = collections.Counter()
for it in items:
    g = pilot[it['id']]['gold']
    r = {'id': it['id'], 'card': pilot[it['id']]['card'], 'gold': g, 'status': it['status'], 'reason': it.get('reason'), 'note': it.get('note', '')}
    reasons[(it['status'], it.get('reason'))] += 1
    if it['status'] == 'ok':
        p = os.path.join(H, 'jobs', 'q2s', 'q%s.out.json' % it['id'])
        if not os.path.exists(p):
            r['run'] = 'no_output'
        else:
            out = json.load(open(p, encoding='utf-8'))
            if out.get('fatal'):
                r['run'] = 'fatal:' + out['fatal'][:40]
            else:
                r['run'] = 'ok'
                r['pred'] = verdict(it, out)
                r['match'] = r['pred'] == g
                r['step_error'] = any('step error' in l for l in out.get('log', []))
    rows.append(r)

N = len(rows)
ok = [r for r in rows if r['status'] == 'ok']
ran = [r for r in ok if r.get('run') == 'ok']
hit = [r for r in ran if r['match']]
print('문항 %d' % N)
print('변환 가능(ok) %d (%.1f%%), unsupported %d' % (len(ok), 100 * len(ok) / N, N - len(ok)))
for (s, rs), n in sorted(reasons.items(), key=lambda x: -x[1]):
    print('  %s %s: %d' % (s, rs or '', n))
print('실행 성공 %d / %d, 실행 실패 %s' % (len(ran), len(ok), collections.Counter(r['run'] for r in ok if r.get('run') != 'ok')))
lo, hi = wilson(len(hit), len(ran))
print('DSL 판정 vs gold 일치 %d / %d = %.1f%% (Wilson 95%% %.1f–%.1f%%)' % (len(hit), len(ran), 100 * len(hit) / max(1, len(ran)), 100 * lo, 100 * hi))
print('  gold 분포(실행된 문항):', collections.Counter(r['gold'] for r in ran), ' 예측 분포:', collections.Counter(r['pred'] for r in ran))
print('  step error가 있었던 문항:', [r['id'] for r in ran if r['step_error']])
# Claude-less estimate: baseline phrase-similarity engine at conf>=0.8 (as measured on this set) + harness-covered items not already covered
base = {i for i, p in pilot.items() if p.get('engine_conf', 0) >= 0.80}
base_hit = sum(1 for i in base if pilot[i]['engine_guess'] == pilot[i]['gold'])
ran_ids = {r['id'] for r in ran}
extra = ran_ids - base
print('기존 문구 엔진 확신>=0.80: %d문항(%.1f%%) 정확도 %.1f%%' % (len(base), 100 * len(base) / N, 100 * base_hit / max(1, len(base))))
extra_hit = sum(1 for r in ran if r['id'] in extra and r['match'])
print('하네스가 추가로 답한 문항: %d (일치 %d)' % (len(extra), extra_hit))
tot = len(base) + len(extra)
tot_hit = base_hit + extra_hit
print('합산: Claude 없이 답 %d문항 (%.1f%%), 정확도 %.1f%%' % (tot, 100 * tot / N, 100 * tot_hit / max(1, tot)))
json.dump(rows, open(os.path.join(H, 'q2s', 'eval_rows.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('--- 불일치 목록')
for r in ran:
    if not r['match']:
        print(r['id'], r['card'], 'gold', r['gold'], 'pred', r['pred'], '|', r['note'][:110])
