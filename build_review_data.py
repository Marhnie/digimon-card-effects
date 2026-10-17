"""Review-page data from struct2.json.
usage: python build_review_data.py            -> review_data41.json : gold-set items whose v4.1 analysis differs from the v4.0 snapshot (review_data.json)
The v4.0 page keeps review_data.json unchanged so its reviewers stay comparable."""
import json, re, collections
S = json.load(open('struct2.json', encoding='utf-8'))
CARDS = {c['no']: c for c in json.load(open('cards.json', encoding='utf-8'))}
cn = lambda no: re.sub(r'^\S+\s*', '', CARDS[no]['name']) if no in CARDS else no
mask = lambda s: re.sub(r'「[^「」]*」', '「X」', s or '')

def step(p):
    return {'acts': p['acts'], 'opt': p['임의'], 'scope': p.get('scope', ''), 'dur': p.get('dur', ''), 'tg': p.get('target', ''), 'side': p.get('side', ''),
            'f': p.get('filters', []), 't': mask(p['text'])}

def item(n, s):
    return {'n': n, 'i': s['i'], 'card': s['card'], 'name': cn(s['card']), 'src': s['출처'], 'text': s['text'], 'cls': s['분류'], 'sub': s.get('세부', ''),
            'tm': s.get('타이밍', []), 'ic': s.get('아이콘', []), 'tk': s.get('유발 키', ''), 'tc': s.get('유발 조건', ''),
            'cond': s.get('처리 조건', []), 'cost': [c['text'] for c in s.get('임의 처리 조건', [])], 'steps': [step(p) for p in s.get('처리', [])],
            'extra': [{'cls': e['분류'], 'cond': e['조건'], 'steps': [step(p) for p in e['처리']]} for e in s.get('부가 효과', [])],
            'pre': s.get('카드 정보', '')}

def sig(x):   # what a reviewer sees and judges
    return (x['cls'], x.get('tc', ''), tuple(x['cond']), tuple(x['cost']),
            tuple((p['opt'], tuple(p['acts']), p.get('tg', ''), p.get('side', '')) for p in x['steps']),
            tuple((e['cond'], tuple(a for p in e['steps'] for a in p['acts'])) for e in x.get('extra', [])))

if __name__ == '__main__':
    old = json.load(open('review_data.json', encoding='utf-8'))
    byi = {s['i']: s for s in S}
    changed = []
    for x in old['items']:
        new = item(x['n'], byi[x['i']])
        if sig(new) != sig({**x, 'extra': []}): changed.append(new)
    pop = collections.Counter(s['분류'] for s in S)
    json.dump({'items': changed, 'pop': pop, 'rv': 'rv41', 'title': 'v4.2 재검수',
               'intro': f'정답셋 300문항 중 v4.2(검수자 A·B·C 지적 반영)에서 자동 분석이 바뀐 {len(changed)}문항만 다시 봅니다. 문항 번호는 정답셋 번호 그대로입니다.'},
              open('review_data41.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('바뀐 문항', len(changed), [x['n'] for x in changed])
