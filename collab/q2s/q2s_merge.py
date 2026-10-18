import json, glob, os
H = os.path.dirname(os.path.abspath(__file__))
merged = {}
for f in sorted(glob.glob(os.path.join(H, 'out', 'batch*.json'))):
    for it in json.load(open(f, encoding='utf-8')):
        merged[it['id']] = it
for f in sorted(glob.glob(os.path.join(H, 'out', 'rerun*.json'))):
    for it in json.load(open(f, encoding='utf-8')):
        merged[it['id']] = it
items = [merged[k] for k in sorted(merged)]
json.dump(items, open(os.path.join(H, 'merged.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
os.makedirs(os.path.join(H, '..', 'jobs', 'q2s'), exist_ok=True)
n = 0
ids = []
for it in items:
    if it['status'] == 'ok':
        j = it['job']
        j['id'] = 'q%s' % it['id']
        j.setdefault('timeScale', 20)
        json.dump(j, open(os.path.join(H, '..', 'jobs', 'q2s', 'q%s.json' % it['id']), 'w', encoding='utf-8'), ensure_ascii=False)
        ids.append('q%s' % it['id'])
        n += 1
open(os.path.join(H, 'run_list.txt'), 'w').write('\n'.join(ids))
print('items', len(items), 'ok', n)
