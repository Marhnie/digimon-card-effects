"""python -X utf8 score_duel.py "C:/Users/Daewonmedia/ourai_data/duel_TAG_*.jsonl"  -> win rate, two-sided binomial p, Wilson CI, per-pair and per-deck."""
import collections, glob, json, math, sys

R = [json.loads(l) for f in sorted(glob.glob(sys.argv[1])) for l in open(f, encoding='utf-8') if l.strip()]
dec = [r for r in R if r['oursWon'] is not None and r['errors'] == 0]
w, n = sum(r['oursWon'] for r in dec), len(dec)


def binom_two_sided(k, n):
    pk = math.comb(n, k) / 2 ** n
    return min(1.0, sum(math.comb(n, i) / 2 ** n for i in range(n + 1) if math.comb(n, i) / 2 ** n <= pk + 1e-12))


def wilson(k, n, z=1.96):
    p = k / n; c = (p + z * z / 2 / n) / (1 + z * z / n); h = z * math.sqrt(p * (1 - p) / n + z * z / 4 / n / n) / (1 + z * z / n)
    return round(c - h, 3), round(c + h, 3)


print('games', len(R), 'decisive', n, 'draws/timeouts', len(R) - n - sum(r['errors'] > 0 for r in R), 'errors', sum(r['errors'] > 0 for r in R))
print(f'ours {w}/{n} = {w / n:.3f}  CI {wilson(w, n)}  two-sided p = {binom_two_sided(w, n):.4f}')
pairs = collections.defaultdict(list)
for r in dec: pairs[(r['seed'], tuple(sorted(r['decks'])))].append(r['oursWon'])
full = [v for v in pairs.values() if len(v) == 2]
print('pairs complete', len(full), 'ours 2-0', sum(v == [True, True] for v in full), 'split', sum(v[0] != v[1] for v in full), '0-2', sum(v == [False, False] for v in full))
print('first player (seat 0) win rate', round(sum(r['winner'] == 0 for r in dec) / n, 3))
fb = [sum(x[1].get('deadline', 0) + x[1].get('capacity', 0) + x[1].get('error', 0) for x in r['fallbacks']) for r in R]
print('search fallbacks per game mean', round(sum(fb) / len(fb), 2), 'max', max(fb))
by = collections.defaultdict(lambda: [0, 0])
for r in dec:
    d = r['decks'][r['oursSeat']]; by[d][0] += r['oursWon']; by[d][1] += 1
print('ours by deck piloted:', {k: f'{a}/{b}' for k, (a, b) in sorted(by.items())})
