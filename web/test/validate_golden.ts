// Parity check: the TS engine must reproduce the Python golden vectors exactly.
// Run: npm run validate   (reads ../01-game/golden.json relative to repo root)
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { applyMove, counts, initialState, winner, State, Variant } from "../src/engine";

interface Golden {
  variant: Variant; seed: number; moves: number[];
  final_board: number[]; black: number; white: number; winner: number;
}

const path = fileURLToPath(new URL("../../01-game/golden.json", import.meta.url));
const golden: Golden[] = JSON.parse(readFileSync(path, "utf8"));

let ok = 0;
const fails: string[] = [];
for (const g of golden) {
  let s: State = initialState();
  for (const m of g.moves) s = applyMove(s, m, g.variant);
  const [b, w] = counts(s);
  const boardOk = JSON.stringify(s.board) === JSON.stringify(g.final_board);
  if (boardOk && b === g.black && w === g.white && winner(s) === g.winner) ok++;
  else fails.push(`${g.variant} seed=${g.seed} (board=${boardOk} B=${b}/${g.black} W=${w}/${g.white})`);
}

console.log(`golden parity: ${ok}/${golden.length} games match the Python engine`);
if (fails.length) { for (const f of fails) console.error("  MISMATCH " + f); process.exit(1); }
