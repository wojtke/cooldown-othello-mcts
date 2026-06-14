#!/usr/bin/env python
"""
Export plot data as .dat files for native pgfplots figures in the report.
Writes everything to 06-report/figs/. Run after the experiments:

  ../.venv/bin/python export_pgfdata.py \
      --tournament ../04-experiments/results/tournament

(Self-play / H4 is table-only, not plotted.)
"""
from __future__ import annotations
import argparse, glob, json, os
import optuna

import analyze as A  # reuse load_run, pair_summary, ranking_data, PLAYER_ORDER, PRETTY

optuna.logging.set_verbosity(optuna.logging.WARNING)
HERE = os.path.dirname(__file__)
FIGS = os.path.join(HERE, "..", "06-report", "figs")
STORAGE = f"sqlite:///{os.path.join(HERE, '..', '03-tuning', 'optuna', 'tuning.db')}"

# symbolic names safe for pgfplots (used for x ticks / coords)
SYM = {"random": "Random", "naive_buro": "Naive-Buro", "cooldown_buro": "Cooldown-Buro",
       "uct": "UCT", "uct_pb_naive": "UCT-PB-naive", "uct_pb_cooldown": "UCT-PB-cooldown"}


def w(name, text):
    with open(os.path.join(FIGS, name), "w") as f:
        f.write(text)


def export_ranking(tour):
    order, data = A.ranking_data(tour)
    lines = ["method classic cooldown"]
    for p in order:
        lines.append(f"{SYM[p]} {data[p]['classic']:.4f} {data[p]['cooldown']:.4f}")
    w("ranking.dat", "\n".join(lines) + "\n")


def export_heatmaps(tour):
    players = [p for p in A.PLAYER_ORDER if p in set(tour.black) | set(tour.white)]
    for variant in ("classic", "cooldown"):
        grid = ["x y c"]
        lab = ["x y c"]
        for yi, row in enumerate(players):           # row beats col
            for xi, col in enumerate(players):
                if row == col:
                    grid.append(f"{xi} {yi} nan")
                    continue
                rate = A.pair_summary(tour, variant, row, col)["rate"]
                grid.append(f"{xi} {yi} {rate:.4f}")
                lab.append(f"{xi} {yi} {rate:.2f}")
        w(f"heatmap_{variant}_grid.dat", "\n".join(grid) + "\n")
        w(f"heatmap_{variant}_lab.dat", "\n".join(lab) + "\n")
    # tick label list (pretty names, order)
    w("players.tex", ",".join(SYM[p] for p in players))


def export_margins(tour):
    players = [p for p in A.PLAYER_ORDER if p in set(tour.black) | set(tour.white)]
    for variant in ("classic", "cooldown"):
        for p in players:
            sub = tour[(tour.variant == variant)
                       & ((tour.black == p) | (tour.white == p))]
            vals = [(r.piece_diff_black if r.black == p else -r.piece_diff_black)
                    for _, r in sub.iterrows()]
            w(f"margin_{variant}_{p}.dat", "v\n" + "\n".join(str(v) for v in vals) + "\n")


def export_hists(tour):
    cl = tour[(tour.variant == "classic") & tour.whipsaw_rate.notna()]
    cd = tour[(tour.variant == "cooldown") & tour.cooldown_blocked_rate.notna()]
    w("whipsaw.dat", "v\n" + "\n".join(f"{v:.4f}" for v in cl.whipsaw_rate) + "\n")
    w("blocked.dat", "v\n" + "\n".join(f"{v:.4f}" for v in cd.cooldown_blocked_rate) + "\n")
    for variant in ("classic", "cooldown"):
        sub = tour[tour.variant == variant]
        w(f"lifespan_{variant}.dat",
          "v\n" + "\n".join(str(int(v)) for v in sub.lifespan_max) + "\n")


def export_gamelen(tour):
    """Game length (n_plies) per variant, for a classic-vs-cooldown histogram."""
    for variant in ("classic", "cooldown"):
        sub = tour[tour.variant == variant]
        w(f"gamelen_{variant}.dat",
          "v\n" + "\n".join(str(int(v)) for v in sub.n_plies) + "\n")


def export_tuning_influence(tuned, untuned):
    """Grouped-bar data: avg WR tuned vs default (literature) params, per method."""
    if untuned is None or not len(untuned):
        print("  (skip tuning_influence: no untuned tournament)"); return
    order, data = A.tuning_influence_data(tuned, untuned)
    lines = ["method tuned_classic def_classic tuned_cooldown def_cooldown"]
    for p in order:
        (tc, dc), (tk, dk) = data[p]["classic"], data[p]["cooldown"]
        lines.append(f"{SYM[p]} {tc:.4f} {dc:.4f} {tk:.4f} {dk:.4f}")
    w("ranking_tuned_untuned.dat", "\n".join(lines) + "\n")


def _study_dat(name, params, out):
    try:
        s = optuna.load_study(study_name=name, storage=STORAGE)
    except Exception as e:
        print(f"  (skip {name}: {e})"); return
    header = " ".join(params) + " value"
    rows = [header]
    for t in s.trials:
        if t.value is None:
            continue
        if all(p in t.params for p in params):
            rows.append(" ".join(f"{t.params[p]:.4f}" for p in params) + f" {t.value:.4f}")
    w(out, "\n".join(rows) + "\n")


def export_tuning():
    # only the UCT c-slices are still plotted (fig 6); the PB/Buro slice fig was dropped
    _study_dat("uct_classic", ["c"], "tune_uct_classic.dat")
    _study_dat("uct_cooldown", ["c"], "tune_uct_cooldown.dat")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tournament", required=True)
    ap.add_argument("--selfplay", default=None)
    ap.add_argument("--tournament-untuned", default=None)
    args = ap.parse_args()
    os.makedirs(FIGS, exist_ok=True)
    tour = A.load_run(args.tournament)
    selfp = A.load_run(args.selfplay) if args.selfplay else None
    untuned = A.load_run(args.tournament_untuned) if args.tournament_untuned else None
    export_ranking(tour)
    export_heatmaps(tour)
    export_margins(tour)
    export_hists(tour)
    export_gamelen(tour)
    export_tuning()
    export_tuning_influence(tour, untuned)
    print(f"wrote .dat files -> {FIGS}")
    print("files:", ", ".join(sorted(os.listdir(FIGS))[:6]), "...")


if __name__ == "__main__":
    main()
