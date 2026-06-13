# P2 — MCTS/UCT for Cooldown Othello 6×6 — STATUS

Single source of truth (mirrors `p1_cvrp/STATUS.md`). Updated as phases land.

## Environment
- Stock macOS **Python 3.9.6**, no scientific libs installed. Phases `01-game` and
  `02-players` are pure-Python (zero deps) and run as-is. `03-tuning` / `05-analysis`
  will use a local `.venv` (optuna, scipy, pandas, matplotlib) — set up when we get there.
- Code is written 3.9-compatible (`from __future__ import annotations`, no `match`).
- No full experiments on this Mac — small dummy runs only; full runs on a rented many-core box.

## Phase status
- [x] **00-konspekt** — locked research design (given).
- [x] **01-game** — engine + tests (9/9) + stats + golden vectors. **DONE.**
- [x] **02-players** — Random, Naive/Cooldown-Buro, UCT, UCT-PB(±cooldown); tests 5/5. **DONE.**
- [x] **04-experiments** — game runner, tournament/self-play drivers, incremental+resumable
      JSONL (crash-resume verified). **DONE.**
- [x] **03-tuning** — Optuna TPE cascade (8 runs, multiprocessing, resumable SQLite). **DONE.**
- [x] **05-analysis** — Wilson CI, McNemar, Holm-Bonferroni, cooldown metrics, plots/tables.
      **DONE.**
- [ ] **06-report / 07-slides** — LaTeX (reuse p1 template). Awaiting real results.
- [ ] **web/ + human-study** — LATER (after analysis): TS frontend + FastAPI study server.

**The full compute pipeline (01→05) is coded, unit-tested, and validated end-to-end with small
dummy runs on this Mac (multiprocessing + crash-resume working). Ready to scale on a rented
many-core CPU box.** No full runs done here by design.

## Perf calibration (measured on this Mac, 1 core)
- One uct-vs-uct game: **B=10000 ≈ 78 s** (~2.3 s/move, 36 plies); **B=2000 ≈ 15.5 s**.
- Full workload extrapolation (~6000 tournament + ~4000 self-play @ B=10000, ~14400 tuning @
  B=2000; many games have cheap Random/Buro opponents): **~3–6 h on 32–64 cores**. Rent a
  high-core CPU box; **no GPU** (confirmed). numba could cut per-game ~10× if ever needed.
- Web study can afford near-full budget (2.3 s/move is fine for humans).

## How to run the real experiments (rented machine)
```bash
# 1) tune (B_tune=2000): writes 03-tuning/results/tune_*.json
../.venv/bin/python 03-tuning/tune_cascade.py --budget 2000 --trials 30 --games-per-control 20 --workers <N>
# 2) main tournament (B=10000): 04-experiments/results/tournament/
python3 04-experiments/run_tournament.py --variant both --games 200 --budget 10000 --workers <N> --run-name tournament
# 3) H4 self-play:
python3 04-experiments/run_selfplay.py --player uct_pb_cooldown --games 2000 --budget 10000 --workers <N> --run-name selfplay
# 4) analyse:
../.venv/bin/python 05-analysis/analyze.py --tournament 04-experiments/results/tournament --selfplay 04-experiments/results/selfplay
```
The tournament/self-play drivers auto-load tuned params from `03-tuning/results/` (per-variant for
MCTS, shared for Buro); pass `--no-tuned` to force defaults. So run step 1 before step 2.
Calibrate wall-time by timing one B=10000 game first.

## 01-game notes
- `engine.py`: immutable hashable `State(board, to_move, cool, passes)`; one cooldown-aware
  capture walk serves both variants (classic = empty `cool`). Hot fns (`legal_moves`,
  `apply_move`, `random_playout`) isolated for a possible future bitboard swap.
- `test_engine.py`: 9/9 pass — incl. the defining **cooldown whipsaw-protection** case
  (a reply that re-flips a just-captured piece is legal in classic, illegal in cooldown).
- Run as `python3 test_engine.py` (no pytest needed) or under pytest.

### Empirical verification (1000 random games/variant, seed 0) — konspekt asked for this
| variant  | mean length | mean branching | B/W/draw win rate |
|----------|-------------|----------------|-------------------|
| classic  | 34.46       | 5.28           | 0.429 / 0.517 / 0.054 |
| cooldown | 34.60       | 4.54           | 0.453 / 0.492 / 0.055 |

**Findings to carry into the report:**
- Cooldown **lowers branching** (4.54 vs 5.28) as expected (some captures blocked), but
  **does not shorten games** — length ≈ classic (~34 plies incl. terminal passes), because
  6×6 boards fill up regardless. The konspekt's preliminary "~28" length estimate is **too low**;
  update it with the measured value.
- Under *random* play, the 2nd-player (White) edge is **smaller under cooldown** (0.492 vs
  0.517) — directionally consistent with **H4**, to be confirmed with strong MCTS self-play.
- `golden.json`: 6 seeded games (3/variant) recorded as move-lists + final boards; the TS web
  engine must reproduce these exactly (rule parity check).

## Review-harden pass (before the paid run)
Independent adversarial review of the trickiest modules (cooldown rule, MCTS backprop, heuristics)
against the konspekt, plus added tests. Whole suite: `./run_tests.sh` (29 tests, ~24s).
- **engine.py — verified correct.** Cooldown legality/execution/pass match konspekt §3.2; the
  invariant "cooled squares are opponent-colored at the mover's turn" holds. A **differential test**
  (`01-game/test_engine_diff.py`) cross-checks legal moves + every move's flips against an
  independent (row,col) walk over **4144 positions / 19071 move-flips**, both variants — all match.
- **mcts.py — verified correct.** UCB perspective/sign correct at root and depth; terminals safe;
  no div-by-zero; progressive-bias H normalized in the mover's perspective. Added
  `test_uct_stronger_with_more_budget` (search monotonicity).
- **heuristics.py — BUG FOUND & FIXED.** `cooldown_term` rewarded a flip shielded on one axis even
  when re-flippable on another (`if protected … elif vulnerable` inverted the sign on a move the
  spec wants penalized). Fixed so **vulnerability takes precedence** (penalty dominates local
  shielding). Regression test: `02-players/test_heuristics.py`.
- Also added `04-experiments/test_metrics.py` (metrics vs independent board-diff replay) and
  `05-analysis/test_stats.py` (Wilson/McNemar/Holm/binomial known values).

## Open questions / deviations
- None blocking. Length-estimate correction above is a logged deviation from the konspekt's
  preliminary numbers (which it explicitly said to verify).
