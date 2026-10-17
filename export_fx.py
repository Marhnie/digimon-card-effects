import json, re, collections, os
from link_fx import ACTION_RULE, FORM_RULE, KIND_RULE, KW_RULE, timing_rule  # importing re-runs the linking step
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

U = json.load(open('units3.json', encoding='utf-8'))
PATS = {p['id']: p for p in json.load(open('patterns.json', encoding='utf-8'))}
QI = {q['id']: q for q in json.load(open('qa_items.json', encoding='utf-8'))}
TOP = {t['id']: t for t in json.load(open('topic_items.json', encoding='utf-8'))}
CARDS = {c['no']: c for c in json.load(open('cards.json', encoding='utf-8'))}
R = {r['n']: r['t'] for r in json.load(open('rules2.json', encoding='utf-8'))['rules'] if r['l'] >= 0}

cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
rl = lambda ns: ', '.join(f'{n} {R.get(n, "")}' for n in ns)
cardname = lambda no: re.sub(r'^\S+\s*', '', CARDS[no]['name']) if no in CARDS else ''

def common(units, key, share=0.5):
    c = collections.Counter(x for u in units for x in set(u[key]))
    return [k for k, v in c.most_common() if v >= share * len(units)]

def group_rules(units, share=0.4):
    c = collections.Counter(n for u in units for n in u['rules'])
    return [k for k, v in c.most_common() if v >= share * len(units)]

def qa_of(units):
    return [q for u in units for q in u.get('qa', [])]

wb = Workbook()
HDR = Font(name='맑은 고딕', size=10, bold=True, color='FFFFFF')
BODY = Font(name='맑은 고딕', size=10)
FILL = PatternFill('solid', fgColor='1F4E78')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

def sheet(ws, headers, rows, widths):
    ws.append(headers)
    for r in rows:
        ws.append(r)
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w
    for i, row in enumerate(ws.iter_rows(), 1):
        for cell in row:
            cell.border = BORDER
            if i == 1:
                cell.font, cell.fill = HDR, FILL
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            else:
                cell.font = BODY
                cell.alignment = Alignment(vertical='top', wrap_text=True)
    ws.freeze_panes = 'B2'
    ws.auto_filter.ref = ws.dimensions

# ---- 1. 효과 유형 ----
by_type = collections.defaultdict(list)
for u in U:
    for ty in u['types']: by_type[ty].append(u)
rows = []
for t, us in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
    pc = collections.Counter(u['pattern'] for u in us)
    top = PATS[pc.most_common(1)[0][0]]
    qs = qa_of(us)
    subs = collections.Counter(u['sub'] for u in us if u['sub'])
    rows.append([t, len(us), sum(1 for u in us if u['type'] == t), len({u['card'] for u in us}), len(pc),
                 ', '.join(f'{k} {v}' for k, v in subs.most_common(8)), top['example'], rl(group_rules(us, 0.3)), len(qs),
                 ', '.join(sorted({TOP[x]['name'] for u in us for x in u['topics']})[:8])])
ws = wb.active; ws.title = '효과 유형'
sheet(ws, ['효과 유형(행동)', '효과 단위 수(복수 소속 포함)', '그중 주 행동', '카드 수', '패턴 수', '타이밍별 분포', '대표 문구(최다 패턴)', '관련 종합 룰 조항', '연결된 카드 Q&A', '관련 규칙 해설 주제'],
      rows, [24, 12, 10, 9, 9, 40, 70, 60, 11, 34])

# ---- 2. 효과 패턴 ----
by_pat = collections.defaultdict(list)
for u in U: by_pat[u['pattern']].append(u)
rows = []
for pid in sorted(by_pat):
    us = by_pat[pid]; p = PATS[pid]; qs = qa_of(us)
    ex = QI[qs[0]] if qs else None
    rows.append([pid, ' / '.join(p['types']), len(us), len(p['cards']), p['example'], p['tpl'],
                 ' / '.join(common(us, 'timing')), ' / '.join(common(us, 'keywords')), ' / '.join(common(us, 'actions')),
                 rl(group_rules(us)), len(qs),
                 (f"[{ex['card']}] Q. {cq(ex['q'])}\nA. {cq(ex['a'])}" if ex else ''),
                 ', '.join(p['cards'][:30]) + (f' 외 {len(p["cards"]) - 30}장' if len(p['cards']) > 30 else '')])
