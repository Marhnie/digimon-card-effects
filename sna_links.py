"""E45: link methods for the effect network, compared as judging evidence on the time split (honest half split).
Each method returns, for a newest-product yes/no question, weighted older Q&A; the answer is their weighted vote.
A threshold (margin, top weight) is chosen on one half of the newest products (acc >= TARGET) and measured on the other.
Also counted: decisions on questions the page does not decide yet (net/tdec_full.json from tests/tdec.js).
Methods
  eff     : undirected effect similarity (the current SNA links, q links left out)
  trig    : same trigger condition (유발 키 / 타이밍) + same asked thing + situation overlap
  inter   : DIRECTED interaction — an act of one involved effect causes the trigger event of another
            (A 「소멸」 -> B 「소멸 시」); Q&A with the same (act -> event) signature
  clause  : shared rule clauses (rare ones weigh more)
  a+b     : union of two methods' evidence
  python sna_links.py [methods]  -> paper/results/sna_links.json
"""
import json, re, sys, math, collections, os
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']; U = T['units']; ST = T['st']; CARDS = T['cards']
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}; HALF = [{'BT22', 'EX9', 'ST21'}, {'BT23', 'BT24', 'EX10', 'ST22'}]
TARGET = float(os.environ.get('TARGET', '0.97'))
prod = lambda c: (re.match(r'([A-Z]+\d*)-', c or '') or [None, ''])[1]
nrm = lambda s: re.sub(r'[\s:：・·\-–—「」『』()（）\[\].,!?~]', '', s or '')
bg = lambda s: (lambda t: {t[i:i + 2] for i in range(len(t) - 1)})(re.sub(r'\s+', '', s))


def tpl(s):
    for _ in range(3): s = re.sub(r'「[^「」]*」', 'X', s)
    return re.sub(r'\d+', 'N', re.sub(r'[A-Z]{1,3}\d{0,2}-\d{2,3}', 'X', s))


YN = [i for i, r in enumerate(QA) if r[0] and r[8] >= 0 and r[3] is not None and r[3] >= 0]
pool = [i for i in YN if prod(QA[i][0]) not in NEW]; test = [i for i in YN if prod(QA[i][0]) in NEW]
TB = {i: bg(tpl(QA[i][1])) for i in YN}
simT = lambda a, b: len(TB[a] & TB[b]) / (len(TB[a] | TB[b]) or 1)
jac = lambda a, b: len(set(a) & set(b)) / (len(set(a) | set(b)) or 1)
al = lambda j, i: QA[j][8] ^ (QA[j][9] ^ QA[i][9])
DEC = {d['i']: d for d in json.load(open('net/tdec_full.json'))} if os.path.exists('net/tdec_full.json') else {}

# ---- units per card, card names mentioned in a question ----
by_card = collections.defaultdict(list)
for u, r in enumerate(U): by_card[r[0]].append(u)
NAMES = collections.defaultdict(list)
for no, c in CARDS.items():
    k = nrm(c[0])
    if len(k) >= 3: NAMES[k].append(no)
KEYS = sorted(NAMES, key=len, reverse=True)


def mentioned(i):
    s = nrm(QA[i][1]); own = nrm(CARDS.get(QA[i][0], [''])[0]); out = []; used = [0] * len(s)
    for k in KEYS:
        p = s.find(k)
        if p < 0 or any(used[p:p + len(k)]): continue
        for x in range(p, p + len(k)): used[x] = 1
        if k != own and k not in own: out.append(k)
    return out


# ---- directed interaction: act -> trigger events it can cause ----
CAUSE = {'등장': {'등장함', '【등장 시】'}, '배틀 에어리어에 놓기': {'등장함', '놓임'}, '진화': {'진화함', '【진화 시】'}, '부화': {'등장함'},
         '소멸': {'소멸함', '【소멸 시】', '벗어남', '상대 디지몬 소멸시킴'}, 'DP 감소': {'소멸함', '【소멸 시】', '벗어남'},
         '파기': {'파기됨', '벗어남'}, '진화원 제거': {'파기됨'}, '퇴화': {'파기됨'}, '키워드 실행: 퇴화': {'파기됨'},
         '덱으로 되돌림': {'벗어남', '되돌아감'}, '패로 회수': {'벗어남', '되돌아감'}, '진화원에 놓기': {'놓임', '벗어남'},
         '레스트': {'레스트함'}, '액티브': {'액티브가 됨'}, '시큐리티 제거': {'줄어듦'}, '시큐리티 추가': {'늘어남'},
         '옵션 사용': {'사용함'}, '링크': {'링크함', '【링크 시】'}, '추가 어택': {'어택함', '【어택 시】'}, '강제 어택': {'어택함', '【어택 시】'},
         '어택 대상 변경': {'어택 대상 변경됨'}, '키워드 실행: 블래스트 진화': {'진화함', '【진화 시】'},
         '키워드 실행: 블래스트 조그레스': {'진화함', '【진화 시】'}}


def acts(u):
    s = ST[u]
    return {a.strip() for st in s[4] for a in st[0].split('/') if a.strip()} if s else set()


def events(u):
    s = ST[u]
    return ({k.split(' · ')[-1] for k in s[1] if not k.startswith('【')} | {k for k in s[1] if k.startswith('【')}) if s else set()


def inter_sig(i):
    u = QA[i][3]; inv = [u] + [v for k in mentioned(i) for no in NAMES[k][:3] for v in by_card[no]]
    sig = set()
    for x in inv:
        for y in inv:
            if x == y and len(inv) > 1: continue
            for a in acts(x):
                for e in CAUSE.get(a, set()) & events(y): sig.add((a, e))
    return sig


