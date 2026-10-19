"""Add cards from a Bandai "번역완료" master workbook (Korean translation pass) to cards.json, for sets that are not on
digimoncard.co.kr yet (e.g. BTK-24 before release). Cards already in cards.json are left untouched.

usage: python import_xlsx_cards.py "<...BTK-24 번역완료_260813.xlsx>" BT-24
Format follows the scraped site cards (scrape_cards.py): '상단 텍스트' = special evolution + effect (+ security effect for
non-options), '하단 텍스트' = inherited effect, or security effect for options, or the link block for link cards.
"""
import json, re, sys
import openpyxl

src, label = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else '')
COLOR = {'赤': 'red', '青': 'blue', '黄': 'yellow', '緑': 'green', '黒': 'black', '紫': 'purple', '白': 'white',
         '레드': 'red', '블루': 'blue', '옐로': 'yellow', '그린': 'green', '블랙': 'black', '퍼플': 'purple', '화이트': 'white'}
KIND = {'デジタマ': '디지타마', 'デジモン': '디지몬', 'テイマー': '테이머', 'オプション': '옵션', '디지타마': '디지타마', '디지몬': '디지몬', '테이머': '테이머', '옵션': '옵션'}
blank = lambda v: v is None or str(v).strip() in ('', '-', 'ー', '－', '―')
txt = lambda v: '' if blank(v) else re.sub(r'\s+', ' ', str(v)).strip()


def sheet_cards(ws):
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows[:6]) if r and r[0] == 'カードNo')
    head = [str(c).strip() if c else '' for c in rows[hi]]
    def col(*names, nth=0):
        for n in names:
            idx = [i for i, h in enumerate(head) if h == n]
            if len(idx) > nth: return idx[nth]
            if idx and nth: return idx[-1]
        return None
    C = {'no': col('カードNo'), 'par': col('パラレル表記'), 'rar': col('レアリティ'), 'kind': col('카드種', 'カード種'),
         'name': col('名前', nth=1), 'lv': col('レベル'), 'form': col('形態', nth=1), 'attr': col('속성', '属性'), 'type': col('유형', 'タイプ'),
         'cost': col('登場/使用コスト'), 'e1lv': col('進化条件1レベル'), 'e1c': col('進化条件1コスト'), 'e2lv': col('진화 조건2レベル', '進化条件2レベル'),
         'e2c': col('進化条件2コスト'), 'dp': col('DP'), 'sp': col('特殊진화'), 'eff': col('효과'), 'spp': col('特殊등장'), 'rule': col('特別ルール'),
         'sec': col('시큐리티효과'), 'inh': col('진화원 효과'), 'ldp': col('リンクDP'), 'lcond': col('링크 조건'), 'leff': col('링크 中효과')}
    colors = [i for i, h in enumerate(head) if re.match(r'^色\d$', h)]
    get = lambda r, k: r[C[k]] if C[k] is not None and C[k] < len(r) else None
    out = []
    for r in rows[hi + 1:]:
        no = txt(get(r, 'no')).replace(' ', '')
        if not re.match(r'^[A-Z]+\d*-\d+$', no) or not txt(get(r, 'name')):
            continue
        kind = KIND.get(txt(get(r, 'kind')), txt(get(r, 'kind')))
        cols = []
        for i in colors:
            c = COLOR.get(txt(r[i]))
            if c and c not in cols: cols.append(c)
        top = ' '.join(x for x in (txt(get(r, 'sp')), txt(get(r, 'spp')), txt(get(r, 'rule')), txt(get(r, 'eff'))) if x)
        sec, inh = txt(get(r, 'sec')), txt(get(r, 'inh'))
        if txt(get(r, 'lcond')):
            ldp = txt(get(r, 'ldp')).replace('DP', '').strip()
            bottom = ' '.join(x for x in (txt(get(r, 'lcond')), txt(get(r, 'leff')), f'〈링크 중〉이 디지몬의 DP {ldp}.' if ldp else '') if x)
        elif kind == '옵션':
            bottom = sec
        else:
            bottom = inh
            if sec: top = (sec + ' ' + top).strip()
        evo = lambda lv, c: f"{txt(lv)}~{txt(c)}" if txt(lv) else '-'
        out.append({'no': no, 'name': f"{no}{txt(get(r, 'rar'))} {txt(get(r, 'name'))}", 'color': '_'.join(cols), 'lv': txt(get(r, 'lv')),
                    'parallel': not blank(get(r, 'par')), 'rarity': txt(get(r, 'rar')), 'type': kind, '형태': txt(get(r, 'form')),
                    '속성': txt(get(r, 'attr')), '유형': txt(get(r, 'type')).replace('/', ','), 'DP': txt(get(r, 'dp')),
                    '등장 코스트': txt(get(r, 'cost')), '진화 코스트 1': evo(get(r, 'e1lv'), get(r, 'e1c')), '진화 코스트 2': evo(get(r, 'e2lv'), get(r, 'e2c')),
                    '상단 텍스트': top or '-', '하단 텍스트': bottom or '-', '입수 정보': label, 'source': 'xlsx'})
    return out


wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
new = []
for ws in wb.worksheets:
    try:
        new += sheet_cards(ws)
    except StopIteration:
        continue
cards = json.load(open('cards.json', encoding='utf-8'))
have = {c['no'] for c in cards}
seen, add = set(), []
for c in sorted(new, key=lambda c: c['parallel']):     # base print first, parallels dropped like the site list
    if c['no'] in have or c['no'] in seen: continue
    seen.add(c['no']); add.append(c)
order = {c['no']: k for k, c in enumerate(new)}
add.sort(key=lambda c: order[c['no']])
json.dump(cards + add, open('cards.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('read', len(new), 'added', len(add), [c['no'] for c in add[:3]], '...', [c['no'] for c in add[-3:]])
