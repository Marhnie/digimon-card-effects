import { appendFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { it } from "vitest";
import { BOT_PROFILES } from "#api/bot/profiles";
import { currentGauntlet, makeRandom, playSeries, type Named } from "#api/ourai/deckTools";

type W = Record<string, number>;
const DECK = process.env.OURAI_DECK ?? "Jupitermon";
const OUT = process.env.OURAI_OUT ?? "pilot.jsonl";
const CHAMP_OUT = process.env.OURAI_CHAMP_OUT ?? "pilot.json";
const SEED = Number(process.env.OURAI_SEED ?? 1);
const SCREEN = Number(process.env.OURAI_SCREEN ?? 8);
const CONFIRM = Number(process.env.OURAI_CONFIRM ?? 16);
const SCREEN_GAP = Number(process.env.OURAI_SCREEN_GAP ?? 0.06);
const CONFIRM_GAP = Number(process.env.OURAI_CONFIRM_GAP ?? 0.03);
const FIXED = new Set(["lethal"]);
const ADDITIVE = new Set(["blockThreshold", "barrierThreshold", "actionThreshold", "deployLevel"]);

async function rate(me: Named, field: Named[], w: W, gamesEach: number, seed: number): Promise<number> {
  let wins = 0;
  for (const [i, o] of field.entries()) wins += await playSeries(me.deck, o.deck, gamesEach, seed + i * 1000, w, undefined);
  return wins / (field.length * gamesEach);
}

it("tune a deck-specific pilot against the current meta field", async () => {
  const field = currentGauntlet().map((n) => ({ name: n.name, deck: n.deck }));
  const me = field.find((n) => n.name === DECK);
  if (!me) throw new Error(`unknown deck ${DECK}`);
  const deadline = Number(process.env.OURAI_DEADLINE_MS ?? Date.now() + 86_400_000);
  const rnd = makeRandom(SEED * 7919 + 13);
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());
  const prior = existsSync(OUT) ? readFileSync(OUT, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l)) : [];
  const lastChamp = [...prior].reverse().find((r) => r.champ)?.champ as W | undefined;
  let champ: W = lastChamp ?? { ...(BOT_PROFILES.balanced.weights as unknown as W) };
  const keys = Object.keys(champ).filter((k) => !FIXED.has(k));
  let seed = 900_000_000 + SEED * 10_000_000 + prior.length * 4000;
  let it0 = prior.length;
  if (!lastChamp) appendFileSync(OUT, JSON.stringify({ it: 0, deck: DECK, champ }) + "\n");
  while (Date.now() < deadline) {
    it0 += 1;
    const cand = { ...champ };
    const changed: string[] = [];
    for (let m = 0; m < 3; m++) {
      const k = keys[Math.floor(rnd() * keys.length)]!;
      changed.push(k);
      cand[k] = ADDITIVE.has(k) ? (k === "deployLevel" ? Math.min(6, Math.max(3, Math.round(cand[k]! + (rnd() < 0.5 ? -1 : 1)))) : cand[k]! + gauss()) : cand[k]! * Math.exp(0.35 * gauss());
    }
    const t0 = Date.now();
    seed += 2000;
    const sc = await rate(me, field, cand, SCREEN, seed);
    const sb = await rate(me, field, champ, SCREEN, seed);
    let cc: number | undefined;
    let cb: number | undefined;
    let accepted = false;
    if (sc - sb >= SCREEN_GAP) {
      seed += 2000;
      cc = await rate(me, field, cand, CONFIRM, seed);
      cb = await rate(me, field, champ, CONFIRM, seed);
      if (cc - cb >= CONFIRM_GAP) {
        champ = cand;
        accepted = true;
        writeFileSync(CHAMP_OUT, JSON.stringify(champ));
      }
    }
    appendFileSync(OUT, JSON.stringify({ it: it0, deck: DECK, changed, screen: [sc, sb], confirm: cc === undefined ? undefined : [cc, cb], accepted, champ: accepted ? champ : undefined, ms: Date.now() - t0 }) + "\n");
  }
}, 86_400_000 * 4);
