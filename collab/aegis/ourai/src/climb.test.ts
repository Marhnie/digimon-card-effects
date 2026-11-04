import { appendFileSync } from "node:fs";
import { it } from "vitest";
import { colorPool, deckLegal, gauntlet, gauntletScore, legalMetaDecks, makeRandom, mutate, type Deck } from "#api/ourai/deckTools";

const START = process.env.OURAI_START ?? "TS Mervamon";
const ITERS = Number(process.env.OURAI_ITERS ?? 120);
const SEED = Number(process.env.OURAI_SEED ?? 1);
const OUT = process.env.OURAI_OUT ?? "climb.jsonl";
const SEARCH_GAMES = 4;
const CONFIRM_GAMES = 8;

it("deck hill climb against the meta gauntlet", async () => {
  const opponents = gauntlet();
  const start = process.env.OURAI_START_DECK
    ? (JSON.parse(process.env.OURAI_START_DECK) as Deck)
    : legalMetaDecks().find((d) => d.name === START)!.deck;
  const pool = colorPool(start);
  const rnd = makeRandom(SEED * 7919);
  const searchSeed = 500_000 + SEED * 10_000;
  let champion = start;
  let score = await gauntletScore(champion, opponents, SEARCH_GAMES, searchSeed);
  let confirmSeed = 900_000 + SEED * 100_000;
  appendFileSync(OUT, JSON.stringify({ it: 0, start: START, score, deck: champion, pool: pool.length }) + "\n");
  for (let i = 1; i <= ITERS; i++) {
    const cand = mutate(champion, pool, rnd);
    if (cand === champion || !deckLegal(cand)) continue;
    const s = await gauntletScore(cand, opponents, SEARCH_GAMES, searchSeed);
    let accepted = false;
    let confirm: [number, number] | undefined;
    if (s > score + 0.02) {
      confirmSeed += 10_000;
      confirm = [
        await gauntletScore(champion, opponents, CONFIRM_GAMES, confirmSeed),
        await gauntletScore(cand, opponents, CONFIRM_GAMES, confirmSeed),
      ];
      if (confirm[1] > confirm[0]) {
        champion = cand;
        score = s;
        accepted = true;
      }
    }
    appendFileSync(OUT, JSON.stringify({ it: i, s, score, accepted, confirm, deck: accepted ? champion : undefined, cand: accepted ? undefined : cand.mainDeck.filter((x, k, a) => a.indexOf(x) === k).length }) + "\n");
  }
}, 86_400_000);
