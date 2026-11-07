import { appendFileSync, existsSync, readFileSync } from "node:fs";
import { it } from "vitest";
import { CardKind } from "@aegis/shared";
import { allCards, getCardDefinition } from "@aegis/shared/cards/registry";
import { colorPool, deckLegal, isPlayable, gauntlet, gauntletScore, legalMetaDecks, makeRandom, mutate, type Deck } from "#api/ourai/deckTools";

const GENS = Number(process.env.OURAI_GENS ?? 40);
const SEED = Number(process.env.OURAI_SEED ?? 1);
const OUT = process.env.OURAI_OUT ?? "evo.jsonl";
const MU = Number(process.env.OURAI_MU ?? 6);
const LAMBDA = Number(process.env.OURAI_LAMBDA ?? 6);
const GAMES = Number(process.env.OURAI_GAMES ?? 4);

const BAN = new Set((process.env.OURAI_BAN ?? "").split(";").filter(Boolean));
const clean = (d: Deck): boolean => d.mainDeck.every((id) => !BAN.has(id));

type Ind = { id: string; deck: Deck; wins: number; games: number; origin: string };

function slotOf(id: string): string {
  const c = getCardDefinition(id)!;
  if (c.kinds.includes(CardKind.Tamer)) return "tamer";
  if (c.kinds.includes(CardKind.Option)) return "option";
  const lv = c.level ?? 3;
  return lv <= 3 ? "lv3" : lv >= 6 ? "lv6" : `lv${lv}`;
}

function fix(main: string[], rnd: () => number): string[] {
  const counts = new Map<string, number>();
  const out: string[] = [];
  for (const id of main) {
    const n = counts.get(id) ?? 0;
    if (n < 4) {
      counts.set(id, n + 1);
      out.push(id);
    }
  }
  while (out.length > 50) out.splice(Math.floor(rnd() * out.length), 1);
  for (let tries = 0; out.length < 50 && tries < 500; tries++) {
    const id = out[Math.floor(rnd() * out.length)]!;
    if ((counts.get(id) ?? 0) < 4) {
      counts.set(id, (counts.get(id) ?? 0) + 1);
      out.push(id);
    }
  }
  return out.sort();
}

function cross(a: Deck, b: Deck, rnd: () => number): Deck {
  const slots = ["lv3", "lv4", "lv5", "lv6", "tamer", "option"];
  const take = new Set(slots.filter(() => rnd() < 0.35));
  if (take.size === 0) take.add(slots[Math.floor(rnd() * slots.length)]!);
  const main = [...a.mainDeck.filter((id) => !take.has(slotOf(id))), ...b.mainDeck.filter((id) => take.has(slotOf(id)))];
  return { mainDeck: fix(main, rnd), eggDeck: [...(rnd() < 0.5 ? a : b).eggDeck] };
}

function mean(x: Ind): number {
  return x.games === 0 ? 0 : x.wins / x.games;
}

