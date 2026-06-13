#!/usr/bin/env python
"""
Round-robin tournament driver (konspekt main experiment, H1-H3).

For each game variant, every unordered pair of selected players plays `--games`
games with alternating starting colors (half each). Games are dispatched to a
process pool and written incrementally to per-pairing JSONL shards; re-running
the same command resumes (skips completed game_ids).

Examples:
  # smoke: 3 players, tiny budget, 4 games/pair, both variants
  python3 run_tournament.py --players random naive_buro uct --budget 60 \
      --games 4 --workers 2 --run-name smoke

  # full main experiment (on the rented machine)
  python3 run_tournament.py --variant both --games 200 --budget 10000 \
      --workers 32 --run-name tournament
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game import (derive_seeds, game_id, load_tuned_overrides, normalize_spec,
                  spec_label)
from players import PLAYER_NAMES
from runner import run_tasks

_DEFAULT_TUNING_DIR = os.path.join(os.path.dirname(__file__), "..", "03-tuning", "results")


def _spec(name, variant, budget, tuning_dir):
    overrides = {"budget": budget}
    overrides.update(load_tuned_overrides(name, variant, tuning_dir))
    return normalize_spec(name, overrides)


def build_tasks(variants, player_names, games, budget, tuning_dir):
    tasks = []
    for variant in variants:
        for a, b in itertools.combinations(player_names, 2):
            spec_a = _spec(a, variant, budget, tuning_dir)
            spec_b = _spec(b, variant, budget, tuning_dir)
            shard = f"{variant}__{spec_label(spec_a)}__vs__{spec_label(spec_b)}"
            for g in range(games):
                # alternate starting color; seeds keyed by game index (pairs across variants)
                black, white = (spec_a, spec_b) if g % 2 == 0 else (spec_b, spec_a)
                seeds = derive_seeds(g)
                tasks.append({
                    "game_id": game_id(variant, black, white, seeds),
                    "shard": shard,
                    "variant": variant,
                    "black": black,
                    "white": white,
                    "seeds": seeds,
                    "collect_metrics": True,
                })
    return tasks


def main():
    ap = argparse.ArgumentParser(description="Round-robin tournament driver")
    ap.add_argument("--variant", choices=["classic", "cooldown", "both"], default="both")
    ap.add_argument("--players", nargs="+", default=list(PLAYER_NAMES))
    ap.add_argument("--games", type=int, default=200, help="games per pairing")
    ap.add_argument("--budget", type=int, default=10000, help="MCTS simulations per move")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--run-name", default="tournament")
    ap.add_argument("--tuning-dir", default=_DEFAULT_TUNING_DIR,
                    help="dir with tuned JSONs (03-tuning/results); '' to use defaults")
    ap.add_argument("--no-tuned", action="store_true", help="ignore tuned params")
    ap.add_argument("--fresh", action="store_true", help="ignore existing results (no resume)")
    args = ap.parse_args()

    tuning_dir = "" if args.no_tuned else args.tuning_dir
    variants = ["classic", "cooldown"] if args.variant == "both" else [args.variant]
    tasks = build_tasks(variants, args.players, args.games, args.budget, tuning_dir)
    run_dir = os.path.join(os.path.dirname(__file__), args.out_dir, args.run_name)

    have_tuned = bool(tuning_dir and os.path.isdir(tuning_dir)
                      and any(f.startswith("tune_") for f in os.listdir(tuning_dir)))
    print(f"Variants  : {variants}")
    print(f"Players   : {args.players}")
    print(f"Games/pair: {args.games}   Budget: {args.budget}")
    print(f"Tuned     : {'loaded from ' + tuning_dir if have_tuned else 'NONE (defaults)'}")
    run_tasks(tasks, run_dir, workers=args.workers, resume=not args.fresh)


if __name__ == "__main__":
    main()
