import { appendFileSync } from "node:fs";
import { it } from "vitest";
import type { Seat } from "@aegis/shared";
import { runBotMatch } from "#api/bot/matchHarness";
import { createEvaluationPolicy } from "#api/bot/policy";
import { trainingObservation } from "#api/bot/training/observation";
import { mainActionReady } from "#api/bot/training/actions";
import digilabDecks from "#api/bot/evolution/digilab-decks.json" with { type: "json" };
import { evolutionDeck } from "#api/bot/evolution/decks";
import { positionFeatures } from "./features.js";
import { evaluateSearchPosition } from "#api/bot/evolution/evaluateSearchPosition";

const GAMES = Number(process.env.OURAI_GAMES ?? 20);
const SEED = Number(process.env.OURAI_SEED ?? 1000);
const OUT = process.env.OURAI_OUT ?? "ourai_positions.jsonl";

it("collect self-play positions", async () => {
  const decks = digilabDecks.decks.flatMap((d) => { try { return [evolutionDeck(d.deckVersion)]; } catch { return []; } });
  console.log("DECKS", decks.map((d) => d.name).join(","));
  let done = 0;
  for (let g = 0; g < GAMES; g++) {
    const seed = SEED + g;
    const pick = [decks[(seed * 7) % decks.length]!, decks[(seed * 13 + 5) % decks.length]!];
    const rows: { seat: Seat; turn: number; x: number[]; b: number }[] = [];
    const seen = new Set<string>();
    const result = await runBotMatch({
      seed,
      firstSeat: (g % 2) as Seat,
      seats: [0, 1].map((s) => ({
        deck: pick[s]!.deck,
        label: pick[s]!.name,
        canChooseMainAction: (engine) => mainActionReady(engine),
        policyFactory: (engine) => {
          const base = createEvaluationPolicy({ seed: seed * 2 + s, temperature: g % 3 === 0 ? 0.6 : undefined });
          return {
            ...base,
            name: "collector",
            onTurnStart: () => base.onTurnStart(),
            chooseMainAction: (view, signal) => {
              const key = `${engine.state.turnCount}`;
              if (!seen.has(key)) {
                seen.add(key);
                for (const seat of [0, 1] as Seat[])
                  { const o = trainingObservation(engine.state, seat); rows.push({ seat, turn: engine.state.turnCount, x: positionFeatures(o), b: evaluateSearchPosition(o) }); }
              }
              return base.chooseMainAction(view, signal);
            },
          };
        },
      })) as never,
    });
    if (result.winnerSeat === undefined || result.errors.length > 0) continue;
    const lines = rows.map((r) =>
      JSON.stringify({ g: seed, d: [pick[r.seat]!.name, pick[1 - r.seat]!.name], t: r.turn, y: r.seat === result.winnerSeat ? 1 : 0, b: r.b, x: r.x }),
    );
    appendFileSync(OUT, lines.join("\n") + "\n");
    done++;
  }
  console.log("COLLECTED", done, "of", GAMES);
}, 3_600_000);
