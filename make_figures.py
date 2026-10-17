"""Paper figures -> paper/figures/*.png
fig1  resolution sweep (fine level): modularity real vs null, seed / adjacent stability, cluster count
fig2  coarse level: cluster-graph Louvain vs effect-graph low-resolution partition
fig3  effect network map coloured by coarse group
fig4  link reasons (count)"""
import json, os, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ('malgun.ttf',):
    p = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', f)
    if os.path.exists(p): font_manager.fontManager.addfont(p); plt.rcParams['font.family'] = font_manager.FontProperties(fname=p).get_name()
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#e6e6e6',
                     'axes.unicode_minus': False, 'font.size': 10})
OUT = os.path.join('paper', 'figures'); os.makedirs(OUT, exist_ok=True)
INK, MUTED, A, B = '#222', '#888', '#2a6fdb', '#d9822b'
RES_F, RES_C = float(os.environ.get('RES_F', '1.6')), float(os.environ.get('RES_C', '0.4'))

# fig1 ---------------------------------------------------------------------
rows = json.load(open('net/cc_fine.json'))['rows']
g = [r['res'] for r in rows]
fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
ax[0].plot(g, [r['Q'] for r in rows], '-o', color=A, ms=4, lw=2, label='실제 네트워크')
ax[0].plot(g, [r['Q_null'] for r in rows], '-o', color=MUTED, ms=4, lw=2, label='무작위(귀무) 네트워크')
ax[0].set_title('모듈성 Q', color=INK); ax[0].set_xlabel('해상도 γ'); ax[0].set_ylim(-0.02, 0.85); ax[0].legend(frameon=False, loc='center right', bbox_to_anchor=(1, 0.42))
ax[1].plot(g, [r['seed_AMI'] for r in rows], '-o', color=A, ms=4, lw=2, label='시드 10회 간 AMI')
ax[1].plot(g[1:], [r['adj_AMI'] for r in rows[1:]], '-o', color=B, ms=4, lw=2, label='이웃 γ 간 AMI')
ax[1].set_title('안정성', color=INK); ax[1].set_xlabel('해상도 γ'); ax[1].set_ylim(0.4, 1); ax[1].legend(frameon=False)
ax[2].plot(g, [r['k_mean'] for r in rows], '-o', color=A, ms=4, lw=2)
ax[2].set_title('클러스터 수(시드 평균)', color=INK); ax[2].set_xlabel('해상도 γ')
for a in ax: a.axvline(RES_F, color=INK, lw=1, ls='--'); a.set_xscale('log'); a.minorticks_off(); a.set_xticks([0.2, 0.5, 1, 1.6, 3, 5]); a.set_xticklabels(['0.2', '0.5', '1', '1.6', '3', '5'])
fig.suptitle(f'세부 클러스터 해상도 검사 — 점선 = 채택값 γ={RES_F}', x=0.01, ha='left', color=INK)
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig1_resolution_fine.png'), dpi=200); plt.close(fig)

# fig2 ---------------------------------------------------------------------
if os.path.exists('net/cc_coarse.json') and os.path.exists('net/cc_coarse_node.json'):
    cg = json.load(open('net/cc_coarse.json'))['rows']; nd = json.load(open('net/cc_coarse_node.json'))['rows']
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    ax[0].plot([r['res'] for r in cg], [r['Q'] for r in cg], '-o', color=A, ms=4, lw=2, label='실제')
    ax[0].plot([r['res'] for r in cg], [r['Q_null'] for r in cg], '-o', color=MUTED, ms=4, lw=2, label='무작위')
    ax[0].set_title('클러스터 그래프 위 재분할 (폐기)', color=INK); ax[0].set_xlabel('해상도'); ax[0].set_ylabel('모듈성 Q'); ax[0].legend(frameon=False)
    ax[1].plot([r['res'] for r in nd], [r['Q'] for r in nd], '-o', color=A, ms=4, lw=2, label='실제')
    ax[1].plot([r['res'] for r in nd], [r['purity'] for r in nd], '-o', color=B, ms=4, lw=2, label='세부 클러스터 포함 순도')
    ax[1].axvline(RES_C, color=INK, lw=1, ls='--')
    ax[1].set_title(f'효과 그래프 저해상도 분할 (채택 γ={RES_C})', color=INK); ax[1].set_xlabel('해상도'); ax[1].legend(frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig2_resolution_coarse.png'), dpi=200); plt.close(fig)

# fig3 ---------------------------------------------------------------------
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
d = json.load(open('net/effect_sna.json', encoding='utf-8'))
T10 = plt.get_cmap('tab10'); col = lambda cc: T10(cc) if cc < 10 else (0.72, 0.72, 0.72, 1)
fig, ax = plt.subplots(figsize=(13, 8.5))
ax.scatter([n['x'] for n in d['nodes']], [n['y'] for n in d['nodes']], s=0.6, c=[col(n['cc']) for n in d['nodes']], linewidths=0)
for c in d['clusters']:
    ax.add_patch(plt.Circle((c['x'], c['y']), c['r'], fill=False, color=col(c['cc']), lw=0.8))
for co in d['coarse']:
    cs = [d['clusters'][f] for f in co['fine']]; w = sum(c['n'] for c in cs)
    x = sum(c['x'] * c['n'] for c in cs) / w; y = sum(c['y'] * c['n'] for c in cs) / w
    ax.text(x, y, str(co['id'] + 1), ha='center', va='center', fontsize=11 if co['id'] < 10 else 8, fontweight='bold', color=INK,
            path_effects=[pe.withStroke(linewidth=3, foreground='white')])
ax.set_aspect('equal'); ax.axis('off')
hs = [Patch(color=col(co['id']), label=f"{co['id'] + 1}. {co['name']} ({co['n']:,})") for co in d['coarse']]
ax.legend(handles=hs, loc='center left', bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=8.5, title='대분류 (효과 수)', title_fontsize=9.5, alignment='left')
ax.set_title(f"카드 효과 {len(d['nodes']):,}개 · 세부 클러스터 {len(d['clusters'])}(원) · 대분류 {len(d['coarse'])}(색·번호)", loc='left', color=INK)
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig3_effect_map.png'), dpi=200, bbox_inches='tight'); plt.close(fig)

# fig4 ---------------------------------------------------------------------
LT = {'s': '구조가 닮음', 'p': '같은 처리', 't': '같은 유발 조건', 'm': '카드 이름 언급', 'c': '같은 카드', 'q': '같은 Q&A 쟁점'}
cnt = collections.Counter(t for l in d['links'] for t in l[2])
ks = sorted(cnt, key=lambda k: cnt[k])
fig, ax = plt.subplots(figsize=(6, 3))
ax.barh([LT.get(k, k) for k in ks], [cnt[k] for k in ks], color=A, height=0.6)
for i, k in enumerate(ks): ax.text(cnt[k], i, f' {cnt[k]:,}', va='center', fontsize=9, color=INK)
ax.set_title('링크 이유별 개수 (한 링크에 이유 여러 개 가능)', loc='left', color=INK); ax.grid(axis='y', visible=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig4_link_reasons.png'), dpi=200); plt.close(fig)
print('figures ->', OUT, os.listdir(OUT))
