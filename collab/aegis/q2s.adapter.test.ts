// Runs the DCGO q2s jobs (card_effects/collab/q2s/merged.json) on the Aegis engine and writes
// DCGO-shaped results so q2s_eval's verdict DSL applies unchanged. Local experiment only.
import { readFileSync, writeFileSync } from "node:fs";
import { it } from "vitest";
import { setupEngine, drainMicrotasks } from "../engine/testkit/harness.js";
import { advance } from "../engine/testkit/advance.js";
import { observe } from "../engine/testkit/observe.js";
import "./index.js";

const SRC = process.env.Q2S_JOBS as string;
const OUT = process.env.Q2S_OUT as string;
const FILL = "BT1-009";
const deck = () => Array.from({ length: 12 }, () => FILL);
const stack = (f: any) => ({ card: f.cards[0], under: f.cards.slice(1).reverse(), suspended: !!f.suspended });
const seat = (x: any = {}) => ({
  battleArea: (x.field ?? []).map(stack), hand: x.hand ?? [], trash: x.trash ?? [],
  security: x.security ?? [], deck: deck(),
});

function logOf(events: any[]): string[] {
  const out: string[] = [];
  for (const e of events) {
    if (e.kind === "effectTriggered" || e.kind === "effectActivated") out.push(`Effect: ${e.sourceCardId} ${e.description ?? ""}`);
    else if (e.kind === "cardPlayed") out.push(`Play on field: ${e.cardId}`);
    else if (e.kind === "digivolved") out.push(`Evolution: ${e.cardId ?? ""} ${JSON.stringify(e)}`);
    else if (e.kind === "attackDeclared") out.push("Attack");
    else if (e.kind === "cardsMoved") {
      const j = JSON.stringify(e);
      if (/"to(Zone)?":"trash"/i.test(j)) out.push(`Delete: ${(e.deletedPermanents ?? []).map((d: any) => d.cardId).join(",")} ${j}`);
      if (/"to(Zone)?":"hand"/i.test(j) && /deck/i.test(j)) out.push(`Draw 1 card ${j}`);
      out.push(`Moved: ${j}`);
    } else if (e.kind === "actionRejected") out.push(`step error ${JSON.stringify(e)}`);
    else if (e.kind === "gameOver") out.push("GameOver");
  }
  return out;
}

const side = (p: any) => ({
  field: p.battleArea.map((b: any) => ({ cards: [b.topCard?.cardId, ...[...b.stack].reverse().map((c: any) => c.cardId)], dp: b.dp })),
  hand: p.hand.map((c: any) => c.cardId), trash: p.trash.map((c: any) => c.cardId), security: p.security.length,
});

it("q2s", async () => {
  const items = JSON.parse(readFileSync(SRC, "utf8")).filter((i: any) => i.job);
  const results: any = {};
  for (const it_ of items) {
    const j = it_.job; const steps: string[] = [];
    try {
      const s = setupEngine({ 0: seat(j.you), 1: seat(j.opp) } as any, { autoAcceptOptional: true, autoSelectCards: true, autoChooseOption: true } as any);
      s.state.memory = j.you.memory ?? 10;
      void s.engine.runOneTurn();
      await advance(s.engine).waitForMainPhase(0);
      const me = () => s.state.players[0] as any; const opp = () => s.state.players[1] as any;
      for (const st of j.steps) {
        let r: any = { ok: true };
        const inHand = () => me().hand.find((c: any) => c.cardId === st.card);
        if (st.do === "play") r = s.engine.applyIntent(0, { type: "playCard", instanceId: inHand().instanceId });
        else if (st.do === "digivolve") r = s.engine.applyIntent(0, { type: "digivolve", permanentId: me().battleArea[st.frame].permanentId, instanceId: inHand().instanceId });
        else if (st.do === "attack") r = s.engine.applyIntent(0, { type: "attack", attackerPermanentId: me().battleArea[st.frame].permanentId, target: (st.target ?? -1) < 0 ? { kind: "player" } : { kind: "digimon", permanentId: opp().battleArea[st.target].permanentId } } as any);
        else if (st.do === "activate") {
          const p = me().battleArea[st.frame]; const ef = observe(s.engine).activatableEffects(p)[st.skill ?? 0];
          r = ef ? s.engine.applyIntent(0, { type: "activateEffect", sourceInstanceId: ef.instanceId ?? p.topCard.instanceId, effectKey: ef.effectKey }) : { ok: false, reason: "no activatable" };
        }
        steps.push(`${st.do}:${JSON.stringify(r)}`);
        await drainMicrotasks(800);
        for (let k = 0; k < 6; k++) { await new Promise<void>((d) => setImmediate(d)); await drainMicrotasks(200); }
      }
      results[it_.id] = { log: logOf(s.events), you: side(me()), opp: side(opp()), steps };
    } catch (e: any) { results[it_.id] = { error: String(e?.message ?? e).slice(0, 300), steps, log: [], you: {}, opp: {} }; }
  }
  writeFileSync(OUT, JSON.stringify(results));
}, 600000);
