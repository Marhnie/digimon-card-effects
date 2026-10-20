import json, sys
S = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'struct.json', encoding='utf8'))
ids = json.load(open(sys.argv[1]))
for i in ids:
    s = S[i]; print('#%d %s' % (i, s['text'][:150].replace('\n', ' ')))
    for n, p in enumerate(s['처리']):
        print('  %d %s|%s|%s|%s|%s|%s|%s|%s%s' % (n + 1, p['text'][:60], ','.join(p['acts']), '임' if p['임의'] else '강', p['scope'][:3], p['target'], p['side'], ','.join(p['filters']), p['dur'][:4], '|' + p['선택지'] if '선택지' in p else ''))
