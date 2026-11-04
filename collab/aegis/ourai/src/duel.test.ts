import { appendFileSync } from "node:fs";
import { it } from "vitest";
import type { Seat } from "@aegis/shared";
import { BotDifficulty } from "@aegis/shared/bot/BotDifficulty";
import { BotStyle } from "@aegis/shared/bot/BotStyle";
import { runBotMatch } from "#api/bot/matchHarness";
import { mainActionReady } from "#api/bot/training/actions";
import { LEVEL_SEARCH_POLICY_TIMEOUT_MS } from "#api/bot/levels/LEVEL_SEARCH_POLICY_TIMEOUT_MS";
import digilabDecks from "#api/bot/evolution/digilab-decks.json" with { type: "json" };
import { evolutionDeck } from "#api/bot/evolution/decks";
import { createOurBotOptions } from "#api/ourai/createOurBotOptions";
import { prewarmLiveSearchWorkers } from "#api/bot/search/prewarmLiveSearchWorkers";

const GAMES = Number(process.env.OURAI_GAMES ?? 4);
const SEED = Number(process.env.OURAI_SEED ?? 5000);
const OUT = process.env.OURAI_OUT ?? "duel.jsonl";
const LEVEL = (process.env.OURAI_LEVEL ?? BotDifficulty.MASTER.value) as BotDifficulty;

it("duel: our value vs aegis value on the same search", async () => {
  console.log("CONFIG", process.env.OURAI_DEPTH, process.env.OURAI_SIMS, process.env.OURAI_CAND);
  const decks = digilabDecks.decks.flatMap((d) => {
    try {
      return [evolutionDeck(d.deckVersion)];
    } catch {
      return [];
    }
  });
  await prewarmLiveSearchWorkers();
  for (let g = 0; g < GAMES; g++) {
    const pair = Math.floor(g / 2);
    const seed = SEED + pair;
    const pick = [decks[(seed * 7) % decks.length]!, decks[(seed * 13 + 5) % decks.length]!];
    const oursSeat = (g % 2) as Seat;
    const t0 = Date.now();
    const result = await runBotMatch({
      seed,
      firstSeat: 0,
      measureDecisionLatencies: true,
      seats: [0, 1].map((s) => ({
        deck: pick[s]!.deck,
        label: s === oursSeat ? "ours" : "aegis",
        policyTimeoutMs: LEVEL_SEARCH_POLICY_TIMEOUT_MS,
        canChooseMainAction: (engine) => mainActionReady(engine),
        policyFactory: (engine) =>
          createOurBotOptions({
            engine,
            seat: s as Seat,
            deck: pick[s]!.deck,
            seed: seed + s * 7919,
            difficulty: LEVEL,
            style: BotStyle.BALANCED.value,
            useOurValue: s === oursSeat,
          }).policy!,
      })) as never,
    });
    const row = {
      seed, g, level: LEVEL, oursSeat, decks: pick.map((d) => d.name), winner: result.winnerSeat,
      oursWon: result.winnerSeat === undefined ? null : result.winnerSeat === oursSeat,
      lat: result.seats.map((x) => { const v = [...x.decisionLatenciesMs].sort((a, b) => a - b); return v.length ? Math.round(v[Math.floor(v.length / 2)]!) : null; }),
      turns: result.turnCount, errors: result.errors.length, ms: Date.now() - t0,
      fallbacks: result.seats.map((x) => [x.inferenceFallbacks, x.searchFallbacks, x.searchErrors]),
    };
    appendFileSync(OUT, JSON.stringify(row) + "\n");
    console.log("DUEL", JSON.stringify(row));
  }
}, 86_400_000);
