"""E52: does our own model add judgments where the page holds? Joins a training run's per-question test predictions
(test_preds.json, shipped inside the adapter zip) with the page's own judging on the same questions (net/tdec_full.json from
tests/tdec.js, keyed by Q&A index). Thresholds come from gen_info.json (chosen on valid), so nothing is tuned on test.
  python train/complement_eval.py [adapter dir, default server/ai_local_model]  -> paper/results/complement_<name>.json"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'server', 'ai_local_model')
gi = json.load(open(os.path.join(AD, 'gen_info.json'), encoding='utf-8'))
P = {r['id']: r for r in json.load(open(os.path.join(AD, 'test_preds.json'), encoding='utf-8'))}
DEC = {d['i']: d for d in json.load(open(os.path.join(ROOT, 'net', 'tdec_full.json')))}
QA = json.load(open(os.path.join(ROOT, 'test_data4.json'), encoding='utf-8'))['qa']
both = [i for i in P if i in DEC]
page = [i for i in both if DEC[i]['by']]; held = [i for i in both if not DEC[i]['by']]
res = {'model': gi['name'], 'joined': len(both), 'page_decided': len(page),
       'page_acc': round(sum(DEC[i]['ans'] == QA[i][8] for i in page) / max(1, len(page)), 4), 'at': {}}
for tgt, m in gi['metrics']['at'].items():
    thr = m['thr']
    add = [i for i in held if P[i]['conf'] >= thr]
    agree = [i for i in page if P[i]['conf'] >= thr]
    tot_ok = sum(DEC[i]['ans'] == QA[i][8] for i in page) + sum(P[i]['ok'] for i in add)
    res['at'][tgt] = {'thr': thr, 'added_on_held': len(add), 'added_acc': round(sum(P[i]['ok'] for i in add) / max(1, len(add)), 4),
                      'combined_share': round((len(page) + len(add)) / max(1, len(both)), 4),
                      'combined_acc': round(tot_ok / max(1, len(page) + len(add)), 4),
                      'model_vs_page_agree': round(sum(int(P[i]['p'] >= .5) == DEC[i]['ans'] for i in agree) / max(1, len(agree)), 4)}
print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open(os.path.join(ROOT, 'paper', 'results', f"complement_{gi['name']}.json"), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
