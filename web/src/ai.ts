// In-browser ports of the six experiment players (01-game/02-players), with the
// tuned hyperparameters from 03-tuning. Faithful to the Python authority:
//   random, naive_buro, cooldown_buro, uct, uct_pb_naive, uct_pb_cooldown
// MCTS players take an optional progress callback so the UI can show a bar.

import {
  applyMove, EMPTY, flipsFor, isTerminal, legalMoves, N, NN, opponent,
  PASS, State, Variant, winner,
} from "./engine";

export type AIKind =
  | "random" | "naive_buro" | "cooldown_buro" | "uct" | "uct_pb_naive" | "uct_pb_cooldown";

export interface AIConfig {
  kind: AIKind;
  budget: number;             // MCTS simulations/move (ignored by random/buro)
  c: number;                  // UCB exploration constant
  wH: number;                 // progressive-bias weight
  wMob: number;               // mobility weight (heuristic)
  lambdaC: number;            // cooldown-term weight (heuristic)
  heuristicAware: null | boolean; // null=plain UCT, false=naive H, true=cooldown H
}

export const ORDER: AIKind[] =
  ["random", "naive_buro", "cooldown_buro", "uct", "uct_pb_naive", "uct_pb_cooldown"];
export const isMCTS = (k: AIKind) => k === "uct" || k === "uct_pb_naive" || k === "uct_pb_cooldown";

// Tuned hyperparameters (03-tuning/results). Heuristics are tuned once (on
// cooldown) and reused; MCTS players are tuned per variant. PB players use the
// DEFAULT heuristic weights (wMob=1, lambdaC=1) for their bias signal — only the
// standalone Buro players use the tuned Buro weights.
export function configFor(kind: AIKind, variant: Variant, budget: number): AIConfig {
  const base: AIConfig =
    { kind, budget, c: Math.SQRT2, wH: 0, wMob: 1, lambdaC: 1, heuristicAware: null };
  const cl = variant === "classic";
  switch (kind) {
    case "random":         return base;
    case "naive_buro":     return { ...base, wMob: 4.7536 };
    case "cooldown_buro":  return { ...base, wMob: 2.488, lambdaC: 0.519 };
    case "uct":            return { ...base, c: cl ? 2.2324 : 0.516 };
    case "uct_pb_naive":   return { ...base, heuristicAware: false,
                                    c: cl ? 0.7462 : 1.1085, wH: cl ? 2.4157 : 1.1208 };
    case "uct_pb_cooldown":return { ...base, heuristicAware: true,
                                    c: cl ? 0.7174 : 0.5412, wH: cl ? 5.0215 : 8.706 };
  }
}

// tiny deterministic PRNG (toy AI; evolves across calls for variety)
let _seed = 1234567;
function rnd(): number { _seed = (_seed * 1103515245 + 12345) & 0x7fffffff; return _seed / 0x7fffffff; }
const pick = <T>(a: T[]): T => a[Math.floor(rnd() * a.length)];

// ---------------------------------------------------------------------------
// Buro heuristic (02-players/heuristics.py)
// ---------------------------------------------------------------------------
const W6 = [
  100, -20, 10, 10, -20, 100,
  -20, -50, -2, -2, -50, -20,
  10, -2, -1, -1, -2, 10,
  10, -2, -1, -1, -2, 10,
  -20, -50, -2, -2, -50, -20,
  100, -20, 10, 10, -20, 100,
];
const AXES: Array<[[number, number], [number, number]]> = [
  [[-1, 0], [1, 0]], [[0, -1], [0, 1]], [[-1, -1], [1, 1]], [[-1, 1], [1, -1]],
];
const WALL = 3;
const cellAt = (b: number[], r: number, c: number) =>
  (r >= 0 && r < N && c >= 0 && c < N) ? b[r * N + c] : WALL;

function positional(board: number[], player: number): number {
  const opp = opponent(player); let s = 0;
  for (let i = 0; i < NN; i++) { if (board[i] === player) s += W6[i]; else if (board[i] === opp) s -= W6[i]; }
  return s;
}
function placements(board: number[], cool: Set<number>, player: number): number {
  let n = 0;
  for (let p = 0; p < NN; p++) if (board[p] === EMPTY && flipsFor(board, cool, p, player).length) n++;
  return n;
}
const mobility = (board: number[], cool: Set<number>, player: number) =>
  placements(board, cool, player) - placements(board, cool, opponent(player));

function cooldownTerm(s: State, move: number): number {
  const player = s.toMove, opp = opponent(player);
  const flips = flipsFor(s.board, s.cool, move, player);
  if (!flips.length) return 0;
  const cb = s.board.slice(); cb[move] = player; for (const i of flips) cb[i] = player;
  let bonus = 0, penalty = 0;
  for (const f of flips) {
    const r = Math.floor(f / N), c = f % N;
    let prot = false, vuln = false;
    for (const [d1, d2] of AXES) {
      const n1 = cellAt(cb, r + d1[0], c + d1[1]);
      const n2 = cellAt(cb, r + d2[0], c + d2[1]);
      if (n1 === player && n2 === player) prot = true;
      if ((n1 === opp && n2 === EMPTY) || (n2 === opp && n1 === EMPTY)) vuln = true;
    }
    if (vuln) penalty++; else if (prot) bonus++;
  }
  return bonus - penalty;
}

