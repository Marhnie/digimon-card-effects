import { readFileSync, writeFileSync } from "node:fs";
import { test } from "vitest";
import { scoreParts, type Model } from "#api/ourai/ourValue";

test("ourai value parity", () => {
  const m = JSON.parse(readFileSync(process.env.OURAI_VALUE!, "utf8")) as Model;
  const rows = readFileSync(process.env.OURAI_ROWS!, "utf8").split("\n").filter(Boolean).slice(0, 200).map((l) => JSON.parse(l) as { x: number[]; c: Record<string, string[]> });
  writeFileSync(process.env.OURAI_OUT!, JSON.stringify(rows.map((r) => scoreParts(m, r.x, r.c))));
});
