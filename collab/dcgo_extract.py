"""DCGO-Card-Scripts(MIT, github.com/DCGO2/DCGO-Card-Scripts)의 카드별 C# 스크립트를 정적으로 읽어
카드마다 효과 아이콘·턴 1회·진화원 효과 여부·발휘 시 재확인 조건을 뽑고, 한글 카드 텍스트의 【아이콘】과 대조한다.
엔진을 실행하지는 않음(Unity 필요). 출력 collab/dcgo_cards.json, collab/dcgo_vs_kr.json"""
import json, re, os, glob, collections, sys
SRC = os.environ.get('DCGO', r'C:\Users\Daewonmedia\ext\DCGO-Card-Scripts')
ICON = {  # 한글 아이콘: (영문 설명 태그, 판정 함수 호출)
 '등장 시': (r"\[On Play", r'CanTriggerOnPlay\b'), '진화 시': (r"\[When Digivolving", r'CanTriggerWhenDigivolving\b'),
 '어택 시': (r"\[When Attacking", r'CanTriggerOnAttack\b'), '소멸 시': (r"\[On Deletion", r'CanTriggerOnDeletion\b'),
 '메인': (r"\[Main\]", r'CanTriggerOptionMainEffect\b'), '시큐리티': (r"\[Security\]", r'CanTriggerSecurityEffect\b|EffectTiming\.SecuritySkill'),
 '자신의 턴': (r"\[Your Turn\]", None), '상대의 턴': (r"\[Opponent's Turn\]", None), '서로의 턴': (r"\[All Turns\]", None),
 '자신의 메인 페이즈 개시 시': (r"\[Start of Your Main Phase", None), '자신의 턴 종료 시': (r"\[End of Your Turn", None),
 '자신의 턴 개시 시': (r"\[Start of Your Turn", None), '어택 종료 시': (r"\[End of Attack", None),
 '상대의 턴 종료 시': (r"\[End of Opponent'?s Turn", None), '링크 시': (r"\[When Link", None)}
cards = {}
for f in glob.glob(os.path.join(SRC, 'CardEffect', '*', '**', '*.cs'), recursive=True):
    no = os.path.basename(f)[:-3].replace('_', '-')
    if not re.match(r'^[A-Z]+\d*-\d+$', no): continue
    s = open(f, encoding='utf-8', errors='ignore').read()
    ic = {k for k, (a, b) in ICON.items() if re.search(a, s, re.I) or (b and re.search(b, s))}
    # 아이콘이 붙는 키워드 효과는 팩토리 호출로 구현됨(설명 문자열 없음)
    if re.search(r'CardEffectFactory\.(Save|MaterialSave)Effect', s): ic.add('소멸 시')
    if re.search(r'CardEffectFactory\.(PlaySelfTamerSecurityEffect|PlaySelfDigimonAfterBattleSecurityEffect|PlaceSelfDelayOptionSecurityEffect)', s): ic.add('시큐리티')
    if re.search(r'isWhenDigivolving:\s*true', s): ic.add('진화 시')
    ic = sorted(ic)
    once = len(re.findall(r'SetUpActivateClass\([^;]*?,\s*1\s*,', s)) + len(re.findall(r'Once Per Turn', s))
    cards[no] = {'icons': ic, 'once_per_turn': once > 0, 'inherited': bool(re.search(r'isInheritedEffect:\s*true|SetIsInheritedEffect\(true\)', s)),
                 'recheck_on_field': len(re.findall(r'bool CanActivateCondition[^{]*\{[^}]*IsExistOnBattleArea', s)),
                 'lines': s.count('\n'), 'stub': s.count('\n') < 15}
json.dump(cards, open('collab/dcgo_cards.json', 'w', encoding='utf-8'), ensure_ascii=False)
# 한글 카드 텍스트와 대조
T = json.load(open('test_data4.json', encoding='utf-8')); kr = collections.defaultdict(set); krtxt = collections.defaultdict(str)
for u in T['units']:
    kr[u[0]].update(i for i in re.findall(r'【([^】]+)】', u[3]) if i in ICON); krtxt[u[0]] += u[3]
both = sorted(set(kr) & set(cards)); per = {}
for k in ICON:
    tp = sum(1 for c in both if k in kr[c] and k in cards[c]['icons']); fn = sum(1 for c in both if k in kr[c] and k not in cards[c]['icons'])
    fp = sum(1 for c in both if k not in kr[c] and k in cards[c]['icons'])
    per[k] = {'kr': tp + fn, 'recall': round(tp / ((tp + fn) or 1), 3), 'precision': round(tp / ((tp + fp) or 1), 3)}
MAIN = ['등장 시', '진화 시', '어택 시', '소멸 시', '메인', '시큐리티']
exact = [c for c in both if set(kr[c]) & set(MAIN) and {i for i in kr[c] if i in MAIN} == {i for i in cards[c]['icons'] if i in MAIN}]
haskr = [c for c in both if set(kr[c]) & set(MAIN)]
miss = [c for c in haskr if c not in exact]
prod = lambda c: c.split('-')[0]
NEW = {'BT22', 'BT23', 'BT24', 'EX9', 'EX10', 'ST21', 'ST22'}
out = {'dcgo_cards': len(cards), 'kr_cards': len(kr), 'matched': len(both), 'kr_only': len(set(kr) - set(cards)),
       'kr_only_by_product': collections.Counter(prod(c) for c in set(kr) - set(cards)).most_common(25),
       'stub_scripts': sum(1 for c in cards.values() if c['stub']), 'per_icon': per,
       'main_icon_exact': round(len(exact) / len(haskr), 4), 'main_icon_n': len(haskr),
       'new_products_exact': round(sum(1 for c in exact if prod(c) in NEW) / (sum(1 for c in haskr if prod(c) in NEW) or 1), 4),
       'mismatch_examples': [{'card': c, 'kr': sorted(kr[c]), 'dcgo': cards[c]['icons']} for c in miss[:40]]}
json.dump(out, open('collab/dcgo_vs_kr.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'mismatch_examples'}, ensure_ascii=False, indent=1))
