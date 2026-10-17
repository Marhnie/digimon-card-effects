exec(open('examples.py', encoding='utf-8').read().split('random.seed(11)')[0])
NEW = [
 ('BT22-063', 3, '상대의 턴에 이 디지몬이 블록해서 레스트했을 때, 진화원에 「쿠레미 쿄코」가 있어 이 효과로 액티브가 되었다면, 같은 턴에 다시 블록할 수 있나요?'),
 ('BT14-033', 0, '이 카드의 효과로 시큐리티를 전부 확인했지만 진화하지 않았을 때도, 자신의 시큐리티를 셔플하나요?'),
 ('BT21-061', 1, '자신의 테이머가 레드 1색뿐일 때, 이 카드의 【등장 시】 효과로 상대의 디지몬을 퇴화시킬 수 있나요?'),
 ('EX5-021', 0, '육성 에어리어에 이미 자신의 디지몬이 있을 때, 이 카드의 【등장 시】 효과로 「데바」 디지몬을 등장시킬 수 있나요?'),
 ('BT19-050', 0, '상대의 어택 중에 【카운터】 타이밍에 이 카드로 블래스트 진화했을 때, 이 카드의 【진화 시】 효과는 발휘되나요?'),
 ('BT19-050', 1, '이 카드의 효과로 레스트시킨 상대의 테이머가, 상대의 다음 액티브 페이즈에 액티브가 되나요?'),
]
by = {}
for i, u in enumerate(U): by.setdefault(u['card'], []).append(u)
res = []
for card, k, q in NEW:
    u = by[card][k]; v = verdict(u, q)
    print(card, k, v[0], v[3], '| slots:', sorted(slots(q)), '| it:', intent(q))
    res.append({'ask_card': card, 'ask_name': re.sub(r'^\S+\s*', '', CARDS[card]['name']), 'effect': u['text'], 'q': q, 'level': v[0]})
json.dump(res, open('examples_none.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
