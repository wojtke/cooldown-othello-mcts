#!/usr/bin/env python
"""
Run the full tuning cascade in order (konspekt Table 1).

Order and control sets are fixed; each algorithm is added to the control set of
every algorithm tuned after it (tokens with "_t" load the just-written JSON).
Buro heuristics are tuned once on cooldown and reused for both variants; the
three MCTS algorithms are tuned separately per variant.

8 tuning runs total: naive_buro, cooldown_buro (cooldown only) +
{uct, uct_pb_naive, uct_pb_cooldown} x {classic, cooldown}.

Resumable end-to-end: every run resumes its own Optuna study, so re-running the
cascade continues where it stopped.

Usage:
  # dummy run (fast): tiny budget/trials/games
  python3 tune_cascade.py --budget 60 --trials 2 --games-per-control 2 --workers 4

  # full run on the rented machine (konspekt settings)
  python3 tune_cascade.py --budget 2000 --trials 30 --games-per-control 20 --workers 32
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from tune import tune_algorithm

# (algo, variants_to_tune, control_tokens) in cascade order
CASCADE = [
    ("naive_buro",      ["cooldown"],            [("random",), ("uct", "_def", 500), ("cooldown_buro", "_def")]),
    ("cooldown_buro",   ["cooldown"],            [("random",), ("naive_buro", "_t"), ("uct", "_def", 500)]),
    ("uct",             ["classic", "cooldown"], [("random",), ("naive_buro", "_t"), ("cooldown_buro", "_t")]),
    ("uct_pb_naive",    ["classic", "cooldown"], [("naive_buro", "_t"), ("cooldown_buro", "_t"), ("uct", "_t")]),
    ("uct_pb_cooldown", ["classic", "cooldown"], [("cooldown_buro", "_t"), ("uct", "_t"), ("uct_pb_naive", "_t")]),
]


def main():
    ap = argparse.ArgumentParser(description="Run the full tuning cascade")
    ap.add_argument("--budget", type=int, default=2000, help="B_tune (sims/move)")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--games-per-control", type=int, default=20)
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()

    print("=== Tuning cascade ===")
    for algo, variants, controls in CASCADE:
        for variant in variants:
            tune_algorithm(algo, variant, controls, args.budget, args.trials,
                           args.games_per_control, args.workers)
    print("\nCascade complete. Tuned JSONs in 03-tuning/results/.")


if __name__ == "__main__":
    main()