ws = wb.create_sheet('효과 패턴')
sheet(ws, ['패턴 ID', '효과 유형(결과)', '효과 단위 수', '카드 수', '대표 문구', '템플릿(숫자→N, 이름→「X」)', '공통 타이밍', '공통 키워드', '공통 행동',
           '관련 종합 룰 조항', '연결된 카드 Q&A', 'Q&A 예시', '카드 목록'],
      rows, [8, 28, 9, 8, 60, 50, 16, 16, 24, 50, 10, 60, 40])

# ---- 3. 효과 단위 ----
rows = []
for u in U:
    rows.append([u['card'], cardname(u['card']), u['where'], u['kind'], ' / '.join(u['types']), u['pattern'], u.get('trigger', ''), ' / '.join(u['timing']), ' / '.join(u['limit']),
                 ' / '.join(u['keywords']), ' / '.join(u['actions']), ' / '.join(u['targets']), ' / '.join(u['filters']), ' / '.join(u['forms']),
                 rl(u['rules']), len(u.get('qa', [])), u['text']])
ws = wb.create_sheet('효과 단위')
sheet(ws, ['카드 번호', '카드명', '위치', '종류', '효과 유형', '패턴 ID', '유발 조건', '타이밍', '횟수·장소 표시', '키워드', '행동', '대상', '필터', '형식',
           '관련 종합 룰 조항', '연결된 Q&A 수', '원문'],
      rows, [11, 16, 11, 14, 26, 8, 26, 16, 10, 16, 26, 18, 16, 20, 50, 9, 80])

# ---- 4. Q&A 연결 ----
rows = []
for q in QI.values():
    u = U[q['unit']] if q['unit'] is not None else None
    rows.append([q['card'] or '', cardname(q['card']) if q['card'] else q['cardname'], cq(q['q']), cq(q['a']),
                 ('효과 단위(인용구·항목명)' if q.get('how') == 'quote' else '효과 단위') if u else (f"일반 판정 → {q['rule']} {R.get(q['rule'], '')[:40]} (자동 추정)" if q.get('general') else '카드 리스트에 없음'),
                 u['pattern'] if u else '', ' / '.join(u['types']) if u else '', u['text'] if u else ''])
ws = wb.create_sheet('Q&A 연결')
sheet(ws, ['카드 번호', '카드명', '질문', '답변', '연결 수준', '패턴 ID', '효과 유형', '연결된 효과 원문'], rows, [11, 16, 60, 50, 30, 8, 26, 70])

# ---- 5. 태그 사전 ----
cnt = {k: collections.Counter(x for u in U for x in u[k]) for k in ('timing', 'keywords', 'actions', 'forms', 'targets', 'filters')}
kinds = collections.Counter(u['kind'] for u in U)
rows = []
for t, n in cnt['timing'].most_common(): rows.append(['타이밍', f'【{t}】', n, rl([timing_rule(t)] if timing_rule(t) else [])])
for t, n in cnt['keywords'].most_common(): rows.append(['키워드', f'《{t}》', n, rl([KW_RULE[t]] if KW_RULE.get(t) else [])])
for t, n in cnt['actions'].most_common(): rows.append(['행동', t, n, rl(ACTION_RULE.get(t, []))])
for t, n in cnt['forms'].most_common(): rows.append(['형식', t, n, rl(FORM_RULE.get(t, []))])
for t, n in kinds.most_common(): rows.append(['종류', t, n, rl(KIND_RULE.get(t, []))])
for t, n in cnt['targets'].most_common(): rows.append(['대상', t, n, ''])
for t, n in cnt['filters'].most_common(): rows.append(['필터', t, n, ''])
ws = wb.create_sheet('태그 사전')
sheet(ws, ['구분', '태그', '효과 단위 수', '연결한 종합 룰 조항'], rows, [10, 26, 12, 70])

