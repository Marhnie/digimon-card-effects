"""Fig 6: pipeline diagram (sections 2.1-2.4, 2.10, 2.15 of 02_방법.md)."""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams['font.family'] = 'Malgun Gothic'
INK, MUTED, EDGE = '#0b0b0b', '#52514e', '#b9b8b0'
FILL = {'data': '#eef4fc', 'route': '#f4f3ef', 'held': '#fdf0e9', 'human': '#e9f7f1'}

fig, ax = plt.subplots(figsize=(10, 6.6), dpi=200)
ax.set_xlim(0, 100); ax.set_ylim(0, 66); ax.axis('off')

def box(x, y, w, h, text, kind='route', size=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=.8',
                                fc=FILL[kind], ec=EDGE, lw=.8))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=size, color=INK, linespacing=1.35)

def arrow(a, b, style='-', rad=0):
    ax.annotate('', xy=b, xytext=a, arrowprops=dict(arrowstyle='-|>', color=MUTED, lw=1, ls=style,
                                                    connectionstyle=f'arc3,rad={rad}', shrinkA=0, shrinkB=0))

def head(x, text):
    ax.text(x, 64, text, ha='center', fontsize=10.5, fontweight='bold', color=INK)

# left: knowledge base
head(14, '지식 구축')
L = [(52, '카드 텍스트 3,852종\n종합 룰 1,138조항\n공식 Q&A 6,047문항'),
     (40, '효과 단위 분할\n8,936개'),
     (28, '룰북 15장 구조 분해\n부품마다 근거 조항 연결'),
     (16, 'Q&A–효과 연결\n쟁점 그룹·이유 묶음')]
for y, t in L:
    box(2, y, 24, 9, t, 'data')
for (y0, _), (y1, _) in zip(L, L[1:]):
    arrow((14, y0), (14, y1 + 9))

# middle: decision routes
head(50, '판정 경로 (앞 경로가 답하면 종료)')
box(36, 58, 28, 4, '질문', 'route')
R = ['1  공식 선례 (같은 상황, 답 만장일치)', '2  확인된 판정 (같은 카드, 유사 질문)',
     '3  룰 쟁점 (예시 답 일치)', '4  엔진 (확신 ≥ 0.80)', '5  의미 검색 (코사인 ≥ 0.885, 서버판)']
ys = [50, 42, 34, 26, 18]
for y, t in zip(ys, R):
    box(33, y, 34, 5.6, t)
arrow((50, 58), (50, 55.6))
for a, b in zip(ys, ys[1:]):
    arrow((50, a), (50, b + 5.6))
arrow((26, 34), (33, 34), rad=0)
ax.text(30.5, 35.2, '근거', ha='center', fontsize=8, color=MUTED)

# right: output
head(84, '출력')
box(73, 34, 24, 9, '판정 표시\n근거 Q&A·조항과 함께', 'human')
for y in ys:
    arrow((67, y + 2.8), (73, 38.5))
box(33, 6, 34, 7, '판정 보류 · 심판 확인 필요', 'held')
arrow((50, 18), (50, 13))
box(73, 16, 24, 9, 'Claude 초안 (운영자)\nq15_v2 의견 (자동 판정 아님)', 'held', 8.5)
box(73, 4, 24, 8, '심판 확인', 'human')
arrow((67, 10), (73, 20))
arrow((85, 16), (85, 12))
ax.plot([73, 27.5, 27.5], [5.2, 5.2, 44.8], color=MUTED, lw=1, ls='--')
arrow((27.5, 44.8), (33, 44.8), '--')
ax.text(50, 3.4, '확인된 판정으로 저장', ha='center', fontsize=8, color=MUTED)

fig.savefig(os.path.join(HERE, 'figures', 'fig6_pipeline.png'), bbox_inches='tight', facecolor='white')