# ---- effect-similarity network (current SNA, q links out) ----
NET = json.load(open('net/effect_sna.json', encoding='utf-8')); U3 = json.load(open('units3.json', encoding='utf-8'))
byct = {(n['card'], n['text']): n['k'] for n in NET['nodes']}
node = lambda u: byct.get((U3[u]['card'], U3[u]['text'])) if 0 <= u < len(U3) else None
adj = collections.defaultdict(dict)
for a, b, _, _, why in NET['links']:
    sc = [int(w[1:]) / 100 for w in why.split(',') if w and w[0] != 'q']
    if sc:
        s = 1 - math.prod(1 - v for v in sc); adj[a][b] = s; adj[b][a] = s

# ---- clauses ----
cl = lambda i: set(U[QA[i][3]][11]) | ({QA[i][4]} if QA[i][4] else set())
MENT = {}
def cl2(i):
    if i not in MENT: MENT[i] = cl(i) | {r for k in mentioned(i) for no in NAMES[k][:3] for v in by_card[no] for r in U[v][11]}
    return MENT[i]
DF = collections.Counter(c for j in pool for c in cl(j)); NP = len(pool)
idf = lambda c: math.log((NP + 1) / (DF[c] + 1))

pool_by_it = collections.defaultdict(list)
for j in pool: pool_by_it[QA[j][6]].append(j)
SIG = {i: inter_sig(i) for i in YN}
TRG = {i: events(QA[i][3]) for i in YN}
NODE = {i: node(QA[i][3]) for i in YN}


def cands(i, m):
    c = pool_by_it.get(QA[i][6], [])
    out = []
    if m == 'eff':
        k = NODE[i]
        if k is None: return []
        nb = {k: 1.0, **{x: s for x, s in adj[k].items() if s >= 0.7}}
        out = [(nb[NODE[j]] * (0.5 + jac(QA[i][7], QA[j][7])), j) for j in c if NODE[j] in nb]
    elif m == 'trig':
        t = TRG[i]
        if not t: return []
        out = [(jac(t, TRG[j]) * jac(QA[i][7], QA[j][7]), j) for j in c if t & TRG[j]]
    elif m == 'inter':
        s = SIG[i]
        if not s: return []
        out = [(jac(s, SIG[j]) * (0.3 + jac(QA[i][7], QA[j][7])), j) for j in c if s & SIG[j]]
    elif m in ('clause', 'clause2', 'rare'):
        f = cl2 if m == 'clause2' else cl
        ci = f(i)
        if m == 'rare': ci = {x for x in ci if idf(x) >= 2.0}
        wi = sum(idf(x) for x in ci) or 1
        out = [(sum(idf(x) for x in ci & f(j)) / wi * (0.3 + jac(QA[i][7], QA[j][7])), j) for j in c if ci & f(j)]
    return [(w, j) for w, j in out if w > 0]


def decide(i, m, textw):
    c = [x for mm in m.split('+') for x in cands(i, mm)]
    if not c: return None
    c = [(w * (textw + simT(i, j)), j) for w, j in c]
    c.sort(reverse=True); c = c[:15]
    yes = sum(w for w, j in c if al(j, i)); no = sum(w for w, j in c if not al(j, i))
    if yes + no == 0: return None
    ans = int(yes >= no)
    return {'ans': ans, 'm': abs(yes - no) / (yes + no), 'top': c[0][0], 'n': len(c), 'ok': int(ans == QA[i][8]),
            'half': 0 if prod(QA[i][0]) in HALF[0] else 1, 'und': i in DEC and not DEC[i]['by'], 'i': i}


def honest(rows):
    out = []
    if os.environ.get('UND'): rows = [r for r in rows if r['und']]
    for a, b in ((0, 1), (1, 0)):
        ra = [r for r in rows if r['half'] == a]; best = None
        for mt in (0.5, 0.7, 0.8, 0.9, 0.95, 1.0):
            for tt in (0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5):
                s = [r for r in ra if r['m'] >= mt and r['top'] >= tt]
                if len(s) >= int(os.environ.get('MINN', '10')) and sum(r['ok'] for r in s) / len(s) >= TARGET and (best is None or len(s) > best[2]): best = (mt, tt, len(s))
        ev = [r for r in rows if best and r['half'] == b and r['m'] >= best[0] and r['top'] >= best[1]]
        un = [r for r in ev if r['und']]
        out.append({'rule': best, 'n': len(ev), 'ok': sum(r['ok'] for r in ev), 'new_on_undecided': len(un), 'new_ok': sum(r['ok'] for r in un)})
    return out


if __name__ == '__main__':
    print('questions with an interaction signature:', sum(1 for i in test if SIG[i]), '/', len(test),
          '| with mentioned cards:', sum(1 for i in test if mentioned(i)))
    res = {}
    methods = sys.argv[1].split(',') if len(sys.argv) > 1 else ['eff', 'trig', 'inter', 'clause', 'inter+trig', 'inter+clause']
    for m in methods:
        for tw in (0.0, 0.3):
            rows = [r for r in (decide(i, m, tw) for i in test) if r]
            h = honest(rows)
            key = f'{m}|tw{tw}'
            res[key] = {'answered': len(rows), 'acc_all': round(sum(r['ok'] for r in rows) / max(1, len(rows)), 3), 'honest': h}
            print(f'{m:<14} tw{tw}  answered {len(rows):3d} acc {res[key]["acc_all"]:.3f}  honest', h)
    json.dump(res, open('paper/results/sna_links.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
