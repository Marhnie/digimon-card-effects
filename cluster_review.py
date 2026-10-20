"""효과 네트워크 세부 클러스터 점검 목록 (E30). 클러스터를 다시 계산하지 않고 net/effect_sna.json의 배정을 그대로 읽어
 - 클러스터마다 구성(분류·유발·처리)과 대표 효과 3개,
 - 클러스터 성격과 맞지 않는 효과(이상치)와 편입 원인
을 paper/results/cluster_review.md로 만든다.
이상치 기준: 효과의 「처리 행동」 또는 「유발 조건」이 그 클러스터에서 드문 것(처리 행동 비율 < 3% 또는 유발 조건 비율 < 3%; 작은 클러스터는 < 10%)
편입 원인: 이상치와 같은 클러스터 구성원을 잇는 링크의 이유 중 가장 센 것 (p 같은 처리 단계 · s 구조 유사 · t 같은 유발 조건 · q 같은 Q&A 쟁점 · c 같은 카드 · m 이름 언급)"""
import json, collections, math, re
N = json.load(open('net/effect_sna.json', encoding='utf-8'))
nodes, clusters, coarse = N['nodes'], N['clusters'], N['coarse']
co_of = {f: c for c in coarse for f in c['fine']}
mem = collections.defaultdict(list)
for n in nodes: mem[n['c']].append(n['k'])
nbr = collections.defaultdict(list)                           # node -> [(other, comps dict)]
for a, b, typ, w, comp in N['links']:
    d = {x[0]: int(x[1:]) for x in comp.split(',')}
    nbr[a].append((b, d)); nbr[b].append((a, d))
def parts(g):
    p = [x.strip() for x in g.split('|')]
    trig = next((x.split(':', 1)[1].strip() for x in p if x.startswith(('타이밍:', '유발 조건:'))), '(없음)')
    act = next((x.split(':', 1)[1].strip() for x in p if x.startswith('처리:')), '(없음)')
    return p[0], trig, act
P = {n['k']: parts(n['grp']) for n in nodes}
# 처리 행동 집합: 효과의 모든 처리 단계의 행동(struct2.json, (카드, 문구)로 짝) — 첫 행동만 보면 「A 그 후 퇴화」 같은 여러 단계 효과가 이상치로 잡힌다
S2 = json.load(open('struct2.json', encoding='utf-8'))
bykey = {}
for s_ in S2:
    bykey.setdefault((s_['card'], s_['text']), s_)
def acts_of(n):
    s_ = bykey.get((n['card'], n['text']))
    if not s_: return {P[n['k']][2]}
    a = {x for p in s_.get('처리', []) for x in p['acts'] if not x.startswith('키워드 실행')} | {x.replace('키워드 실행: ', '') for p in s_.get('처리', []) for x in p['acts'] if x.startswith('키워드 실행')}
    a |= {'K:' + k for k in s_.get('키워드', [])} if s_['분류'] == '키워드 효과' else set()
    return a or {'(처리 없음)'}
AS = {n['k']: acts_of(n) for n in nodes}
REASON = {'p': '같은 처리 단계', 's': '구조 유사(kNN)', 't': '같은 유발 조건', 'q': '같은 Q&A 쟁점', 'c': '같은 카드', 'm': '이름 언급'}
TH = 0.15; weak = collections.Counter(); rows = []; cause_cnt = collections.Counter(); out_total = 0
md = ['# 효과 네트워크 클러스터 점검 (E30)', '',
      '`net/effect_sna.json`의 세부 클러스터 %d개를 **다시 계산하지 않고** 읽기만 했습니다(노드 %d개). 대표 효과 3개는 클러스터 안 연결 중심성(pr)이 높은 순서로, 같은 카드는 한 번만 뽑았습니다.' % (len(clusters), len(nodes)), '',
      '**이상치 기준** — 효과의 「처리 행동」(모든 처리 단계의 행동)이 어느 것도 그 클러스터 구성원의 3% 이상이 하지 않는(구성원 30개 미만이면 10% 미만)으로만 나타나는 효과. 처리 행동은 맞지만 「유발 조건」이 드문 효과(3% 미만)는 이상치로 세지 않고 클러스터마다 개수만 적었습니다. **편입 원인**은 이상치와 같은 클러스터 구성원 사이 링크의 이유 중 가장 센 것입니다(p 같은 처리 단계 · s 구조 유사 · t 같은 유발 조건 · q 같은 Q&A 쟁점 · c 같은 카드 · m 이름 언급).', '']
