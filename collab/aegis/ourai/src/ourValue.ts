import { appendFileSync, readFileSync } from "node:fs";
import type { TrainingObservation } from "#api/bot/training/observation";
import { positionFeatures, positionFeatures2 } from "#api/ourai/features";

type Model = { key?: string; features_mean: number[]; features_std: number[]; layers: { W: number[][]; b: number[] }[] };
let model: Model | undefined;

export function ourValue(observation: TrainingObservation): number {
  if (process.env.OURAI_TRACE) appendFileSync(process.env.OURAI_TRACE, "1");
  model ??= JSON.parse(readFileSync(process.env.OURAI_VALUE!, "utf8")) as Model;
  let h = (model.key === "x2" ? positionFeatures2(observation) : positionFeatures(observation)).map((x, i) => (x - model!.features_mean[i]!) / model!.features_std[i]!);
  model.layers.forEach((layer, k) => {
    h = layer.W.map((row, j) => row.reduce((s, w, i) => s + w * h[i]!, layer.b[j]!));
    if (k < model!.layers.length - 1) h = h.map((v) => Math.max(0, v));
  });
  return 1 / (1 + Math.exp(-Math.max(-12, Math.min(12, h[0]!))));
}
