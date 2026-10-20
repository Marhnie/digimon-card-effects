"""Question normalisation + frame decomposition for colloquial judge-helper questions (E31).

normalize(q)  -> question rewritten with the official wording (see qnorm_dict.json; build with qnorm_make_dict.py)
frame(qn)     -> {'cards', 'timing', 'slots', 'ask'}  = target card / effect timing / situation / what is asked
frame_bonus(fq, fd) -> additive score for a query frame vs a Q&A frame

Card names are resolved only against test_data4.json card names (qnorm_names.json). A truncated name is expanded
only when it is the unique prefix of one official name; ambiguous ones are left as typed.
"""
import json, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, 'qnorm_dict.json'), encoding='utf-8'))
NAMES = json.load(open(os.path.join(HERE, 'qnorm_names.json'), encoding='utf-8'))


def _rep(s):  # JS-style $1 -> python \g<1>
    return re.sub(r'\$(\d)', r'\\g<\1>', s)


PRE = [(re.compile(x['p']), _rep(x['r'])) for x in D['pre']]
RULES = [(re.compile(x['p']), _rep(x['r']), x.get('g', '')) for x in D['rules']]
GROUPS = {'num', 'timing', 'keyword', 'term', 'ending'}   # rule groups switched on (ablation / tuning)
SLOTS = [(a, b, re.compile(c)) for a, b, c in D['slots']]
ASK = [(a, re.compile(p)) for a, p in D['ask']]
W = D['weights']
NSET = set(NAMES)
VOCAB0 = set(json.load(open(os.path.join(HERE, 'qnorm_vocab.json'), encoding='utf-8')))
_STRIP = {n.replace(' ', ''): n for n in NAMES}
_BYLEN = sorted(_STRIP, key=lambda x: -len(x))
_PREFIX = {}
for _n in _STRIP:  # truncated forms (drop up to 4 trailing chars, min length 3) -> names
    for k in range(1, 5):
        if len(_n) - k >= 3:
            _PREFIX.setdefault(_n[:-k], set()).add(_n)


def clean(s):
    s = unicodedata.normalize('NFC', s or '')
    for p, r in PRE:
        s = p.sub(r, s)
    return s


def expand_names(s, vocab=None):
    """Expand truncated card names that are the unique prefix of one official name (hangul tokens, >=3 chars)."""
    def f(m):
        t = m.group(0)
        if t in _STRIP or t in VOCAB0 or (vocab and t in vocab):
            return t
        c = _PREFIX.get(t)
        if c and len(c) == 1:
            return _STRIP[next(iter(c))] if False else _STRIP[next(iter(c))]
        return t
    return re.sub(r'[가-힣]{3,}', f, s)


def normalize(q, names=True, vocab=None):
    s = clean(q)
    for p, r, g in RULES:
        if g in GROUPS:
            s = p.sub(r, s)
    if names:
        s = expand_names(s, vocab)
    return re.sub(r'\s+', ' ', s).strip()


def cards_in(s):
    t = s.replace(' ', '')
    found, used = [], [False] * len(t)
    for n in _BYLEN:
        if len(n) < 3:
            continue
        i = t.find(n)
        if i >= 0 and not any(used[i:i + len(n)]):
            found.append(_STRIP[n])
            for k in range(i, i + len(n)):
                used[k] = True
    return found


def frame(s):
    timing = sorted(set(re.findall(r'【[^】]+】|《[^》]+》', s)))
    slots = sorted({(a + ':' + b) for a, b, p in SLOTS if p.search(s)})
    ask = next((a for a, p in ASK if p.search(s)), '')
    return {'cards': cards_in(s), 'timing': timing, 'slots': slots, 'ask': ask}


def _j(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def frame_bonus(fq, fd, card_name=''):
    s = W['timing'] * _j(fq['timing'], fd['timing']) + W['slot'] * _j(fq['slots'], fd['slots'])
    if fq['ask'] and fq['ask'] == fd['ask']:
        s += W['ask']
    if fq['cards'] and (card_name in fq['cards'] or set(fq['cards']) & set(fd['cards'])):
        s += W['card']
    return s


def bigrams(s):
    t = re.sub(r'\s+', '', s)
    return {t[i:i + 2] for i in range(len(t) - 1)}


def jac(a, b):
    x = len(a & b)
    return x / ((len(a) + len(b) - x) or 1)


if __name__ == '__main__':
    import sys
    for q in sys.argv[1:] or ['샤인그레이몬 루인모드가 걸려있는데 파피몬 등장시키면 1드로 등장시효과 쓸수있어?']:
        n = normalize(q)
        print(n, json.dumps(frame(n), ensure_ascii=False))


_END = re.compile(r'(?:할 수 (?:있|없)|수 (?:있|없)|되|하|한|인|입|있|없)?(?:나요|습니까|ㅂ니까|니까|가요|까요|나여)\s*[?]?\s*$')
_STOP = re.compile(r'이 카드의|이 카드가|이 카드를|이 카드|이때,?|상황입니다\.?|경우')


def content(s):
    """Text used for the 2-gram overlap: the question ending (kept in frame['ask']) and filler words removed."""
    s = _STOP.sub(' ', s)
    return _END.sub('', s.strip())
