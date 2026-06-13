// Cooldown Othello 6x6 — rules engine (TypeScript port of 01-game/engine.py).
// Same semantics as the Python authority; validated against 01-game/golden.json.

export const N = 6;
export const NN = 36;
export const EMPTY = 0, BLACK = 1, WHITE = 2;
export const PASS = -1;
export type Variant = "classic" | "cooldown";

const DIRS: Array<[number, number]> = [
  [-1, -1], [-1, 0], [-1, 1],
  [0, -1], [0, 1],
  [1, -1], [1, 0], [1, 1],
];

export const sq = (r: number, c: number) => r * N + c;
export const rc = (s: number): [number, number] => [Math.floor(s / N), s % N];

// RAYS[square][k] = square indices walking direction k to the edge
const RAYS: number[][][] = (() => {
  const rays: number[][][] = [];
  for (let s = 0; s < NN; s++) {
    const [r, c] = rc(s);
    const per: number[][] = [];
    for (const [dr, dc] of DIRS) {
      const line: number[] = [];
      let rr = r + dr, cc = c + dc;
      while (rr >= 0 && rr < N && cc >= 0 && cc < N) {
        line.push(sq(rr, cc));
        rr += dr; cc += dc;
      }
      per.push(line);
    }
    rays.push(per);
  }
  return rays;
})();

export interface State {
  board: number[];      // length 36, EMPTY/BLACK/WHITE
  toMove: number;
  cool: Set<number>;    // cooldown-marked squares (empty in classic)
  passes: number;
}

export function initialState(): State {
  const board = new Array(NN).fill(EMPTY);
  board[sq(2, 2)] = WHITE;
  board[sq(2, 3)] = BLACK;
  board[sq(3, 2)] = BLACK;
  board[sq(3, 3)] = WHITE;
  return { board, toMove: BLACK, cool: new Set(), passes: 0 };
}

export const opponent = (p: number) => (p === WHITE ? BLACK : WHITE);

// Cooldown-aware capture walk; with an empty `cool` this is classic Othello.
export function flipsFor(board: number[], cool: Set<number>, p: number, player: number): number[] {
  const opp = opponent(player);
  const flips: number[] = [];
  for (const ray of RAYS[p]) {
    const seg: number[] = [];
    let sawFree = false;
    for (const idx of ray) {
      const v = board[idx];
      if (v === opp) {
        seg.push(idx);
        if (!cool.has(idx)) sawFree = true;
        continue;
      }
      if (v === player) {
        if (seg.length && sawFree) {
          for (const j of seg) if (!cool.has(j)) flips.push(j);
        }
        break;
      }
      break; // EMPTY
    }
  }
  return flips;
}

export function legalMoves(s: State, _variant: Variant): number[] {
  const moves: number[] = [];
  for (let p = 0; p < NN; p++) {
    if (s.board[p] === EMPTY && flipsFor(s.board, s.cool, p, s.toMove).length) moves.push(p);
  }
  return moves.length ? moves : [PASS];
}

export function applyMove(s: State, move: number, variant: Variant): State {
  const opp = opponent(s.toMove);
  if (move === PASS) {
    return { board: s.board.slice(), toMove: opp, cool: new Set(), passes: s.passes + 1 };
  }
  const flips = flipsFor(s.board, s.cool, move, s.toMove);
  if (!flips.length) throw new Error("illegal move " + move);
  const nb = s.board.slice();
  nb[move] = s.toMove;
  for (const i of flips) nb[i] = s.toMove;
  const cool = variant === "cooldown" ? new Set<number>([move, ...flips]) : new Set<number>();
  return { board: nb, toMove: opp, cool, passes: 0 };
}

export const isTerminal = (s: State) => s.passes >= 2;

export function counts(s: State): [number, number] {
  let b = 0, w = 0;
  for (const v of s.board) { if (v === BLACK) b++; else if (v === WHITE) w++; }
  return [b, w];
}

export function winner(s: State): number {
  const [b, w] = counts(s);
  return b > w ? BLACK : w > b ? WHITE : EMPTY;
}

// Classically-legal placements blocked by the cooldown rule (for highlighting).
export function cooldownBlocked(s: State, variant: Variant): Set<number> {
  if (variant !== "cooldown") return new Set();
  const blocked = new Set<number>();
  const cd = new Set(legalMoves(s, variant));
  for (let p = 0; p < NN; p++) {
    if (s.board[p] === EMPTY && flipsFor(s.board, new Set(), p, s.toMove).length && !cd.has(p)) {
      blocked.add(p);
    }
  }
  return blocked;
}
