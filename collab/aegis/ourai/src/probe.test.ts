import { it } from "vitest";
import { createBaselinePolicy } from "#api/bot/baselinePolicy";
import { runBotSeries } from "#api/bot/matchHarness";
it("probe", async () => {
  const t = Date.now();
  const r = await runBotSeries({ games: 4, baseSeed: 11, seats: [{ profile: "balanced", label: "balanced" }, { policy: createBaselinePolicy(), label: "baseline" }] });
  console.log("PROBE", JSON.stringify({ ms: Date.now() - t, winsA: r.winsA, winsB: r.winsB, draws: r.draws, turns: r.averageTurns, rej: r.totalRejections, errors: r.errors.slice(0, 3) }));
}, 600_000);
