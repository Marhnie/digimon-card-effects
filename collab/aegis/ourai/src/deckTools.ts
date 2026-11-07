import { existsSync, readFileSync } from "node:fs";
import type { Seat } from "@aegis/shared";
import { BOT_PROFILES, type BotProfile } from "#api/bot/profiles";
import { allCards, getCardDefinition } from "@aegis/shared/cards/registry";
import { CardKind } from "@aegis/shared";
import { runBotMatch } from "#api/bot/matchHarness";
import { createEvaluationPolicy } from "#api/bot/policy";
import { mainActionReady } from "#api/bot/training/actions";
import digilabDecks from "#api/bot/evolution/digilab-decks.json" with { type: "json" };
import { evolutionDeck } from "#api/bot/evolution/decks";
import { validateDecklist } from "#api/engine/deckValidation";
import { getEffectModule } from "#api/engine/effects/registry";

export type Deck = { mainDeck: string[]; eggDeck: string[] };
export type Named = { name: string; deck: Deck; weights?: Record<string, number> };

export function legalMetaDecks(): Named[] {
  return digilabDecks.decks.flatMap((d) => {
    try {
      const e = evolutionDeck(d.deckVersion);
      return [{ name: e.name, deck: e.deck }];
    } catch {
      return [];
    }
  });
}

export function gauntlet(): Named[] {
  const seen = new Set<string>();
  return legalMetaDecks().filter((d) => (seen.has(d.name) ? false : (seen.add(d.name), true)));
}

export function currentGauntlet(): Named[] {
  const meta = digilabDecks.meta as { format: string; archetypes: { archetype_name: string; meta_pct: number }[] }[];
  const share = new Map<string, number>();
  for (const f of [...meta].sort((a, b) => (a.format === "EX13" ? 1 : 0) - (b.format === "EX13" ? 1 : 0))) for (const a of f.archetypes) share.set(a.archetype_name, a.meta_pct);
  const latest = new Map<string, { date: string; named: Named }>();
  for (const d of digilabDecks.decks) {
    try {
      const e = evolutionDeck(d.deckVersion);
      const prev = latest.get(e.name);
      if (!prev || d.eventDate > prev.date) latest.set(e.name, { date: d.eventDate, named: { name: e.name, deck: e.deck } });
    } catch {
      continue;
    }
  }
  const dir = process.env.OURAI_PILOT_DIR;
  return [...latest.values()]
    .map((x) => x.named)
    .sort((a, b) => (share.get(b.name) ?? 0) - (share.get(a.name) ?? 0))
    .map((n) => {
      const f = dir ? `${dir}/pilot_${n.name.replace(/[^A-Za-z0-9]+/g, "_")}.json` : "";
      return f && existsSync(f) ? { ...n, weights: JSON.parse(readFileSync(f, "utf8")) as Record<string, number> } : n;
    });
}

export function isPlayable(id: string): boolean {
  const c = getCardDefinition(id);
  if (c === undefined || c.isToken) return false;
  const text = (c.effectText ?? "").trim() || (c.inheritedEffectText ?? "").trim() || (c.securityEffectText ?? "").trim();
  return !text || getEffectModule(id) !== undefined;
}

export function deckLegal(deck: Deck): boolean {
  return validateDecklist(deck).ok && [...deck.mainDeck, ...deck.eggDeck].every(isPlayable);
}

const withWeights = (w: Record<string, number> | undefined): BotProfile | undefined => (w ? { ...BOT_PROFILES.balanced, weights: w as never } : undefined);

export async function playSeries(a: Deck, b: Deck, games: number, seed: number, aW?: Record<string, number>, bW?: Record<string, number>): Promise<number> {
  let wins = 0;
  for (let g = 0; g < games; g++) {
    const s = seed + Math.floor(g / 2);
    const aSeat = (g % 2) as Seat;
    const decks = aSeat === 0 ? [a, b] : [b, a];
    const result = await runBotMatch({
      seed: s,
      firstSeat: 0,
      seats: [0, 1].map((k) => ({
        deck: decks[k]!,
        label: k === aSeat ? "a" : "b",
        canChooseMainAction: (engine) => mainActionReady(engine),
        policyFactory: () => {
          const profile = withWeights(k === aSeat ? aW : bW);
          return createEvaluationPolicy(profile ? { profile, seed: s * 2 + k } : { seed: s * 2 + k });
        },
      })) as never,
    });
    if (result.winnerSeat === aSeat) wins += 1;
    else if (result.winnerSeat === undefined) wins += 0.5;
  }
  return wins;
}

export async function gauntletScore(deck: Deck, opponents: Named[], gamesEach: number, seed: number): Promise<number> {
  let w = 0;
  for (const [i, o] of opponents.entries()) w += await playSeries(deck, o.deck, gamesEach, seed + i * 1000, undefined, o.weights);
  return w / (opponents.length * gamesEach);
}

export function colorPool(deck: Deck): string[] {
  const colors = new Set(deck.mainDeck.flatMap((id) => getCardDefinition(id)?.colors ?? []));
  return allCards()
    .filter((c) => !c.kinds.includes(CardKind.DigiEgg) && c.colors.some((x) => colors.has(x)) && isPlayable(c.cardId))
    .map((c) => c.cardId);
}

export function mutate(deck: Deck, pool: string[], rnd: () => number): Deck {
  const main = [...deck.mainDeck];
  const counts = new Map<string, number>();
  for (const id of main) counts.set(id, (counts.get(id) ?? 0) + 1);
  const k = rnd() < 0.6 ? 1 : 2;
  const distinct = [...counts.keys()];
  const out = distinct[Math.floor(rnd() * distinct.length)]!;
  const take = Math.min(k, counts.get(out)!);
  let add: string;
  for (let tries = 0; ; tries++) {
    add = rnd() < 0.55 ? distinct[Math.floor(rnd() * distinct.length)]! : pool[Math.floor(rnd() * pool.length)]!;
    if (add !== out && (counts.get(add) ?? 0) + take <= 4) break;
    if (tries > 50) return deck;
  }
  for (let i = 0; i < take; i++) main.splice(main.indexOf(out), 1);
  for (let i = 0; i < take; i++) main.push(add);
  return { mainDeck: main.sort(), eggDeck: [...deck.eggDeck] };
}

export function makeRandom(seed: number): () => number {
  let x = seed >>> 0 || 1;
  return () => {
    x ^= x << 13;
    x ^= x >>> 17;
    x ^= x << 5;
    return ((x >>> 0) % 1_000_000) / 1_000_000;
  };
}
