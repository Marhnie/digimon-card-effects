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

it("tune evaluation-policy weights by self-play", async () => {
  const rnd = makeRandom(SEED * 104729);
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());
  let champ: W = existsSync(process.env.OURAI_START_W ?? "") ? JSON.parse(readFileSync(process.env.OURAI_START_W!, "utf8")) : { ...(BOT_PROFILES.balanced.weights as unknown as W) };
  const keys = Object.keys(champ).filter((k) => !FIXED.has(k));
  let seed = 7_000_000 + SEED * 1_000_000;
  appendFileSync(OUT, JSON.stringify({ it: 0, champ }) + "\n");
  for (let i = 1; i <= ITERS; i++) {
    const cand = { ...champ };
    const changed: string[] = [];
    for (let m = 0; m < 3; m++) {
      const k = keys[Math.floor(rnd() * keys.length)]!;
      changed.push(k);
      cand[k] = ADDITIVE.has(k) ? (k === "deployLevel" ? Math.min(6, Math.max(3, Math.round(cand[k]! + (rnd() < 0.5 ? -1 : 1)))) : cand[k]! + gauss()) : cand[k]! * Math.exp(0.35 * gauss());
    }
    const t0 = Date.now();
    seed += 1000;
    const s = await series(cand, champ, SCREEN, seed);
    let c: number | undefined;
    if (s >= 0.55) {
      seed += 1000;
      c = await series(cand, champ, CONFIRM, seed);
      if (c > 0.53) champ = cand;
    }
    appendFileSync(OUT, JSON.stringify({ it: i, changed, screen: s, confirm: c, accepted: c !== undefined && c > 0.53, champ: c !== undefined && c > 0.53 ? champ : undefined, ms: Date.now() - t0 }) + "\n");
  }
}, 86_400_000);
