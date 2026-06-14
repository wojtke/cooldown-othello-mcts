// Off-main-thread AI: runs chooseMove so the board never freezes during search,
// and streams progress so the UI can show a loading bar. Bundled as a static
// module worker by Vite — hosts on GitHub Pages unchanged.
import { State, Variant } from "./engine";
import { AIConfig, chooseMove } from "./ai";

interface Req {
  gen: number;            // turn token, echoed back so stale results can be dropped
  board: number[];
  toMove: number;
  cool: number[];         // Set serialized as an array
  passes: number;
  variant: Variant;
  cfg: AIConfig;
}

const ctx = self as unknown as {
  onmessage: ((e: MessageEvent<Req>) => void) | null;
  postMessage: (m: { type: "progress" | "result"; gen: number; frac?: number; move?: number }) => void;
};

ctx.onmessage = (e) => {
  const r = e.data;
  const state: State = {
    board: r.board, toMove: r.toMove, cool: new Set<number>(r.cool), passes: r.passes,
  };
  const move = chooseMove(state, r.variant, r.cfg, (done, total) => {
    ctx.postMessage({ type: "progress", gen: r.gen, frac: done / total });
  });
  ctx.postMessage({ type: "result", gen: r.gen, move });
};