body = []
for c in sorted(clusters, key=lambda c: -c['n']):
    ks = mem[c['id']]; n = len(ks); thr = 0.10 if n < 30 else 0.03
    cls_c = collections.Counter(P[k][0] for k in ks); tr_c = collections.Counter(P[k][1] for k in ks); ac_c = collections.Counter(a for k in ks for a in AS[k])
    rep, seen = [], set()
    for k in sorted(ks, key=lambda k: -nodes[k]['pr']):
        if nodes[k]['card'] in seen: continue
        seen.add(nodes[k]['card']); rep.append(k)
        if len(rep) == 3: break
    themes = {a for a, v in ac_c.items() if v / n >= TH}
    if not themes: themes = {ac_c.most_common(1)[0][0]}
    outs = []
    for k in ks:
        if AS[k] & themes: continue
        inner = collections.Counter()
        for o, d in nbr[k]:
            if nodes[o]['c'] == c['id']:
                for r, w in d.items(): inner[r] = max(inner[r], w)
        top = max(inner.items(), key=lambda x: x[1]) if inner else None
        outs.append((k, top[0] if top else '-', top[1] if top else 0))
    weak_n = sum(1 for k in ks if (AS[k] & themes) and tr_c[P[k][1]] / n < (0.10 if n < 30 else 0.03))
    out_total += len(outs)
    for k, r, w in outs: cause_cnt[REASON.get(r, '클러스터 안 링크 없음')] += 1
    grp = collections.defaultdict(list)
    for o in outs: grp[' + '.join(sorted(AS[o[0]]))].append(o)
    top_act = ', '.join('%s %d%%' % (a, round(100 * v / n)) for a, v in ac_c.most_common(3))   # 그 행동을 하는 효과의 비율(여러 단계라 합이 100%를 넘을 수 있음)
    top_tr = ', '.join('%s %d%%' % (a[:28], round(100 * v / n)) for a, v in tr_c.most_common(2))
    body += ['## %d. %s  (구성원 %d · 대분류 %d %s)' % (c['id'], c['name'], n, co_of[c['id']]['id'], co_of[c['id']]['name']), '',
             '- 구성: %s | 유발·타이밍 %s | 처리 행동 %s | 주제 행동(%d%% 이상) %s' % (', '.join('%s %d%%' % (a, round(100 * v / n)) for a, v in cls_c.most_common(3)), top_tr, top_act, round(100 * TH), ', '.join(sorted(themes))),
             '- 대표 효과:']
    for k in rep: body.append('  - %s %s · %s' % (nodes[k]['card'], nodes[k]['name'], nodes[k]['text'][:110]))
    body.append('- 이상치 %d개 (%.1f%%)%s · 주제 행동은 맞지만 유발 조건만 드문 효과 %d개' % (len(outs), 100 * len(outs) / n, ':' if outs else ' — 없음', weak_n))
    for acts, L in sorted(grp.items(), key=lambda x: -len(x[1])):
        cc = collections.Counter(REASON.get(r, '링크 없음') for _, r, _ in L)
        body.append('  - 처리 「%s」 %d개 — 편입 원인: %s' % (acts[:50], len(L), ', '.join('%s %d' % x for x in cc.most_common(2))))
        for k, r, w in sorted(L, key=lambda o: -o[2])[:3]:
            nd = nodes[k]; body.append('    - **%s %s** (k=%d) %s → %s %d' % (nd['card'], nd['name'], k, nd['text'][:90], REASON.get(r, '링크 없음'), w))
        if len(L) > 3: body.append('    - 같은 처리 %d개 전체: %s' % (len(L), ', '.join('%s %s' % (nodes[k]['card'], nodes[k]['name']) for k, _, _ in sorted(L, key=lambda o: nodes[o[0]]['card'])[:14]) + (' …' if len(L) > 14 else '')))
    body.append('')
    rows.append((c['id'], c['name'], n, len(outs), ac_c.most_common(1)[0][1] / n, weak_n))
