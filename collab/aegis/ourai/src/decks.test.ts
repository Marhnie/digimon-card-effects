import { it } from "vitest";
import { ALL_META_DECKS, COVERED_BLOCKS, metaDecksForBlock } from "#api/bot/metaDecks/index";
it("decks", () => {
  console.log("DECKS", ALL_META_DECKS.length, JSON.stringify(COVERED_BLOCKS.slice(-6).map((b) => [b, metaDecksForBlock(b).length, metaDecksForBlock(b).map((d: any) => d.name ?? d.archetype ?? d.deckVersion).slice(0, 12)])));
  console.log("KEYS", Object.keys(ALL_META_DECKS[0] as object));
});