it("evolutionary deck search without a fixed boss", async () => {
  const opponents = gauntlet();
  const fullPool = allCards().filter((c) => !c.isToken && !c.kinds.includes(CardKind.DigiEgg) && isPlayable(c.cardId) && !BAN.has(c.cardId)).map((c) => c.cardId);
  const deadline = Number(process.env.OURAI_DEADLINE_MS ?? Date.now() + 86_400_000);
  const peers = (process.env.OURAI_PEERS ?? "").split(";").filter((f) => f && f !== OUT);
  const resume = existsSync(OUT) ? readFileSync(OUT, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l)).filter((r) => r.state) : [];
  const last = resume.at(-1);
  const rnd = makeRandom(SEED * 104729 + 7 + (last?.gen ?? 0) * 31);
  let seed: number = last?.state.seed ?? 300_000_000 + SEED * 1_000_000;
  let serial: number = last?.state.serial ?? 0;
  let pop: Ind[];
  const strip = (d: Deck): Deck | undefined => {
    if (BAN.size === 0) return d;
    for (let t = 0; t < 50; t++) {
      const x = { mainDeck: fix(d.mainDeck.filter((id) => !BAN.has(id)), rnd), eggDeck: [...d.eggDeck] };
      if (deckLegal(x)) return x;
    }
    return undefined;
  };
  const evaluate = async (x: Ind) => {
    seed += 10_000;
    x.wins += (await gauntletScore(x.deck, opponents, GAMES, seed)) * opponents.length * GAMES;
    x.games += opponents.length * GAMES;
  };
  const eggPool = allCards().filter((c) => !c.isToken && c.kinds.includes(CardKind.DigiEgg) && isPlayable(c.cardId)).map((c) => c.cardId);
  const randomDeck = (): Deck => {
    for (;;) {
      const counts = new Map<string, number>();
      const main: string[] = [];
      while (main.length < 50) {
        const id = fullPool[Math.floor(rnd() * fullPool.length)]!;
        if ((counts.get(id) ?? 0) < 4) {
          counts.set(id, (counts.get(id) ?? 0) + 1);
          main.push(id);
        }
      }
      const egg = eggPool[Math.floor(rnd() * eggPool.length)]!;
      const d = { mainDeck: main.sort(), eggDeck: [egg, egg, egg, egg] };
      if (deckLegal(d)) return d;
    }
  };
  const RANDOM_START = Number(process.env.OURAI_RANDOM_START ?? 0);
  if (last) pop = last.state.pop as Ind[];
  else if (RANDOM_START > 0) {
    pop = Array.from({ length: RANDOM_START }, (_, k) => ({ id: `r${k}`, deck: randomDeck(), wins: 0, games: 0, origin: "random" }));
    for (const x of pop) await evaluate(x);
  } else {
    const files = (process.env.OURAI_SEED_DECKS ?? "").split(";").filter((f) => f && existsSync(f));
    const seeds: { id: string; deck: Deck | undefined; origin: string }[] = [
      ...opponents.map((o) => ({ id: `meta:${o.name}`, deck: strip(o.deck), origin: "meta" })),
      ...files.map((f) => ({ id: f.split("/").pop()!.replace(".json", ""), deck: strip(JSON.parse(readFileSync(f, "utf8")) as Deck), origin: "file" })),
    ];
    pop = seeds.filter((x) => x.deck !== undefined).map((x) => ({ id: x.id, deck: x.deck!, wins: 0, games: 0, origin: x.origin }));
    for (const x of pop) await evaluate(x);
  }
  for (let g = (last?.gen ?? 0) + 1; g <= GENS && Date.now() < deadline; g++) {
    pop.sort((p, q) => mean(q) - mean(p));
    const parents = pop.slice(0, MU);
    const kids: Ind[] = [];
    if (g % 5 === 0 && peers.length > 0) {
      const f = peers[Math.floor(rnd() * peers.length)]!;
      if (existsSync(f)) {
        const lines = readFileSync(f, "utf8").trim().split("\n").filter(Boolean);
        const peer = lines.length ? JSON.parse(lines.at(-1)!) : undefined;
        if (peer?.best && deckLegal(peer.best) && clean(peer.best)) kids.push({ id: `g${g}m${serial++}`, deck: peer.best, wins: 0, games: 0, origin: `migrant(${f.split("/").pop()})` });
      }
    }
    for (let tries = 0; kids.length < LAMBDA && tries < 200; tries++) {
      const pa = parents[Math.floor(rnd() * parents.length)]!;
      let deck: Deck;
      let origin: string;
      if (rnd() < 0.5) {
        const pb = pop[Math.floor(rnd() * pop.length)]!;
        if (pb === pa) continue;
        deck = cross(pa.deck, pb.deck, rnd);
        origin = `cross(${pa.id},${pb.id})`;
      } else {
        deck = pa.deck;
        const steps = 1 + Math.floor(rnd() * 3);
        for (let s = 0; s < steps; s++) deck = mutate(deck, rnd() < 0.25 ? fullPool : colorPool(deck).filter((id) => !BAN.has(id)), rnd);
        origin = `mut(${pa.id})`;
      }
      if (!deckLegal(deck) || !clean(deck)) continue;
      kids.push({ id: `g${g}k${serial++}`, deck, wins: 0, games: 0, origin });
    }
    for (const x of [...parents, ...kids]) await evaluate(x);
    pop = [...parents, ...kids].sort((p, q) => mean(q) - mean(p)).slice(0, MU);
    appendFileSync(
      OUT,
      JSON.stringify({ gen: g, t: Date.now(), pop: pop.map((x) => ({ id: x.id, origin: x.origin, games: x.games, score: Number(mean(x).toFixed(4)) })), best: pop[0]!.deck, state: { seed, serial, pop } }) + "\n",
    );
  }
}, 86_400_000 * 4);
