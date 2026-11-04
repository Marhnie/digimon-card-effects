import { appendFileSync } from "node:fs";
import { it } from "vitest";
import { getCardDefinition } from "@aegis/shared/cards/registry";
import { gauntlet, gauntletScore, makeRandom } from "#api/ourai/deckTools";
import { bossCandidates, buildDeck } from "#api/ourai/buildDeck";

const N = Number(process.env.OURAI_N ?? 40);
const OUT = process.env.OURAI_OUT ?? "scratch.jsonl";
const SEED = Number(process.env.OURAI_SEED ?? 3);

it("build decks from scratch and score them", async () => {
  const opponents = gauntlet();
  const bosses = bossCandidates();
  const rnd = makeRandom(SEED);
  console.log("BOSSES", bosses.length);
  for (let i = 0; i < N; i++) {
    const boss = bosses[Math.floor(rnd() * bosses.length)]!;
    const deck = buildDeck(boss.cardId, rnd);
    if (!deck) {
      appendFileSync(OUT, JSON.stringify({ boss: boss.cardId, ok: false }) + "\n");
      continue;
    }
    const score = await gauntletScore(deck, opponents, 4, 600_000 + i * 1000);
    const row = { boss: boss.cardId, name: boss.nameEn, colors: boss.colors, ok: true, score, deck };
    appendFileSync(OUT, JSON.stringify(row) + "\n");
    console.log("BUILT", boss.cardId, getCardDefinition(boss.cardId)?.nameEn, score);
  }
}, 86_400_000);
