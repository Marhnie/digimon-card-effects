"""Fig 5: accuracy-coverage operating points (values from E52, complement_q15_v2.json).
Item-level probabilities on the 597 test set were not saved, so these are thresholds, not a full curve."""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams['font.family'] = 'Malgun Gothic'
c = json.load(open(os.path.join(HERE, 'results', 'complement_q15_v2.json'), encoding='utf-8'))
at = c['at']
page = [(c['page_decided'] / c['joined'] * 100, c['page_acc'] * 100)]
# E52 table: q15_v2 alone on the full 597 test set
model = [(100, 80.9), (50.8, 97.0), (35.9, 100)]
both = [(at[k]['combined_share'] * 100, at[k]['combined_acc'] * 100) for k in ('0.97', '0.98')]

fig, ax = plt.subplots(figsize=(7, 4.4), dpi=200)
ax.plot(*zip(*sorted(model)), 'o', color='#2a78d6', ms=7, label='q15_v2 단독 (n=597)')
ax.plot(*zip(*page), 's', color='#eb6834', ms=9, label='판정 페이지 단독 (n=557)')
ax.plot(*zip(*both), 'D', color='#1baf7a', ms=8, label='페이지 + q15_v2 (n=557)')
ax.set_xlim(30, 103); ax.set_ylim(78, 102)
ax.set_xlabel('답변 범위 (%)'); ax.set_ylabel('답변 문항 정확도 (%)')
ax.grid(color='#e5e4df', lw=.7); ax.set_axisbelow(True)
for s in ('top', 'right'): ax.spines[s].set_visible(False)
ax.legend(frameon=False, loc='lower left')
fig.tight_layout()
fig.savefig(os.path.join(HERE, 'figures', 'fig5_accuracy_coverage.png'))
