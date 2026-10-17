"""Bundle the v2 classification into one JSON blob for the test page."""
import json, re
import parse_fx as P
import link_fx as L   # re-runs linking (writes the same outputs)

U = json.load(open('units3.json', encoding='utf-8'))
QI = json.load(open('qa_items.json', encoding='utf-8'))
PATS = json.load(open('patterns.json', encoding='utf-8'))
CARDS = json.load(open('cards.json', encoding='utf-8'))
R = [r for r in json.load(open('rules2.json', encoding='utf-8'))['rules'] if r['l'] >= 0]

cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
qidx = {q['id']: i for i, q in enumerate(QI)}
data = {
    'cards': {c['no']: [re.sub(r'^\S+\s*', '', c['name']), c['type'], c['color']] for c in CARDS},
    'units': [[u['card'], u['where'], u['kind'], u['text'], u['ntext'] if u['ntext'] != u['text'] else 0, u['timing'], u['limit'], u['keywords'],
               u['types'], u['forms'], u['pattern'], u['rules'], [qidx[x] for x in u.get('qa', [])], u['tpl']] for u in U],
    'qa': [[q['card'] or '', cq(q['q']), cq(q['a']), q['unit'] if q['unit'] is not None else -1, q.get('rule') or '', q.get('how') or ''] for q in QI],
    'pats': {p['id']: [p['size'], p['types'], p['sub']] for p in PATS},
    'rules': {r['n']: r['t'] for r in R},
    # parser & mapping config so pasted text is analysed the same way as the card list
    'cfg': {
        'wording': [[a.pattern, re.sub(r'\\(\d)', r'$\1', b)] for a, b in P.WORDING],
        'actions': [[n, p.pattern] for n, p in P.ACTIONS],
        'forms': [[n, p.pattern] for n, p in P.FORMS],
        'actRule': L.ACTION_RULE, 'formRule': L.FORM_RULE, 'kindRule': L.KIND_RULE, 'whereRule': L.WHERE_RULE,
        'kwRule': {k: v for k, v in L.KW_RULE.items() if v}, 'timingRule': {t: L.timing_rule(t) for t in set(x for u in U for x in u['timing']) if L.timing_rule(t)},
    },
}
s = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
open('test_data.json', 'w', encoding='utf-8').write(s)
print(len(s))
