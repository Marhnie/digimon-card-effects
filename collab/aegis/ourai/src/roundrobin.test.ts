import { writeFileSync } from "node:fs";
import { it } from "vitest";
import { gauntlet, playSeries } from "#api/ourai/deckTools";

const GAMES = Number(process.env.OURAI_GAMES ?? 10);

it("meta round robin", async () => {
  const g = gauntlet();
  const m: Record<string, Record<string, number>> = {};
  for (const [i, a] of g.entries()) {
    m[a.name] = {};
    for (const [j, b] of g.entries()) {
      if (j <= i) continue;
      const w = await playSeries(a.deck, b.deck, GAMES, 300_000 + i * 100 + j);
      m[a.name]![b.name] = w / GAMES;
    }
    console.log("ROW", a.name, JSON.stringify(m[a.name]));
  }
  writeFileSync(process.env.OURAI_OUT ?? "rr.json", JSON.stringify({ games: GAMES, decks: g.map((x) => x.name), m }));
}, 86_400_000);
