"""Add standardized-question data (intent, situation slots, yes/no, negation per Q&A) to the test-page bundle."""
import json, re
src = open('q_slots.py', encoding='utf-8').read().split("for d in D: d['sl']")[0]
exec(src)   # INTENTS, intent(), SLOTS, slots(), D (all card Q&A in qa_items order)
data = json.loads(open('test_data.json', encoding='utf-8').read().replace('<\/', '</'))
slot_names = [f'{k}:{n}' for k, v in SLOTS.items() for n, _ in v]
sidx = {s: i for i, s in enumerate(slot_names)}
it_names = [n for n, _ in INTENTS] + ['기타']
assert len(D) == len(data['qa'])
for row, d in zip(data['qa'], D):
    sl = slots(d['q'])
    row += [it_names.index(d['it']), sorted(sidx[s] for s in sl), -1 if d['y'] is None else d['y'],
            1 if '부정:부정 질문' in sl else 0]
data['form'] = {
    'slots': [[k, n, p.pattern] for k, v in SLOTS.items() for n, p in v],
    'intents': [[n, p.pattern] for n, p in INTENTS] + [['기타', '']],
}
s = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\/')
open('test_data2.json', 'w', encoding='utf-8').write(s)
print(len(s), slot_names[:5], it_names)
