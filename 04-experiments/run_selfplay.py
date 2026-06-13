#!/usr/bin/env python
"""
Self-play driver for H4 (second-player advantage under each rule set).

The strongest variant plays itself for many games per game-variant, with
distinct RNG streams for the two colors of each game (black_seed != white_seed),
so there is no identical-rollout artifact. Analysis reports the second-player
(White) win rate with a Wilson CI. Incremental + resumable like the tournament.

Examples:
  python3 run_selfplay.py --player uct --budget 60 --games 4 --run-name smoke
  python3 run_selfplay.py --player uct_pb_cooldown --games 2000 --budget 10000 \
      --workers 32 --run-name selfplay
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game import (derive_seeds, game_id, load_tuned_overrides, normalize_spec,
                  spec_label)
from runner import run_tasks

_DEFAULT_TUNING_DIR = os.path.join(os.path.dirname(__file__), "..", "03-tuning", "results")


def build_tasks(variants, player_name, games, budget, tuning_dir):
    tasks = []
    for variant in variants:
        overrides = {"budget": budget}
        overrides.update(load_tuned_overrides(player_name, variant, tuning_dir))
        spec = normalize_spec(player_name, overrides)
        shard = f"{variant}__selfplay__{spec_label(spec)}"
        for g in range(games):
            seeds = derive_seeds(g)  # black=2M+g, white=3M+g -> distinct streams
            tasks.append({
                "game_id": game_id(variant, spec, spec, seeds),
                "shard": shard,
                "variant": variant,
                "black": spec,
                "white": spec,
                "seeds": seeds,
                "collect_metrics": True,
            })
    return tasks


def main():
    ap = argparse.ArgumentParser(description="Self-play driver (H4)")
    ap.add_argument("--variant", choices=["classic", "cooldown", "both"], default="both")
    ap.add_argument("--player", default="uct_pb_cooldown")
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--budget", type=int, default=10000)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--run-name", default="selfplay")
    ap.add_argument("--tuning-dir", default=_DEFAULT_TUNING_DIR)
    ap.add_argument("--no-tuned", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args()

    tuning_dir = "" if args.no_tuned else args.tuning_dir
    variants = ["classic", "cooldown"] if args.variant == "both" else [args.variant]
    tasks = build_tasks(variants, args.player, args.games, args.budget, tuning_dir)
    run_dir = os.path.join(os.path.dirname(__file__), args.out_dir, args.run_name)

    print(f"Variants  : {variants}")
    print(f"Player    : {args.player}   Games/variant: {args.games}   Budget: {args.budget}")
    run_tasks(tasks, run_dir, workers=args.workers, resume=not args.fresh)


if __name__ == "__main__":
    main()
