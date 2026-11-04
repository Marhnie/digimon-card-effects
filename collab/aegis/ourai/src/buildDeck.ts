import { CardKind, type CardDefinition } from "@aegis/shared";
import { allCards, getCardDefinition } from "@aegis/shared/cards/registry";
import { deckLegal, isPlayable, type Deck } from "#api/ourai/deckTools";

const RARITY: Record<string, number> = { C: 0, U: 0.3, R: 0.7, SR: 1.2, SEC: 1.4, P: 0.6 };
const SLOTS: [string, number][] = [
  ["lv3", 13],
  ["lv4", 9],
  ["lv5", 9],
  ["lv6", 5],
  ["tamer", 6],
  ["option", 8],
];

function slotOf(c: CardDefinition): string | undefined {
  if (c.kinds.includes(CardKind.Tamer)) return "tamer";
  if (c.kinds.includes(CardKind.Option)) return "option";
  if (c.kinds.includes(CardKind.Digimon)) return c.level === undefined ? undefined : c.level <= 3 ? "lv3" : c.level >= 6 ? "lv6" : `lv${c.level}`;
  return undefined;
}

function words(c: CardDefinition): Set<string> {
  return new Set([...(c.types ?? []), c.nameEn].map((x) => x.toLowerCase()));
}

function synergy(c: CardDefinition, boss: CardDefinition): number {
  const bw = words(boss);
  const cw = words(c);
  const btext = `${boss.effectText ?? ""} ${boss.inheritedEffectText ?? ""}`.toLowerCase();
  const ctext = `${c.effectText ?? ""} ${c.inheritedEffectText ?? ""}`.toLowerCase();
  let s = 0;
  for (const w of cw) if (bw.has(w)) s += 1;
  for (const t of boss.types ?? []) if (ctext.includes(t.toLowerCase())) s += 1.5;
  for (const t of c.types ?? []) if (btext.includes(t.toLowerCase())) s += 1;
  if (btext.includes(c.nameEn.toLowerCase())) s += 3;
  if (ctext.includes(boss.nameEn.toLowerCase())) s += 3;
  return s;
}

function power(c: CardDefinition): number {
  const text = (c.effectText ?? "").length + (c.inheritedEffectText ?? "").length;
  const body = c.kinds.includes(CardKind.Digimon) && c.level !== undefined ? c.dp / 1000 - c.level * 1.6 : 0;
  return (RARITY[c.rarity ?? "C"] ?? 0) + Math.min(1, text / 200) + body * 0.15 - Math.max(0, c.playCost - 7) * 0.1;
}

export function bossCandidates(): CardDefinition[] {
  return allCards().filter(
    (c) =>
      c.kinds.includes(CardKind.Digimon) &&
      (c.level ?? 0) >= 6 &&
      (c.rarity === "SR" || c.rarity === "SEC") &&
      c.colors.length >= 1 &&
      isPlayable(c.cardId),
  );
}

export function buildDeck(bossId: string, rnd: () => number): Deck | undefined {
  const boss = getCardDefinition(bossId)!;
  const colors = new Set(boss.colors);
  const pool = allCards().filter((c) => c.colors.some((x) => colors.has(x)) && isPlayable(c.cardId) && !c.isToken);
  const main: string[] = [bossId, bossId, bossId, bossId];
  const used = new Map<string, number>([[bossId, 4]]);
  for (const [slot, n] of SLOTS) {
    let need = slot === "lv6" ? n - 4 : n;
    const ranked = pool
      .filter((c) => slotOf(c) === slot && !used.has(c.cardId))
      .map((c) => ({ c, v: synergy(c, boss) * 1.0 + power(c) + rnd() * 0.6 }))
      .sort((a, b) => b.v - a.v);
    for (const { c } of ranked) {
      if (need <= 0) break;
      const k = Math.min(need, slot === "option" || slot === "tamer" ? 3 : 4);
      for (let i = 0; i < k; i++) main.push(c.cardId);
      used.set(c.cardId, k);
      need -= k;
    }
  }
  while (main.length > 50) main.pop();
  const eggs = pool
    .filter((c) => c.kinds.includes(CardKind.DigiEgg))
    .map((c) => ({ c, v: synergy(c, boss) + power(c) + rnd() * 0.3 }))
    .sort((a, b) => b.v - a.v);
  if (main.length < 50 || eggs.length === 0) return undefined;
  const egg = eggs[0]!.c.cardId;
  const egg2 = eggs[1]?.c.cardId ?? egg;
  const deck = { mainDeck: main.sort(), eggDeck: egg2 === egg ? [egg, egg, egg, egg] : [egg, egg, egg, egg, egg2] };
  return deckLegal(deck) ? deck : undefined;
}
