"""E51 follow-up: how often do judges agree with the AI opinions?  Read-only report on server/judge.db.

  python server/ai_agreement.py [--db path] [--json]

Sources: ai_cache (every opinion: model, ans, confidence), ai_spend (cost), drafts (kind 'ai': open / approved / dropped),
rulings (origin 'draft', src 'claude', agreed = the judge kept the AI yes/no). Joined by the cache key  q|cards|model .
Reports per model and per confidence: opinions, unsure (ans null) share, judge-reviewed count, agreement with a Wilson 95 % CI,
drops, and spend. Agreement counts only opinions with a yes/no (ans 1/0); a dropped draft is counted separately (not agreement).
"""
import argparse, json, math, os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]


def report(db_path):
    c = sqlite3.connect('file:' + db_path.replace('\\', '/') + '?mode=ro', uri=True)
    have = {r[0] for r in c.execute("select name from sqlite_master where type='table'")}
    cache = {}
    if 'ai_cache' in have:
        for key, doc, at in c.execute('select key, doc, at from ai_cache'):
            base, _, model = key.rpartition('|')
            d = json.loads(doc)
            cache[base] = {**d, 'model': d.get('model') or model, 'at': at}
    spend = c.execute('select coalesce(sum(usd),0), count(*) from ai_spend').fetchone() if 'ai_spend' in have else (0, 0)
    drafts = {'open': 0, 'approved': 0, 'dropped': 0}
    if 'drafts' in have:
        for (doc, st) in c.execute('select doc, status from drafts'):
            if json.loads(doc).get('kind') == 'ai':
                drafts[st] = drafts.get(st, 0) + 1
    rulings = []
    if 'rulings' in have:
        for (doc,) in c.execute('select doc from rulings'):
            d = json.loads(doc)
            if d.get('origin') == 'draft' and d.get('src') == 'claude' and 'AI 의견' in (d.get('note') or ''):
                rulings.append(d)
    rows = {}

    def bucket(model, conf):
        return rows.setdefault((model, conf), {'opinions': 0, 'unsure': 0, 'reviewed': 0, 'agree': 0})

    for d in cache.values():
        b = bucket(d.get('model'), d.get('confidence') or '-')
        b['opinions'] += 1
        b['unsure'] += d.get('ans') is None
    unmatched = 0
    for r in rulings:
        cards = ','.join([r.get('card') or ''] + [x for x in (r.get('others') or '').split(',') if x])
        d = cache.get((r.get('q') or '').strip()[:600] + '|' + cards)
        if not d:
            unmatched += 1
            continue
        b = bucket(d.get('model'), d.get('confidence') or '-')
        if d.get('ans') in (0, 1):
            b['reviewed'] += 1
            b['agree'] += bool(r.get('agreed'))
    out = []
    for (m, cf), b in sorted(rows.items(), key=lambda x: (str(x[0][0]), str(x[0][1]))):
        out.append({'model': m, 'confidence': cf, **b, 'agree_rate': round(b['agree'] / b['reviewed'], 3) if b['reviewed'] else None,
                    'agree_ci95': wilson(b['agree'], b['reviewed'])})
    tot = {k: sum(b[k] for b in rows.values()) for k in ('opinions', 'unsure', 'reviewed', 'agree')}
    return {'opinions': tot['opinions'], 'unsure_share': round(tot['unsure'] / tot['opinions'], 3) if tot['opinions'] else None,
            'drafts': drafts, 'judge_reviewed_with_answer': tot['reviewed'], 'agree': tot['agree'],
            'agree_rate': round(tot['agree'] / tot['reviewed'], 3) if tot['reviewed'] else None, 'agree_ci95': wilson(tot['agree'], tot['reviewed']),
            'spend_usd': round(spend[0], 3), 'spend_calls': spend[1], 'rulings_unmatched_to_cache': unmatched, 'by_model_confidence': out}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(os.environ.get('JUDGE_DATA', HERE), 'judge.db'))
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(a.db):
        sys.exit('no database: ' + a.db)
    r = report(a.db)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit()
    print(f"AI 의견 {r['opinions']}건 (판단 불가 {r['unsure_share']}) · 지출 {r['spend_usd']}달러/{r['spend_calls']}회 · 초안 {r['drafts']}")
    print(f"심판 검토(네/아니요) {r['judge_reviewed_with_answer']}건 중 동의 {r['agree']}건 = {r['agree_rate']} (95% 구간 {r['agree_ci95']})")
    for x in r['by_model_confidence']:
        print(f"  {x['model']} / 확신 {x['confidence']}: 의견 {x['opinions']} · 판단불가 {x['unsure']} · 검토 {x['reviewed']} · 동의 {x['agree']} ({x['agree_rate']}, {x['agree_ci95']})")
