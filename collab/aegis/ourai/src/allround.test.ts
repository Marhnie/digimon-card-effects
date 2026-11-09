import { appendFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { it } from "vitest";
import { BOT_PROFILES } from "#api/bot/profiles";
import { currentGauntlet, deckLegal, makeRandom, playSeries, type Deck, type Named } from "#api/ourai/deckTools";

type W = Record<string, number>;
const OUT = process.env.OURAI_OUT ?? "allround.jsonl";
const CHAMP_OUT = process.env.OURAI_CHAMP_OUT ?? "allround.json";
const SEED = Number(process.env.OURAI_SEED ?? 1);
const SCREEN = Number(process.env.OURAI_SCREEN ?? 2);
const CONFIRM = Number(process.env.OURAI_CONFIRM ?? 4);
const SCREEN_GAP = Number(process.env.OURAI_SCREEN_GAP ?? 0.03);
const CONFIRM_GAP = Number(process.env.OURAI_CONFIRM_GAP ?? 0.015);
const FIXED = new Set(["lethal"]);
const ADDITIVE = new Set(["blockThreshold", "barrierThreshold", "actionThreshold", "deployLevel"]);

function pilots(): Named[] {
  const meta = currentGauntlet().map((n) => ({ name: n.name, deck: n.deck }));
  const extra: Named[] = [];
  for (const f of (process.env.OURAI_EXTRA ?? "").split(";").filter((x) => x && existsSync(x))) {
    const lines = readFileSync(f, "utf8").trim().split("\n").filter(Boolean);
    const best = lines.length ? (JSON.parse(lines.at(-1)!).best as Deck | undefined) : undefined;
    if (best && deckLegal(best)) extra.push({ name: f.split("/").pop()!, deck: best });
  }
  return [...meta, ...extra];
}

async function rate(mine: Named[], field: Named[], w: W | undefined, gamesEach: number, seed: number): Promise<number> {
  let wins = 0;
  for (const [j, me] of mine.entries()) for (const [i, o] of field.entries()) wins += await playSeries(me.deck, o.deck, gamesEach, seed + j * 100_000 + i * 1000, w, undefined);
  return wins / (mine.length * field.length * gamesEach);
}

it.skipIf(!!process.env.OURAI_CHECK)("tune one all-round policy over every deck", async () => {
  const field = currentGauntlet().map((n) => ({ name: n.name, deck: n.deck }));
  const deadline = Number(process.env.OURAI_DEADLINE_MS ?? Date.now() + 86_400_000);
  const rnd = makeRandom(SEED * 7919 + 101);
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());
  const prior = existsSync(OUT) ? readFileSync(OUT, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l)) : [];
  for (let k = 0; k < prior.length * 7; k++) rnd();
  const lastChamp = [...prior].reverse().find((r) => r.champ)?.champ as W | undefined;
  let champ: W = lastChamp ?? { ...(BOT_PROFILES.balanced.weights as unknown as W) };
  const keys = Object.keys(champ).filter((k) => !FIXED.has(k));
  let seed = 2_100_000_000 + SEED * 10_000_000 + prior.length * 4000;
  let it0 = prior.length;
  if (!lastChamp) appendFileSync(OUT, JSON.stringify({ it: 0, champ }) + "\n");
  while (Date.now() < deadline) {
    it0 += 1;
    const mine = pilots();
    const cand = { ...champ };
    const changed: string[] = [];
    for (let m = 0; m < 3; m++) {
      const k = keys[Math.floor(rnd() * keys.length)]!;
      changed.push(k);
      cand[k] = ADDITIVE.has(k) ? (k === "deployLevel" ? Math.min(6, Math.max(3, Math.round(cand[k]! + (rnd() < 0.5 ? -1 : 1)))) : cand[k]! + gauss()) : cand[k]! * Math.exp(0.35 * gauss());
    }
    const t0 = Date.now();
    seed += 2000;
    const sc = await rate(mine, field, cand, SCREEN, seed);
    const sb = await rate(mine, field, champ, SCREEN, seed);
    let cc: number | undefined;
    let cb: number | undefined;
    let accepted = false;
    if (sc - sb >= SCREEN_GAP) {
      seed += 2000;
      cc = await rate(mine, field, cand, CONFIRM, seed);
      cb = await rate(mine, field, champ, CONFIRM, seed);
      if (cc - cb >= CONFIRM_GAP) {
        champ = cand;
        accepted = true;
        writeFileSync(CHAMP_OUT, JSON.stringify(champ));
      }
    }
    appendFileSync(OUT, JSON.stringify({ it: it0, decks: mine.length, changed, screen: [sc, sb], confirm: cc === undefined ? undefined : [cc, cb], accepted, champ: accepted ? champ : undefined, ms: Date.now() - t0 }) + "\n");
  }
}, 86_400_000 * 4);

it.skipIf(!process.env.OURAI_CHECK)("check the all-round policy on reserved seeds", async () => {
  const field = currentGauntlet().map((n) => ({ name: n.name, deck: n.deck }));
  const mine = pilots();
  const read = (f: string | undefined) => (f && existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as W) : undefined);
  const cand = read(process.env.OURAI_CAND);
  const base = read(process.env.OURAI_BASE);
  const games = Number(process.env.OURAI_GAMES ?? 4);
  const seed = Number(process.env.OURAI_EVAL_SEED ?? 2_000_000_000);
  const c = await rate(mine, field, cand, games, seed);
  const b = await rate(mine, field, base, games, seed);
  appendFileSync(OUT, JSON.stringify({ check: true, t: Date.now(), decks: mine.map((m) => m.name), cand: c, base: b, games: mine.length * field.length * games, seed }) + "\n");
}, 86_400_000);
