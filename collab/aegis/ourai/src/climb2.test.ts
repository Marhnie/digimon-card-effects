import { appendFileSync, readFileSync } from "node:fs";
import { it } from "vitest";
import { colorPool, deckLegal, gauntlet, gauntletScore, legalMetaDecks, makeRandom, mutate, type Deck } from "#api/ourai/deckTools";

const START = process.env.OURAI_START ?? "TS Mervamon";
const ITERS = Number(process.env.OURAI_ITERS ?? 60);
const SEED = Number(process.env.OURAI_SEED ?? 1);
const OUT = process.env.OURAI_OUT ?? "climb2.jsonl";
const SEARCH_GAMES = 4;
const CONFIRM_GAMES = 16;

it("deck hill climb with paired fresh seeds", async () => {
  const opponents = gauntlet();
  const start: Deck = process.env.OURAI_START_DECK_FILE ? (JSON.parse(readFileSync(process.env.OURAI_START_DECK_FILE, "utf8")) as Deck) : legalMetaDecks().find((d) => d.name === START)!.deck;
  const pool = colorPool(start);
  const rnd = makeRandom(SEED * 7919 + 13);
  let seed = 60_000_000 + SEED * 1_000_000;
  let champion: Deck = start;
  appendFileSync(OUT, JSON.stringify({ it: 0, start: START, deck: champion, pool: pool.length }) + "\n");
  for (let i = 1; i <= ITERS; i++) {
    const cand = mutate(champion, pool, rnd);
    if (cand === champion || !deckLegal(cand)) continue;
    seed += 10_000;
    const search: [number, number] = [await gauntletScore(champion, opponents, SEARCH_GAMES, seed), await gauntletScore(cand, opponents, SEARCH_GAMES, seed)];
    let confirm: [number, number] | undefined;
    let accepted = false;
    if (search[1] >= search[0] + 0.06) {
      seed += 10_000;
      confirm = [await gauntletScore(champion, opponents, CONFIRM_GAMES, seed), await gauntletScore(cand, opponents, CONFIRM_GAMES, seed)];
      if (confirm[1] > confirm[0] + 0.03) {
        champion = cand;
        accepted = true;
      }
    }
    appendFileSync(OUT, JSON.stringify({ it: i, search, confirm, accepted, deck: accepted ? champion : undefined }) + "\n");
  }
}, 86_400_000);
