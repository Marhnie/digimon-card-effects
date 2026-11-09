"""E31 regression guard: recall of the LIVE server search (/api/search, fused retrievers + 2-gram) on the colloquial test set.

Corpus here is the server's whole Q&A set (not the old+same-card corpus of q_eval_retrieval.py), so the numbers are not comparable with
the E31 tables; use them to see that a deployed model/fusion change did not make colloquial search worse (compare runs of this script).
Gold: same as q_eval_retrieval (A = source or same reason group+polarity or word-identical question; B = the same without the source,
source hits removed from the result list).
  python live_search_check.py [--url http://127.0.0.1:8787] [--limit 200]  -> paper/results/live_search_check.json
"""
import argparse, json, re, sys, time, urllib.request
sys.argv, _argv = sys.argv[:1], sys.argv[1:]
import q_eval_retrieval as E        # gold(), colloquial set (heavy import: builds frames once)

ap = argparse.ArgumentParser()
ap.add_argument('--url', default='http://127.0.0.1:8787')
ap.add_argument('--limit', type=int, default=200)
a = ap.parse_args(_argv)
rows = json.load(open('paper/results/colloquial_test.json', encoding='utf-8'))['items'][:a.limit]


def search(q, k=12, tries=3):
    for t in range(tries):
        try:
            r = urllib.request.Request(a.url + '/api/search', json.dumps({'q': q, 'k': k}).encode(), {'Content-Type': 'application/json'})
            return [h['i'] for h in json.load(urllib.request.urlopen(r, timeout=60))['hits']]
        except Exception as e:
            err = e
            time.sleep(2)
    raise SystemExit(f'search failed: {err}')


res = {m: {1: 0, 3: 0, 10: 0, 'n': 0} for m in 'AB'}
t0 = time.time()
for x in rows:
    for field in ('colloquial',):
        hits = search(x[field])
        for mode in 'AB':
            g = E.gold(x['qid'], mode)
            if not g:
                continue
            hh = [i for i in hits if mode == 'A' or i != x['qid']]
            res[mode]['n'] += 1
            for k in (1, 3, 10):
                res[mode][k] += bool(g & set(hh[:k]))
out = {m: {'n': v['n'], **{f'recall@{k}': round(v[k] / v['n'], 3) if v['n'] else None for k in (1, 3, 10)}} for m, v in res.items()}
out['seconds'] = round(time.time() - t0)
out['url'] = a.url
print(json.dumps(out, ensure_ascii=False))
json.dump(out, open('paper/results/live_search_check.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
