import { appendFileSync, readFileSync } from "node:fs";
import type { TrainingObservation } from "#api/bot/training/observation";
import { positionCards, positionFeatures, positionFeatures2 } from "#api/ourai/features";

export type Model = { key?: string; prior?: Model; scale?: number; bias?: number; card_w?: number[]; groups?: string[]; vocab?: string[]; features_mean: number[]; features_std: number[]; layers: { W: number[][]; b: number[] }[] };
let model: Model | undefined;
const indexes = new WeakMap<Model, Map<string, number>>();

export function ourValue(observation: TrainingObservation): number {
  if (process.env.OURAI_TRACE) appendFileSync(process.env.OURAI_TRACE, "1");
  model ??= JSON.parse(readFileSync(process.env.OURAI_VALUE!, "utf8")) as Model;
  const base = model.key === "x2" || model.prior?.key === "x2" ? positionFeatures2(observation) : positionFeatures(observation);
  return scoreParts(model, base, model.vocab ? positionCards(observation) : {});
}

/** Same math for engine use and parity tests: x = summary features (key x or x2), cards = positionCards groups. */
export function scoreParts(m: Model, x: number[], cards: Record<string, string[]>): number {
  const z = m.key === "xr" ? cardTerm(m, cards, m.card_w!) + logit(m.prior!, x, cards) * m.scale! + m.bias! : logit(m, x, cards);
  return 1 / (1 + Math.exp(-Math.max(-12, Math.min(12, z))));
}

function vocabIndex(m: Model): Map<string, number> {
  let ix = indexes.get(m);
  if (!ix) indexes.set(m, (ix = new Map(m.vocab!.map((c, i) => [c, i]))));
  return ix;
}

function cardTerm(m: Model, cards: Record<string, string[]>, w: number[]): number {
  const ix = vocabIndex(m), v = m.vocab!.length;
  let z = 0;
  m.groups!.forEach((g, k) => {
    for (const c of cards[g] ?? []) {
      const i = ix.get(c);
      if (i !== undefined) z += w[k * v + i]!;
    }
  });
  return z;
}

function logit(m: Model, x: number[], cards: Record<string, string[]>): number {
  let h = x.map((xi, i) => (xi - m.features_mean[i]!) / m.features_std[i]!);
  if (m.key === "xc") {
    const ix = vocabIndex(m), v = m.vocab!.length;
    const bag = new Array<number>(m.groups!.length * v).fill(0);
    m.groups!.forEach((g, k) => {
      for (const c of cards[g] ?? []) {
        const i = ix.get(c);
        if (i !== undefined) bag[k * v + i]! += 1;
      }
    });
    h = [...h, ...bag];
  }
  m.layers.forEach((layer, k) => {
    h = layer.W.map((row, j) => row.reduce((s, w, i) => s + w * h[i]!, layer.b[j]!));
    if (k < m.layers.length - 1) h = h.map((v) => Math.max(0, v));
  });
  return h[0]!;
}
