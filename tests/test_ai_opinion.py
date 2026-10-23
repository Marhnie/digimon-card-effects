"""E51 smoke test with a fake Claude client (no network, no key): cache, budget cap, per-IP cap, JSON parsing, refs filtering."""
import json, os, sys, tempfile, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server')); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import ai_opinion as A
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
cards = {c['no']: c for c in json.load(open('cards.json', encoding='utf-8'))}
rules = json.load(open('rules2.json', encoding='utf-8'))['rules']
calls = []
class FakeMsgs:
    def create(self, **kw):
        calls.append(kw)
        txt = '설명입니다 {"ans": 0, "confidence": "high", "summary": "근거 Q1에 따라 아니요입니다.", "refs": ["Q1", "C1", "ZZ9"]}'
        return types.SimpleNamespace(content=[types.SimpleNamespace(type='text', text=txt)], usage=types.SimpleNamespace(input_tokens=3000, output_tokens=400))
fake = types.SimpleNamespace(messages=FakeMsgs())
db = os.path.join(tempfile.mkdtemp(), 'ai.db')
ai = A.AiOpinion(db, QA, cards, rules, lambda q, k: [3117, 10, 11, 12, 13, 14, 15, 16, 17, 18][:k], client=fake)
r = ai.ask('샤인그레이몬 루인모드 파피몬 등장시 효과', ['EX4-074'], ip='1.1.1.1')
assert r['ans'] == 0 and not r['cached'] and r['label'].startswith('AI 의견'), r
assert [x['id'] for x in r['refs']] == ['Q1', 'C1'], r['refs']          # unknown id ZZ9 dropped
assert abs(r['usd'] - (3000 * 4 + 400 * 20) / 1e6) < 1e-6
assert 'EX4-074' in calls[0]['messages'][0]['content'] and '[R1]' in calls[0]['messages'][0]['content']
r2 = ai.ask('샤인그레이몬 루인모드 파피몬 등장시 효과', ['EX4-074'], ip='2.2.2.2'); assert r2['cached'] and len(calls) == 1   # cache: no second call
A.PER_IP = 2
ai.ask('다른 질문 1', ['EX4-074'], ip='9.9.9.9'); ai.ask('다른 질문 2', ['EX4-074'], ip='9.9.9.9')
assert ai.ask('다른 질문 3', ['EX4-074'], ip='9.9.9.9')['error'] == 'rate'
A.DAILY_USD = 0.0001
assert ai.ask('또 다른 질문', ['EX4-074'], ip='5.5.5.5')['error'] == 'budget'
print('ok, calls =', len(calls))
