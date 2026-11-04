import { appendFileSync } from "node:fs";
import { it } from "vitest";
import type { Seat } from "@aegis/shared";
import { BotDifficulty } from "@aegis/shared/bot/BotDifficulty";
import { BotStyle } from "@aegis/shared/bot/BotStyle";
import { runBotMatch } from "#api/bot/matchHarness";
import { mainActionReady } from "#api/bot/training/actions";
import { trainingObservation } from "#api/bot/training/observation";
import { LEVEL_SEARCH_POLICY_TIMEOUT_MS } from "#api/bot/levels/LEVEL_SEARCH_POLICY_TIMEOUT_MS";
import { prewarmLiveSearchWorkers } from "#api/bot/search/prewarmLiveSearchWorkers";
import { evaluateSearchPosition } from "#api/bot/evolution/evaluateSearchPosition";
import { createOurBotOptions } from "#api/ourai/createOurBotOptions";
import { legalMetaDecks } from "#api/ourai/deckTools";
import { positionFeatures, positionFeatures2 } from "#api/ourai/features";

const GAMES = Number(process.env.OURAI_GAMES ?? 4);
const SEED = Number(process.env.OURAI_SEED ?? 1);
const OUT = process.env.OURAI_OUT ?? "selfplay.jsonl";

it("search self-play with our value on both seats", async () => {
  await prewarmLiveSearchWorkers();
  const decks = legalMetaDecks();
  for (let g = 0; g < GAMES; g++) {
    const seed = SEED + g;
    const pick = [decks[(seed * 7) % decks.length]!, decks[(seed * 11 + 3) % decks.length]!];
    const rows: { seat: Seat; turn: number; x: number[]; x2: number[]; b: number }[] = [];
    const seen = new Set<number>();
    const result = await runBotMatch({
      seed,
      firstSeat: (g % 2) as Seat,
      seats: [0, 1].map((s) => ({
        deck: pick[s]!.deck,
        label: pick[s]!.name,
        policyTimeoutMs: LEVEL_SEARCH_POLICY_TIMEOUT_MS,
        canChooseMainAction: (engine) => mainActionReady(engine),
        policyFactory: (engine) => {
          const base = createOurBotOptions({
            engine, seat: s as Seat, deck: pick[s]!.deck, seed: seed * 2 + s,
            difficulty: BotDifficulty.MASTER.value, style: BotStyle.BALANCED.value, useOurValue: true,
          }).policy!;
          return {
            ...base,
            chooseMainAction: (view, signal) => {
              if (!seen.has(engine.state.turnCount)) {
                seen.add(engine.state.turnCount);
                for (const seat of [0, 1] as Seat[]) {
                  const o = trainingObservation(engine.state, seat);
                  rows.push({ seat, turn: engine.state.turnCount, x: positionFeatures(o), x2: positionFeatures2(o), b: evaluateSearchPosition(o) });
                }
              }
              return base.chooseMainAction(view, signal);
            },
          };
        },
      })) as never,
    });
    if (result.winnerSeat === undefined || result.errors.length > 0) continue;
    appendFileSync(OUT, rows.map((r) => JSON.stringify({ g: seed, src: "v1search", d: [pick[r.seat]!.name, pick[1 - r.seat]!.name], t: r.turn, y: r.seat === result.winnerSeat ? 1 : 0, b: r.b, x: r.x, x2: r.x2 })).join("\n") + "\n");
    console.log("GAME", seed, result.turnCount, result.winnerSeat);
  }
}, 86_400_000);
