// Off-main-thread AI: runs chooseMove so the board never freezes during search.
// Bundled as a static module worker by Vite — hosts on GitHub Pages unchanged.
import { State, Variant } from "./engine";
import { AIKind, chooseMove } from "./ai";

interface Req {
  gen: number;            // turn token, echoed back so stale results can be dropped
  board: number[];
  toMove: number;
  cool: number[];         // Set serialized as an array
  passes: number;
  variant: Variant;
  kind: AIKind;
  budget: number;
}

const ctx = self as unknown as {
  onmessage: ((e: MessageEvent<Req>) => void) | null;
  postMessage: (m: { gen: number; move: number }) => void;
};

ctx.onmessage = (e) => {
  const r = e.data;
  const state: State = {
    board: r.board, toMove: r.toMove, cool: new Set<number>(r.cool), passes: r.passes,
  };
  const move = chooseMove(state, r.variant, r.kind, r.budget);
  ctx.postMessage({ gen: r.gen, move });
};
