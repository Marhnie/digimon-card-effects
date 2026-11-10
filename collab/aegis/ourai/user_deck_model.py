# 유저 레시피(DigiLab 1위 덱 22개) 학습 → 새 출발 덱 생성.
# 모델: 카드 동시출현 조건부 샘플링. 다음 카드 확률 ∝ Σ_{고른 카드 c} cooc(c,x) + α·freq(x).
# 장수: 그 카드가 유저 덱에 들어간 장수 분포에서 샘플. 디지타마: 메인과 가장 많이 겹치는 유저 덱의 디지타마.
import json, random, collections, sys, os
SRC = "C:/Users/Daewonmedia/aegis_engine/apps/api/src/bot/evolution/digilab-decks.json"
OUT = "C:/Users/Daewonmedia/ourai_data/routes"
ALPHA = 0.3
decks = [d["decklist"] for d in json.load(open(SRC, encoding="utf8"))["decks"]]
mains = [collections.Counter(d["mainDeck"]) for d in decks]
freq = collections.Counter(); copies = collections.defaultdict(list); cooc = collections.defaultdict(collections.Counter)
for m in mains:
    for a, n in m.items():
        freq[a] += 1; copies[a].append(n)
        for b in m:
            if a != b: cooc[a][b] += 1
cards = sorted(freq)
def gen(rnd):
    chosen = collections.Counter()
    first = rnd.choices(cards, weights=[freq[c] for c in cards])[0]
    while sum(chosen.values()) < 50:
        if not chosen: x = first
        else:
            cand = [c for c in cards if c not in chosen]
            w = [sum(cooc[c0][c] for c0 in chosen) + ALPHA * freq[c] for c in cand]
            x = rnd.choices(cand, weights=w)[0]
        n = min(rnd.choice(copies[x]), 4, 50 - sum(chosen.values()))
        chosen[x] = n
    best = max(range(len(decks)), key=lambda i: sum(min(chosen[c], mains[i][c]) for c in chosen))
    return {"mainDeck": sorted(chosen.elements()), "eggDeck": list(decks[best]["eggDeck"])}
if __name__ == "__main__":
    routes, per = int(sys.argv[1]), int(sys.argv[2])
    for r in range(1, routes + 1):
        rnd = random.Random(7000 + r)
        os.makedirs(f"{OUT}/r{r}", exist_ok=True)
        for k in range(per):
            json.dump(gen(rnd), open(f"{OUT}/r{r}/u{k}.json", "w"))
    print("ok", routes, per, "cards", len(cards))