md += ['## 요약', '', '| # | 이름 | 구성원 | 이상치 | 유발 조건만 드문 효과 | 최다 처리 행동을 하는 효과 비율 |', '|---|---|---|---|---|---|']
for r in rows: md.append('| %d | %s | %d | %d | %d | %d%% |' % (r[0], r[1], r[2], r[3], r[5], round(100 * r[4])))
md += ['', '이상치 합계 %d개 / 노드 %d개 (%.1f%%).' % (out_total, len(nodes), 100 * out_total / len(nodes)), '']
tot = sum(cause_cnt.values())
md += ['## 원인 분석', '',
       '이상치 %d개의 편입 원인(이상치와 같은 클러스터 구성원을 잇는 링크 중 가장 센 이유): %s.' % (out_total, ', '.join('%s %d개(%d%%)' % (r, v, round(100 * v / tot)) for r, v in cause_cnt.most_common())), '',
       '- **같은 유발 조건 링크(t)가 처리 차이를 이깁니다.** 링크는 같은 유발 조건 안에서 구조가 가장 비슷한 5개를 강도 50~100으로 잇는데, 유발 조건이 특이한 경우(예: 「이 카드가 진화원에서 효과로 파기되었을 때」) 그 조건을 쓰는 효과는 처리가 달라도 서로만 강하게 연결됩니다. 그 결과 소수의 형제 효과 묶음이 다른 처리의 큰 클러스터에 통째로 들어갑니다. 예: 《퇴화》 클러스터(12)의 「진화원에서 파기됐을 때 메모리 +1」 10개(EX8-005 고로몬 포함)·「…드로우」 8개는 같은 유발 조건의 《퇴화》 효과와 묶였습니다.',
       '- **구조 유사(s)만으로 들어온 경우**는 「상대의 턴 종료까지 ~내성」처럼 문장 틀이 같은 효과입니다. 처리 행동 이름은 다르지만 구조 유사도(TF-IDF)에서 유발 타이밍·지속 토큰의 비중이 커서 그런 것으로 보입니다(추정, 가중치를 바꿔 확인하지는 않았습니다).',
       '- **Q&A 쟁점(q)·이름 언급(m)으로 들어온 경우**는 소수입니다. Q&A 쟁점은 20개 이하 묶음에서만 링크를 만들기 때문에 영향이 작습니다.',
       '- 처리 단계가 둘 이상인 효과는 첫 행동이 아니라 모든 단계의 행동으로 판단했기 때문에(예: BT23-032 토우몬 「효과 부여 → 퇴화」) 이상치로 세지 않았습니다.',
       '- **개선 방향(이번에 하지 않음):** (1) 유발 조건 링크의 이웃 선택에서 처리 행동이 하나도 겹치지 않는 후보를 제외하거나 가중치를 낮추기, (2) 유발 조건이 같은 형제 묶음이 10개 이상이면 별도 클러스터로 분리, (3) 클러스터 확정 후 주제 행동이 없는 구성원을 가장 가까운 주제 클러스터로 재배정하는 후처리. 클러스터는 사용자 지시에 따라 다시 계산하지 않았습니다.', '']
open('paper/results/cluster_review.md', 'w', encoding='utf-8').write('\n'.join(md) + '\n' + '\n'.join(body) + '\n')
print(out_total, cause_cnt.most_common())
