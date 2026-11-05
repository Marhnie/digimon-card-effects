import { appendFileSync, existsSync, readFileSync } from "node:fs";
import { it } from "vitest";
import type { Seat } from "@aegis/shared";
import { runBotMatch } from "#api/bot/matchHarness";
import { createEvaluationPolicy } from "#api/bot/policy";
import { BOT_PROFILES, type BotProfile } from "#api/bot/profiles";
import { mainActionReady } from "#api/bot/training/actions";
import { gauntlet, makeRandom } from "#api/ourai/deckTools";

type W = Record<string, number>;
const OUT = process.env.OURAI_OUT ?? "tune.jsonl";
const SEED = Number(process.env.OURAI_SEED ?? 1);
const ITERS = Number(process.env.OURAI_ITERS ?? 200);
const SCREEN = Number(process.env.OURAI_SCREEN ?? 64);
const CONFIRM = Number(process.env.OURAI_CONFIRM ?? 96);
const FIXED = new Set(["lethal"]);
const ADDITIVE = new Set(["blockThreshold", "barrierThreshold", "actionThreshold", "deployLevel"]);

async function series(a: W, b: W, games: number, seed: number): Promise<number> {
  const decks = gauntlet();
  let wins = 0;
  for (let g = 0; g < games; g++) {
    const s = seed + Math.floor(g / 4);
    const r = makeRandom(s);
    const d1 = decks[Math.floor(r() * decks.length)]!.deck;
    const d2 = decks[Math.floor(r() * decks.length)]!.deck;
    const aDeck = g % 4 < 2 ? d1 : d2;
    const bDeck = g % 4 < 2 ? d2 : d1;
    const aSeat = (g % 2) as Seat;
    const prof = (w: W): BotProfile => ({ ...BOT_PROFILES.balanced, weights: w as never });
    const result = await runBotMatch({
      seed: s,
      firstSeat: 0,
      seats: [0, 1].map((k) => ({
        deck: k === aSeat ? aDeck : bDeck,
        label: k === aSeat ? "a" : "b",
        canChooseMainAction: (engine) => mainActionReady(engine),
        policyFactory: () => createEvaluationPolicy({ profile: prof(k === aSeat ? a : b), seed: s * 2 + k }),
      })) as never,
    });
    if (result.winnerSeat === aSeat) wins += 1;
    else if (result.winnerSeat === undefined) wins += 0.5;
  }
  return wins / games;
}

it("evaluate weights vs balanced", async () => {
  const a: W = JSON.parse(readFileSync(process.env.OURAI_A!, "utf8"));
  const b: W = existsSync(process.env.OURAI_B ?? "") ? JSON.parse(readFileSync(process.env.OURAI_B!, "utf8")) : { ...(BOT_PROFILES.balanced.weights as unknown as W) };
  const games = Number(process.env.OURAI_GAMES ?? 200);
  const t0 = Date.now();
  const score = await series(a, b, games, Number(process.env.OURAI_EVAL_SEED ?? 20_000_000));
  appendFileSync(OUT, JSON.stringify({ a: process.env.OURAI_A, b: process.env.OURAI_B ?? "balanced", games, score, ms: Date.now() - t0 }) + "\n");
}, 86_400_000);
