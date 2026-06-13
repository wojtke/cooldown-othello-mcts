// Light in-browser AI for "getting a feel" — NOT the tuned research player.
// Three strengths: random, greedy (Buro positional, 1-ply), and a short-budget UCT.

import {
  applyMove, counts, EMPTY, flipsFor, isTerminal, legalMoves, NN, opponent,
  PASS, State, Variant, winner,
} from "./engine";

export type AIKind = "random" | "greedy" | "mcts";

// 6x6 Buro-style positional weights (same table as 02-players/heuristics.py)
const W = [
  100, -20, 10, 10, -20, 100,
  -20, -50, -2, -2, -50, -20,
  10, -2, -1, -1, -2, 10,
  10, -2, -1, -1, -2, 10,
  -20, -50, -2, -2, -50, -20,
  100, -20, 10, 10, -20, 100,
];

let _seed = 1234567;
function rnd(): number { // tiny deterministic-ish PRNG (fine for a toy AI)
  _seed = (_seed * 1103515245 + 12345) & 0x7fffffff;
  return _seed / 0x7fffffff;
}
const pick = <T>(a: T[]): T => a[Math.floor(rnd() * a.length)];

function positional(board: number[], player: number): number {
  const opp = opponent(player);
  let s = 0;
  for (let i = 0; i < NN; i++) {
    if (board[i] === player) s += W[i];
    else if (board[i] === opp) s -= W[i];
  }
  return s;
}

function greedyMove(s: State, variant: Variant): number {
  const moves = legalMoves(s, variant);
  if (moves.length === 1) return moves[0];
  let best = -Infinity, bestMoves: number[] = [];
  for (const m of moves) {
    const child = applyMove(s, m, variant);
    const v = positional(child.board, s.toMove);
    if (v > best + 1e-9) { best = v; bestMoves = [m]; }
    else if (v >= best - 1e-9) bestMoves.push(m);
  }
  return pick(bestMoves);
}

function randomPlayout(s: State, variant: Variant): State {
  let cur = s;
  while (!isTerminal(cur)) cur = applyMove(cur, pick(legalMoves(cur, variant)), variant);
  return cur;
}

const resultFor = (s: State, player: number) => {
  const w = winner(s);
  return w === EMPTY ? 0.5 : w === player ? 1 : 0;
};

interface Node { state: State; parent: Node | null; move: number; children: Node[]; untried: number[]; n: number; w: number; }
const mkNode = (state: State, parent: Node | null, move: number, variant: Variant): Node =>
  ({ state, parent, move, children: [], untried: legalMoves(state, variant), n: 0, w: 0 });

function mctsMove(s: State, variant: Variant, budget: number): number {
  const moves = legalMoves(s, variant);
  if (moves.length === 1) return moves[0];
  const C = Math.SQRT2;
  const root = mkNode(s, null, -2, variant);
  for (let i = 0; i < budget; i++) {
    let node = root;
    while (node.untried.length === 0 && node.children.length > 0 && !isTerminal(node.state)) {
      let best = node.children[0], bestS = -Infinity;
      for (const ch of node.children) {
        const exploit = 1 - ch.w / ch.n;
        const explore = C * Math.sqrt(Math.log(node.n) / ch.n);
        const sc = exploit + explore;
        if (sc > bestS) { bestS = sc; best = ch; }
      }
      node = best;
    }
    if (node.untried.length && !isTerminal(node.state)) {
      const idx = Math.floor(rnd() * node.untried.length);
      const m = node.untried.splice(idx, 1)[0];
      const child = mkNode(applyMove(node.state, m, variant), node, m, variant);
      node.children.push(child);
      node = child;
    }
    const final = randomPlayout(node.state, variant);
    let cur: Node | null = node;
    while (cur) { cur.n++; cur.w += resultFor(final, cur.state.toMove); cur = cur.parent; }
  }
  let best = root.children[0];
  for (const ch of root.children) if (ch.n > best.n) best = ch;
  return best.move;
}

export function chooseMove(s: State, variant: Variant, kind: AIKind, budget = 800): number {
  if (legalMoves(s, variant)[0] === PASS) return PASS;
  if (kind === "random") return pick(legalMoves(s, variant));
  if (kind === "greedy") return greedyMove(s, variant);
  return mctsMove(s, variant, budget);
}
