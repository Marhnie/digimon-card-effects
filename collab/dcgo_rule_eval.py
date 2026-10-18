"""DCGO 효과 정보로 질문 유형별 규칙 판정 → 공식 Q&A 정답과 대조(전체·엔진 미확신 문항)"""
import json, re, collections
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']
E = json.load(open('collab/dcgo_effects.json', encoding='utf-8'))
EN = json.load(open('net/engine_py_test.json')); uns = {int(k) for k, v in EN.items() if v[1] < 0.8}
L = [i for i, r in enumerate(QA) if r[8] >= 0 and r[0]]
SKIP = r'(하지\s*않|않고|않을\s*수|선택하지\s*않|일부만|만\s*(파기|등장|놓|되돌|선택|추가|레스트|소멸)[^?]*수\s*있)'
def blocks(i):
    c = QA[i][0]; q = QA[i][1]
    if c not in E: return None
    ic = re.findall(r'【([^】]+)】', q.split('효과')[0] if '효과' in q else q)
    bs = [b for b in E[c] if b['tags'] and (not ic or set(ic) & set(b['tags']))]
    return bs
def predict(i):
    bs = blocks(i)
    if not bs: return None
    if any(b['optional'] or b['noselect'] or b['endnotmax'] for b in bs): return 1
    if all(b['all_forced'] and not b['optional'] for b in bs): return 0
    return None
res = collections.Counter(); rows = []
for i in L:
    if not re.search(SKIP, QA[i][1]): continue
    p = predict(i)
    if p is None: res['abstain'] += 1; continue
    ok = p == QA[i][8]; res[('ok' if ok else 'bad', p)] += 1
    if i in uns: res[('uns_ok' if ok else 'uns_bad')] += 1
    rows.append((i, p, QA[i][8]))
print(res)
