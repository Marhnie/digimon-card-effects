"""Wilson 95 % intervals for the headline selective-judging numbers, so the thesis reports n and uncertainty, not bare percentages.
  python paper/stats_ci.py  -> paper/results/stats_ci.json"""
import json, math, os
ROOT = os.path.dirname(os.path.abspath(__file__))
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0, c - h), 4), round(min(1, c + h), 4)
X = {'BT25 dry run, R2 colloquial (E55)': (16, 16), 'BT25 dry run, R2 official (E55)': (2, 2), 'BT25 dry run, R1 colloquial (E55)': (7, 7),
     'BT25 dry run, page official (E55)': (84, 85), 'BT25 dry run, page colloquial (E55)': (20, 21)}
c = json.load(open(os.path.join(ROOT, 'results', 'complement_q15_v2.json'), encoding='utf-8'))
for t, m in c['at'].items():
    n = m['added_on_held']
    if n: X[f'q15_v2 on held, target {t}'] = (round(m['added_acc'] * n), n)
res = {k: {'k': a, 'n': b, 'acc': round(a / b, 4), 'wilson95': wilson(a, b)} for k, (a, b) in X.items()}
json.dump(res, open(os.path.join(ROOT, 'results', 'stats_ci.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in res.items(): print(k, v['k'], v['n'], v['wilson95'])
