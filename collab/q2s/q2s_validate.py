import json, sys, os, re
H = os.path.dirname(os.path.abspath(__file__))
IDS = set(json.load(open(os.path.join(H, 'dcgo_ids.json'))))
REASONS = {'needs_choice', 'opp_turn', 'multi_card', 'hand_or_inherited', 'not_impl', 'other'}
OPS = {'log_has', 'log_not', 'field_count', 'stack_size', 'dp', 'hand_count', 'trash_count', 'security_count', 'hand_has', 'trash_has', 'field_has'}
CMP = {'==', '<', '>', '<=', '>='}
STEPS = {'play', 'digivolve', 'activate', 'attack', 'optional', 'pass'}


def cards_of(side):
    out = list(side.get('hand', [])) + list(side.get('trash', [])) + list(side.get('security', []))
    for st in side.get('field', []):
        out += st.get('cards', [])
    return out


def check(it):
    e = []
    if it.get('status') not in ('ok', 'unsupported'):
        return ['bad status']
    if it['status'] == 'unsupported':
        if it.get('reason') not in REASONS:
            e.append('bad reason')
        return e
    j = it.get('job')
    v = it.get('verdict')
    if not isinstance(j, dict) or not isinstance(v, dict):
        return ['missing job/verdict']
    for s in ('you', 'opp'):
        side = j.get(s, {})
        for c in cards_of(side):
            if c not in IDS:
                e.append('card not in DCGO: %s' % c)
        for st in side.get('field', []):
            if not st.get('cards'):
                e.append('empty stack')
    you = j.get('you', {})
    for st in j.get('steps', []):
        if st.get('do') not in STEPS:
            e.append('bad step %s' % st)
        if st.get('do') in ('play', 'digivolve') and st.get('card') not in you.get('hand', []):
            e.append('step card not in hand: %s' % st.get('card'))
        if st.get('do') in ('activate', 'attack', 'digivolve') and not (0 <= st.get('frame', -1) < len(you.get('field', []))):
            e.append('frame out of range: %s' % st)
    if not j.get('steps'):
        e.append('no steps')
    y = v.get('yes_if') or {}
    conds = y.get('all') if 'all' in y else y.get('any')
    if not conds:
        e.append('verdict needs yes_if.all or any')
    for c in conds or []:
        if c.get('op') not in OPS:
            e.append('bad op %s' % c)
            continue
        if c['op'].startswith('log'):
            try:
                re.compile(c['re'])
            except Exception:
                e.append('bad regex')
        elif 'cmp' in c and c['cmp'] not in CMP:
            e.append('bad cmp')
        if c['op'] in ('hand_has', 'trash_has', 'field_has') and c.get('card') not in IDS:
            e.append('verdict card not in DCGO: %s' % c.get('card'))
    return e


if __name__ == '__main__':
    bad = 0
    for f in sys.argv[1:]:
        d = json.load(open(f, encoding='utf-8'))
        for it in d:
            er = check(it)
            if er:
                bad += 1
                print(f, it.get('id'), er)
    print('problems:', bad)
