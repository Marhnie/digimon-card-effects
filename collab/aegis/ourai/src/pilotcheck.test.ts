import { appendFileSync, existsSync, readFileSync } from "node:fs";
import { it } from "vitest";
import { currentGauntlet, playSeries } from "#api/ourai/deckTools";

it("compare a tuned pilot with the generic policy on reserved seeds", async () => {
  const field = currentGauntlet().map((n) => ({ name: n.name, deck: n.deck }));
  const games = Number(process.env.OURAI_GAMES ?? 32);
  const seed = Number(process.env.OURAI_EVAL_SEED ?? 1_500_000_000);
  for (const name of (process.env.OURAI_DECKS ?? "").split(";").filter(Boolean)) {
    const me = field.find((n) => n.name === name)!;
    const file = `${process.env.OURAI_PILOT_DIR}/pilot_${name.replace(/[^A-Za-z0-9]+/g, "_")}.json`;
    if (!existsSync(file)) {
      appendFileSync(process.env.OURAI_OUT ?? "pilotcheck.jsonl", JSON.stringify({ deck: name, tuned: false }) + "\n");
      continue;
    }
    const w = JSON.parse(readFileSync(file, "utf8")) as Record<string, number>;
    let tuned = 0;
    let generic = 0;
    for (const [i, o] of field.entries()) {
      tuned += await playSeries(me.deck, o.deck, games, seed + i * 1000, w, undefined);
      generic += await playSeries(me.deck, o.deck, games, seed + i * 1000, undefined, undefined);
    }
    const n = field.length * games;
    appendFileSync(process.env.OURAI_OUT ?? "pilotcheck.jsonl", JSON.stringify({ deck: name, tuned: tuned / n, generic: generic / n, games: n, seed }) + "\n");
  }
}, 86_400_000);
