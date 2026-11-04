import { appendFileSync, readFileSync } from "node:fs";
import { it } from "vitest";
import { gauntlet, legalMetaDecks, playSeries } from "#api/ourai/deckTools";

// Fresh-seed check of a climbed deck: original vs champion, same seeds per opponent.
it("validate climbed deck on fresh seeds", async () => {
  const name = process.env.OURAI_START!;
  const champ = (JSON.parse(readFileSync(process.env.OURAI_CHAMPS!, "utf8")) as Record<string, never>)[name]!;
  const orig = legalMetaDecks().find((d) => d.name === name)!.deck;
  const games = Number(process.env.OURAI_GAMES ?? 16);
  const seed = Number(process.env.OURAI_SEED ?? 3_000_000);
  for (const [i, o] of gauntlet().entries()) {
    const s = seed + i * 1000;
    const a = await playSeries(orig, o.deck, games, s);
    const b = await playSeries(champ, o.deck, games, s);
    appendFileSync(process.env.OURAI_OUT!, JSON.stringify({ deck: name, opp: o.name, games, orig: a, champ: b }) + "\n");
  }
}, 86_400_000);
