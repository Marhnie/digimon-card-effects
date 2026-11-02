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
const settleAll = async () => { await drainMicrotasks(800); for (let k = 0; k < 8; k++) { await new Promise<void>((d) => setImmediate(d)); await drainMicrotasks(200); } };
const seat = (x: any = {}) => ({
  battleArea: (x.field ?? []).map(stack), hand: x.hand ?? [], trash: x.trash ?? [],
  security: x.security ?? [], deck: [...(x.deck ?? []), ...deck()],
});

function logOf(events: any[]): string[] {
  const out: string[] = [];
  for (const e of events) {
    if (e.kind === "effectTriggered" || e.kind === "effectActivated") out.push(`Effect: ${e.sourceCardId} seat${e.seat} ${e.description ?? ""}`);
    else if (e.kind === "effectHadNoEffect" || e.kind === "securityChecked" || e.kind === "battleCompared" || e.kind === "deletionPrevented") out.push(`${e.kind}: ${JSON.stringify(e).slice(0, 300)}`);
    else if (e.kind === "cardPlayed") out.push(`Play on field: ${e.cardId} seat${e.seat}`);
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
  field: p.battleArea.map((b: any) => ({ cards: [b.topCard?.cardId, ...[...b.stack].reverse().map((c: any) => c.cardId)], dp: b.dp, suspended: b.isSuspended })),
  hand: p.hand.map((c: any) => c.cardId), trash: p.trash.map((c: any) => c.cardId), security: p.security.length,
});

it("q2s", async () => {
  const items = JSON.parse(readFileSync(SRC, "utf8")).filter((i: any) => i.job);
  const results: any = {};
  for (const it_ of items) {
    const j = it_.job; const steps: any[] = [];
    try {
      const preferred: string[] = [];
      const opts: any = j.decline
        ? { autoDeclineOptional: true, declinePrompts: [""], autoSelectCards: true, autoChooseOption: true, preferInstanceIds: preferred }
        : { autoAcceptOptional: true, autoSelectCards: true, autoChooseOption: true, preferInstanceIds: preferred };
      const s = setupEngine({ 0: seat(j.you), 1: seat(j.opp) } as any, opts);
      s.state.memory = j.you.memory ?? 10;
      for (const id of j.prefer ?? []) for (const p of [s.state.players[0], s.state.players[1]] as any[]) {
        for (const z of ["hand", "trash", "security"]) for (const c of p[z]) if (c.cardId === id) preferred.push(c.instanceId);
        for (const b of p.battleArea) if (b.topCard?.cardId === id) preferred.push(b.topCard.instanceId);
      }
      void s.engine.startTurnLoop();
      await advance(s.engine).waitForMainPhase(0);
      (j.you.field ?? []).forEach((f: any, n: number) => { if (f.suspended) (s.state.players[0] as any).battleArea[n].isSuspended = true; });
      let cur = 0;
      for (const st of j.steps) {
        const me = () => s.state.players[cur] as any; const foe = () => s.state.players[1 - cur] as any;
        const inHand = () => me().hand.find((c: any) => c.cardId === st.card);
        const a = (i: any) => s.engine.applyIntent(cur as any, i);
        let r: any = { ok: true };
        if (st.do === "end_turn") { r = a({ type: "endPhase" }); await settleAll(); cur = 1 - cur; await advance(s.engine).waitForMainPhase(cur as any); }
        else if (st.do === "play") r = inHand() ? a({ type: "playCard", instanceId: inHand().instanceId }) : { ok: false, reason: "not in hand" };
        else if (st.do === "digivolve") r = inHand() ? a({ type: "digivolve", permanentId: me().battleArea[st.frame].permanentId, instanceId: inHand().instanceId }) : { ok: false, reason: "not in hand" };
        else if (st.do === "attack") r = a({ type: "attack", attackerPermanentId: me().battleArea[st.frame].permanentId, target: (st.target ?? -1) < 0 ? { kind: "player" } : { kind: "digimon", permanentId: foe().battleArea[st.target].permanentId } });
        else if (st.do === "activate") { const p = me().battleArea[st.frame]; const ef = observe(s.engine).activatableEffects(p)[st.skill ?? 0]; r = ef ? a({ type: "activateEffect", sourceInstanceId: ef.instanceId ?? p.topCard.instanceId, effectKey: ef.effectKey }) : { ok: false, reason: "no activatable" }; }
        else r = { ok: false, reason: "unknown step" };
        steps.push({ do: st.do, ok: !!r.ok, reason: r.reason });
        await settleAll();
      }
      results[it_.id] = { log: logOf(s.events), you: side(s.state.players[0]), opp: side(s.state.players[1]), steps, memory: s.state.memory, turnSeat: s.state.turnSeat, gameOver: !!s.state.gameOver };
    } catch (e: any) { results[it_.id] = { error: String(e?.message ?? e).slice(0, 300), steps, log: [], you: {}, opp: {} }; }
  }
  writeFileSync(OUT, JSON.stringify(results));
}, 1200000);