export function evaluateMove(s: State, move: number, variant: Variant, cfg: AIConfig, aware: boolean): number {
  if (move === PASS) return 0;
  const player = s.toMove;
  const child = applyMove(s, move, variant);
  let score = positional(child.board, player);
  score += cfg.wMob * mobility(child.board, child.cool, player);
  if (aware) score += cfg.lambdaC * cooldownTerm(s, move);
  return score;
}

function buroMove(s: State, variant: Variant, cfg: AIConfig, aware: boolean): number {
  const moves = legalMoves(s, variant);
  if (moves.length === 1) return moves[0];
  let best = -Infinity, top: number[] = [];
  for (const m of moves) {
    const v = evaluateMove(s, m, variant, cfg, aware);
    if (v > best + 1e-9) { best = v; top = [m]; }
    else if (v >= best - 1e-9) top.push(m);
  }
  return pick(top);
}

// ---------------------------------------------------------------------------
// UCT / progressive bias (02-players/mcts.py)
// ---------------------------------------------------------------------------
const resultFor = (s: State, player: number) => {
  const w = winner(s);
  return w === EMPTY ? 0.5 : w === player ? 1 : 0;
};
function randomPlayout(s: State, variant: Variant): State {
  let cur = s;
  while (!isTerminal(cur)) cur = applyMove(cur, pick(legalMoves(cur, variant)), variant);
  return cur;
}

interface Node {
  state: State; parent: Node | null; move: number;
  children: Node[]; untried: number[]; n: number; w: number; h: number;
}
const mkNode = (state: State, parent: Node | null, move: number, variant: Variant): Node =>
  ({ state, parent, move, children: [], untried: legalMoves(state, variant), n: 0, w: 0, h: 0 });

type Progress = (done: number, total: number) => void;

function mctsMove(s: State, variant: Variant, cfg: AIConfig, onProgress?: Progress): number {
  const moves = legalMoves(s, variant);
  if (moves.length === 1) return moves[0];
  const usePB = cfg.heuristicAware !== null && cfg.wH > 0;
  const aware = cfg.heuristicAware === true;
  const root = mkNode(s, null, -2, variant);
  const reportEvery = Math.max(1, Math.floor(cfg.budget / 40));

  for (let i = 0; i < cfg.budget; i++) {
    let node = root;
    // selection
    while (node.untried.length === 0 && node.children.length > 0 && !isTerminal(node.state)) {
      let hmin = 0, hspan = 0;
      if (usePB) {
        let mn = Infinity, mx = -Infinity;
        for (const ch of node.children) { if (ch.h < mn) mn = ch.h; if (ch.h > mx) mx = ch.h; }
        hmin = mn; hspan = mx - mn;
      }
      let best = node.children[0], bestS = -Infinity;
      for (const ch of node.children) {
        const exploit = 1 - ch.w / ch.n;
        const explore = cfg.c * Math.sqrt(Math.log(node.n) / ch.n);
        let sc = exploit + explore;
        if (usePB) sc += cfg.wH * (hspan > 0 ? (ch.h - hmin) / hspan : 0) / (ch.n + 1);
        if (sc > bestS) { bestS = sc; best = ch; }
      }
      node = best;
    }
    // expansion
    if (node.untried.length && !isTerminal(node.state)) {
      const idx = Math.floor(rnd() * node.untried.length);
      const m = node.untried.splice(idx, 1)[0];
      const child = mkNode(applyMove(node.state, m, variant), node, m, variant);
      if (usePB) child.h = evaluateMove(node.state, m, variant, cfg, aware);
      node.children.push(child); node = child;
    }
    // simulation + backprop
    const final = randomPlayout(node.state, variant);
    let cur: Node | null = node;
    while (cur) { cur.n++; cur.w += resultFor(final, cur.state.toMove); cur = cur.parent; }
    if (onProgress && i % reportEvery === 0) onProgress(i, cfg.budget);
  }
  if (onProgress) onProgress(cfg.budget, cfg.budget);
  let best = root.children[0];
  for (const ch of root.children) if (ch.n > best.n) best = ch;
  return best.move;
}

// ---------------------------------------------------------------------------
export function chooseMove(s: State, variant: Variant, cfg: AIConfig, onProgress?: Progress): number {
  if (legalMoves(s, variant)[0] === PASS) return PASS;
  switch (cfg.kind) {
    case "random":        return pick(legalMoves(s, variant));
    case "naive_buro":    return buroMove(s, variant, cfg, false);
    case "cooldown_buro": return buroMove(s, variant, cfg, true);
    default:              return mctsMove(s, variant, cfg, onProgress);
  }
}
