"""DGC Sim 협업 시범 세트: 최신 팩(BT22~24·EX9·EX10·ST21·ST22) 네/아니요 Q&A 중 엔진이 확신하지 못한(conf<0.80) 문항.
룰 엔진이 실제 실행으로 판정할 수 있는지 시험하기 위한 입력. 출력 collab/pilot_set.json, collab/pilot_set.csv"""
import json, re, csv
T = json.load(open('test_data4.json', encoding='utf-8')); QA = T['qa']; UN = T['units']
E = json.load(open('net/engine_py_test.json')); thr = 0.80
cq = lambda s: re.sub(r'\s*\d{4}/\d{2}/\d{2}\s*업데이트\s*', ' ', s).strip()
CARD = re.compile(r'[A-Z]{1,3}\d{0,2}-\d{2,3}')
def kind(i):
    q, a = QA[i][1], cq(QA[i][2])
    other = bool(CARD.search(q + a)) and any(c != QA[i][0] for c in CARD.findall(q + a))
    nm = re.findall(r'「([^「」]+)」', q)
    rest = re.sub(r'^\s*(네|예|아니요|아니오|아뇨)[,，.\s]+[^.]*?니다\.\s*', '', a, count=1).strip()
    return ('다른 카드' if other else '단일 카드'), ('이유 있음' if len(rest) >= 15 else '이유 없음')
rows = []
for k, (p, c, y) in E.items():
    i = int(k)
    if c >= thr: continue
    u = QA[i][3]; fx = UN[u][3] if u is not None and u >= 0 else ''
    k1, k2 = kind(i)
    rows.append({'id': i, 'card': QA[i][0], 'effect': fx, 'question': QA[i][1], 'answer': cq(QA[i][2]),
                 'gold': '네' if y else '아니요', 'engine_guess': '네' if p else '아니요', 'engine_conf': c,
                 'scope': k1, 'reason': k2})
rows.sort(key=lambda r: (r['card'], r['id']))
json.dump({'note': '공식 Q&A(카드 효과 시점 기준). gold=공식 답. 룰 엔진은 question만 보고 판정 → gold와 대조', 'n': len(rows), 'items': rows},
          open('collab/pilot_set.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
with open('collab/pilot_set.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]) + ['sim_answer', 'sim_note']); w.writeheader()
    for r in rows: w.writerow(r)
import collections; print(len(rows), collections.Counter((r['scope'], r['reason']) for r in rows))