# ---- 0. 안내 ----
ws = wb.create_sheet('안내', 0)
info = [
    ['디지몬 카드 효과 분류 v3', ''],
    ['만든 날', '2026-10-17'],
    ['카드 데이터', '한글 사이트 카드 리스트 전체(5,824장, 카드 번호 기준 3,852종; 같은 번호의 축약 재판 문구는 가장 긴 정식 문구로 통일)'],
    ['근거 데이터', '종합 룰 Ver.4.3 한국어판(3차 수정본), 한글 사이트 규칙 해설 Q&A·카드 Q&A(2026-10-17 수집)'],
    ['효과 단위 수', "=COUNTA('효과 단위'!A:A)-1"],
    ['효과 유형 수', "=COUNTA('효과 유형'!A:A)-1"],
    ['효과 패턴 수', "=COUNTA('효과 패턴'!A:A)-1"],
    ['카드 Q&A 수', "=COUNTA('Q&A 연결'!C:C)-1"],
    ['효과 단위에 연결된 Q&A', "=COUNTIF('Q&A 연결'!E:E,\"효과 단위*\")"],
    ['일반 판정으로 분류된 Q&A', "=COUNTIF('Q&A 연결'!E:E,\"일반 판정*\")"],
    ['v3 추가(2026-10-17)', '유발 조건 축: 「~했을 때」 절에서 누가·어디서·무엇으로·무슨 일이를 뽑아 유형에 「유발 · …」로 추가(136종), 타이밍 표시 없는 「~했을 때」 효과 108개를 유발 효과로 재분류, 결과 행동은 「때,」 뒤에서만 추출, 유발 조건과 결과가 같으면 문구가 조금 달라도 같은 패턴(예: EX8-005 고로몬 = BT10-072 바그라군).'],
    ['v2 반영 결정(2026-10-17)', '① 유형=행동 중심(타이밍은 하위) ② 행동이 여러 개면 모든 유형에 포함 ③④ 옛·새 문구 10쌍 동일 취급(분류용, 원문 보존) ⑤ 행동 6개 룰 조항 연결 보완 ⑥ 결과(행동 조합)가 다르면 다른 패턴 ⑦ 미연결 Q&A: 인용구·항목명으로 연결, 남는 것은 일반 판정→가장 가까운 룰 조항(자동 추정)'],
    ['', ''],
    ['시트', '내용'],
    ['효과 유형', '사람이 읽을 수 있는 큰 분류. 타이밍 효과는 「타이밍 × 주 행동」(예: 【등장 시+진화 시】 · 소멸), 그 외는 키워드 능력·특수 진화 조건·〈룰〉 등'],
    ['효과 패턴', '머신러닝 군집(문구 템플릿의 글자 n-gram TF-IDF + 요소 태그, 코사인 평균 연결 군집). 문구가 조금 달라도 같은 처리를 하는 효과를 한 패턴으로 묶음. 같은 패턴 안의 다른 카드 Q&A는 판정 근거로 서로 참고할 수 있음'],
    ['효과 단위', '카드 텍스트를 효과 하나하나로 쪼갠 결과와 요소 태그(타이밍·키워드·행동·대상·필터·형식), 연결한 종합 룰 조항'],
    ['Q&A 연결', '카드 Q&A 각 문항이 그 카드의 어느 효과에 대한 질문인지 연결한 결과(질문의 타이밍·키워드 표기와 문구 유사도로 판정)'],
    ['태그 사전', '태그별 효과 단위 수와, 태그에 연결한 종합 룰 조항(이 표를 고치면 근거 연결이 바뀝니다)'],
    ['', ''],
    ['검토 부탁', '① 효과 유형의 나눔이 실무 감각과 맞는지 ② 같은 패턴에 다른 처리가 섞인 곳 ③ 태그 사전의 룰 조항 연결이 틀린 곳'],
]
for r in info: ws.append(r)
ws.column_dimensions['A'].width = 24; ws.column_dimensions['B'].width = 110
for i, row in enumerate(ws.iter_rows(), 1):
    for c in row:
        c.font = Font(name='맑은 고딕', size=12 if i == 1 else 10, bold=(i == 1 or c.column == 1 or i == 11))
        c.alignment = Alignment(vertical='top', wrap_text=True)

out = os.environ.get('OUT_DIR', 'out'); os.makedirs(out, exist_ok=True)
os.makedirs(out, exist_ok=True)
path = os.path.join(out, '카드효과_분류_v3.xlsx')
wb.save(path)
print(path)
