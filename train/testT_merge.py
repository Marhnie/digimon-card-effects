"""Add unofficial next-set (JP->KR translation) cards and Q&A to this COPY's cards.json / qa.json (experiment only, test T)."""
import json, glob, collections
S = 'C:/Users/Daewonmedia/Downloads/카드_QA_번역_납품/신규세트_미발매_카드_QA_번역/_원본데이터/'
J = json.load(open(S + 'jp_card_text.json', encoding='utf-8'))
F = json.load(open(S + 'final_u.json', encoding='utf-8'))
C = json.load(open('cards.json', encoding='utf-8'))
have = {c['no'] for c in C}
out = [x for f in sorted(glob.glob('jpnext/cards_out_*.json')) for x in json.load(open(f, encoding='utf-8'))]
COL = {'赤': 'red', '青': 'blue', '黄': 'yellow', '緑': 'green', '黒': 'black', '紫': 'purple', '白': 'white'}
KIND = {'デジタマ': '디지타마', 'デジモン': '디지몬', 'テイマー': '테이머', 'オプション': '옵션'}
add = 0
for x in out:
    if x['no'] in have: continue
    j = J[x['no']]; info = dict((a, b) for a, b in j['info']); m = j['meta']
    col = '_'.join(COL.get(ch, '') for ch in info.get('色', '') if ch in COL)
    evo = info.get('進化条件1', '-')
    C.append({'no': x['no'], 'name': f"{x['no']}{m[1]} {x['name_kr']}", 'color': col, 'lv': m[3] if len(m) > 3 and m[3].startswith('Lv') else '',
              'parallel': False, 'rarity': m[1], 'type': KIND.get(m[2], m[2]), '형태': x.get('form', ''), '속성': x.get('attr', ''),
              '유형': x.get('types', ''), 'DP': info.get('DP', ''), '등장 코스트': info.get('コスト', ''), '진화 코스트 1': evo, '진화 코스트 2': '-',
              '상단 텍스트': x['upper'] or '-', '하단 텍스트': x['lower'] or '-', '입수 정보': j['set'], 'source': 'jp-unofficial'})
    add += 1
json.dump(C, open('cards.json', 'w', encoding='utf-8'), ensure_ascii=False)
Q = json.load(open('qa.json', encoding='utf-8'))
names = {c['no']: c['name'].split(' ', 1)[-1] for c in C}
by = collections.defaultdict(list)
for x in F:
    if x['set'] != 'BT-25':
        by[x['set']].append({'name': f"{x['no']} {names.get(x['no'], x['kr_name'])}", 'upd': '', 'qa': [[q['q'], q['a']] for q in x['final']]})
for s, cards in by.items():
    Q['cqa'].insert(0, {'set': f'{s} 【{s}】(일본판 임의번역)', 'cards': cards})
json.dump(Q, open('qa.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('cards added', add, {s: sum(len(c['qa']) for c in v) for s, v in by.items()})
