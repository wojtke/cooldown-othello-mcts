#!/usr/bin/env python
"""
Empirical game statistics + golden vectors for the Othello 6x6 engine.

Two jobs (konspekt asks for the first before the main experiments):

  1. Random self-play over many games to measure mean game length and mean
     branching factor for each variant, to check the konspekt's estimates
     (classic ~ Othello-like; Cooldown 6x6 ~ length 28, branching 4).

  2. A small set of seeded "golden" games (move list + final board) dumped to
     JSON, used later to cross-check that a second engine implementation (the
     TypeScript web rules) reproduces identical games.

Usage:
  python3 stats.py                       # 1000 games/variant, print summary
  python3 stats.py --games 200           # fewer games
  python3 stats.py --golden golden.json  # also write golden vectors
"""

from __future__ import annotations

import argparse
import json
import random
from statistics import mean, median, pstdev

import engine as E
from engine import (apply_move, counts, initial_state, is_terminal, legal_moves,
                    piece_diff, winner)


def play_random_game(variant: str, rng: random.Random):
    """Play one random game; return (n_plies, branching_samples, final_state)."""
    s = initial_state()
    n_plies = 0
    branching = []   # number of legal placements at each genuine decision
    while not is_terminal(s):
        moves = legal_moves(s, variant)
        if moves != [E.PASS]:
            branching.append(len(moves))
        m = moves[rng.randrange(len(moves))]
        s = apply_move(s, m, variant)
        n_plies += 1
    return n_plies, branching, s


def measure(variant: str, n_games: int, seed: int) -> dict:
    rng = random.Random(seed)
    lengths = []
    branch_all = []
    black_wins = white_wins = draws = 0
    for _ in range(n_games):
        n_plies, branching, s = play_random_game(variant, rng)
        lengths.append(n_plies)
        branch_all.extend(branching)
        w = winner(s)
        if w == E.BLACK:
            black_wins += 1
        elif w == E.WHITE:
            white_wins += 1
        else:
            draws += 1
    return {
        "variant": variant,
        "n_games": n_games,
        "mean_length": round(mean(lengths), 2),
        "median_length": median(lengths),
        "std_length": round(pstdev(lengths), 2),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "mean_branching": round(mean(branch_all), 2),
        "max_branching": max(branch_all),
        "black_win_rate": round(black_wins / n_games, 3),
        "white_win_rate": round(white_wins / n_games, 3),
        "draw_rate": round(draws / n_games, 3),
    }


def make_golden(variant: str, seeds) -> list[dict]:
    """Seeded games recorded as move lists + final boards (engine cross-check)."""
    out = []
    for seed in seeds:
        rng = random.Random(seed)
        s = initial_state()
        moves = []
        while not is_terminal(s):
            ms = legal_moves(s, variant)
            m = ms[rng.randrange(len(ms))]
            moves.append(m)
            s = apply_move(s, m, variant)
        b, w = counts(s)
        out.append({
            "variant": variant,
            "seed": seed,
            "moves": moves,                       # PASS encoded as -1
            "final_board": list(s.board),
            "black": b, "white": w,
            "winner": winner(s),
            "piece_diff": piece_diff(s),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Engine stats + golden vectors")
    ap.add_argument("--games", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--golden", type=str, default=None,
                    help="write golden vectors to this JSON path")
    ap.add_argument("--golden-seeds", type=int, nargs="+", default=[1, 2, 3])
    args = ap.parse_args()

    print(f"Random self-play: {args.games} games/variant (seed={args.seed})\n")
    header = (f"{'variant':9s} {'len(mean)':>9s} {'len(med)':>8s} {'len(std)':>8s} "
              f"{'len[min,max]':>14s} {'branch':>7s} {'B/W/draw win%':>16s}")
    print(header)
    print("-" * len(header))
    results = []
    for variant in E.VARIANTS:
        r = measure(variant, args.games, args.seed)
        results.append(r)
        print(f"{r['variant']:9s} {r['mean_length']:>9.2f} {r['median_length']:>8} "
              f"{r['std_length']:>8.2f} "
              f"{('['+str(r['min_length'])+','+str(r['max_length'])+']'):>14s} "
              f"{r['mean_branching']:>7.2f} "
              f"{(str(r['black_win_rate'])+'/'+str(r['white_win_rate'])+'/'+str(r['draw_rate'])):>16s}")

    if args.golden:
        golden = []
        for variant in E.VARIANTS:
            golden.extend(make_golden(variant, args.golden_seeds))
        with open(args.golden, "w") as f:
            json.dump(golden, f, indent=2)
        print(f"\nWrote {len(golden)} golden vectors to {args.golden}")


if __name__ == "__main__":
    main()
