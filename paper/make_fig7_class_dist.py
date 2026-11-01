"""Fig 7: distribution of effect classes in struct2.json (rulebook 15-8 classes plus keyword and card-info units)."""
import collections, json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams['font.family'] = 'Malgun Gothic'
S = json.load(open(os.path.join(HERE, '..', 'struct2.json'), encoding='utf-8'))
S = S if isinstance(S, list) else S['units']
c = collections.Counter(s['분류'] for s in S).most_common()[::-1]
print(sum(n for _, n in c), c)
fig, ax = plt.subplots(figsize=(7, 3.2), dpi=200)
ax.barh([k for k, _ in c], [n for _, n in c], color='#2a78d6', height=.6)
for i, (_, n) in enumerate(c):
    ax.text(n + 60, i, f'{n:,}', va='center', fontsize=9, color='#0b0b0b')
ax.set_xlabel('효과 단위 수')
ax.set_xlim(0, c[-1][1] * 1.12)
ax.grid(axis='x', color='#e5e4df', lw=.7); ax.set_axisbelow(True)
for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
ax.tick_params(axis='y', length=0)
fig.tight_layout()
fig.savefig(os.path.join(HERE, 'figures', 'fig7_class_distribution.png'), facecolor='white')
