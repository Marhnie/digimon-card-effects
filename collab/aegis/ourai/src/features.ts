import type { TrainingObservation } from "#api/bot/training/observation";

type Player = TrainingObservation["players"][number];

function side(p: Player): number[] {
  const board = p.board;
  const digimon = board.filter((x) => (x.top.level ?? 0) > 0);
  const levels = digimon.map((x) => x.top.level ?? 0);
  const dps = digimon.map((x) => Math.max(0, x.dp));
  return [
    p.securityCount,
    p.handCount,
    p.deckCount / 10,
    p.trash.length / 10,
    digimon.length,
    board.length - digimon.length,
    levels.reduce((a, b) => a + b, 0) / 5,
    Math.max(0, ...levels),
    dps.reduce((a, b) => a + b, 0) / 10000,
    Math.max(0, ...dps) / 10000,
    digimon.filter((x) => !x.suspended).length,
    digimon.reduce((a, x) => a + x.stack.length, 0) / 5,
    p.breeding === undefined ? 0 : 1 + (p.breeding.top.level ?? 0) / 2,
    p.faceUpSecurity.length,
    p.securityCount === 0 ? 1 : 0,
  ];
}

export const FEATURE_NAMES = [
  ...["sec", "hand", "deck", "trash", "dig", "other", "lvsum", "lvmax", "dpsum", "dpmax", "ready", "srcs", "breed", "secup", "sec0"].flatMap((n) => [`me_${n}`, `op_${n}`]),
  "my_turn",
  "memory_signed",
  "turn",
];

export function positionFeatures(o: TrainingObservation): number[] {
  const me = o.players.find((p) => p.seat === o.seat)!;
  const op = o.players.find((p) => p.seat !== o.seat)!;
  const a = side(me);
  const b = side(op);
  const mine = o.turnSeat === o.seat;

  return [...a.flatMap((x, i) => [x, b[i]!]), mine ? 1 : 0, mine ? o.memory / 5 : -o.memory / 5, Math.min(o.turn, 30) / 10];
}
