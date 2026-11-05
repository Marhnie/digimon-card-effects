import { appendFileSync, readFileSync } from "node:fs";
import { it } from "vitest";
import { gauntlet, gauntletScore, legalMetaDecks, type Deck } from "#api/ourai/deckTools";

it("score deck files against the gauntlet on one seed", async () => {
  const opponents = gauntlet();
  const games = Number(process.env.OURAI_GAMES ?? 32);
  const seed = Number(process.env.OURAI_EVAL_SEED ?? 200_000_000);
  for (const spec of (process.env.OURAI_DECKS ?? "").split(";").filter(Boolean)) {
    const deck: Deck = spec.startsWith("meta:") ? legalMetaDecks().find((d) => d.name === spec.slice(5))!.deck : (JSON.parse(readFileSync(spec, "utf8")) as Deck);
    const score = await gauntletScore(deck, opponents, games, seed);
    appendFileSync(process.env.OURAI_OUT ?? "vdeck.jsonl", JSON.stringify({ deck: spec, games: games * opponents.length, seed, score }) + "\n");
  }
}, 86_400_000);
