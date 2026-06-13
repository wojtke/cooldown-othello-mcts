#!/usr/bin/env python
"""
Analysis for the Cooldown-Othello experiments (konspekt sec. 6.5).

Reads the JSONL shards produced by 04-experiments and emits:
  * tables/  — LaTeX win-rate matrices, a cooldown-metrics table, an H1-H4
    verdict table, and a plain-text verdict report;
  * figures/ — win-rate heatmaps (per variant), end-margin boxplots, cooldown
    metric plots.

Statistics: win rate counts a draw as half a win; Wilson 95% CI on (rate, n);
significance of "beats chance" by binomial test; McNemar for seed-paired
classic-vs-cooldown comparisons; Holm-Bonferroni across the primary hypothesis
family; effect sizes (win-rate differences) reported with every p-value.

Usage:
  ../.venv/bin/python analyze.py --tournament ../04-experiments/results/dummy \
      --selfplay ../04-experiments/results/dummy_selfplay
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(__file__)
TABLES = os.path.join(HERE, "tables")
FIGURES = os.path.join(HERE, "figures")

PLAYER_ORDER = ["random", "naive_buro", "cooldown_buro", "uct",
                "uct_pb_naive", "uct_pb_cooldown"]
PRETTY = {"random": "Random", "naive_buro": "Naive-Buro",
          "cooldown_buro": "Cooldown-Buro", "uct": "UCT",
          "uct_pb_naive": "UCT-PB-naive", "uct_pb_cooldown": "UCT-PB-cooldown"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_run(run_dir: str) -> pd.DataFrame:
    rows = []
    for fn in sorted(os.listdir(run_dir)):
        if not fn.endswith(".jsonl"):
            continue
        with open(os.path.join(run_dir, fn)) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                m = r.get("metrics", {}) or {}
                rows.append({
                    "game_id": r["game_id"],
                    "variant": r["variant"],
                    "black": r["black"]["name"],
                    "white": r["white"]["name"],
                    "winner": r["winner"],
                    "result_black": r["result_black"],
                    "piece_diff_black": r["piece_diff_black"],
                    "n_plies": r["n_plies"],
                    "seed_game": r["seeds"]["game"],
                    "whipsaw_rate": m.get("whipsaw_rate"),
                    "cooldown_blocked_rate": m.get("cooldown_blocked_rate"),
                    "lifespan_mean": m.get("lifespan_mean"),
                    "lifespan_max": m.get("lifespan_max"),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Stats primitives
# ---------------------------------------------------------------------------

def wilson_ci(successes: float, n: int, z: float = 1.96):
    """(rate, lo, hi). `successes` may be fractional (draws as 0.5)."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, center - half), min(1.0, center + half)


def binom_p(successes: float, n: int) -> float:
    """Two-sided binomial test vs 0.5 (fractional successes rounded)."""
    if n == 0:
        return 1.0
    k = int(round(successes))
    return stats.binomtest(k, n, 0.5).pvalue


def mcnemar_p(b: int, c: int) -> float:
    """Two-sided McNemar exact test on discordant pair counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2.0 * stats.binom.cdf(k, n, 0.5))


def holm_bonferroni(pvals: dict) -> dict:
    """Holm-Bonferroni adjusted p-values for a family keyed by name."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj = {}
    running = 0.0
    for i, (k, p) in enumerate(items):
        a = min(1.0, (m - i) * p)
        running = max(running, a)      # enforce monotonicity
        adj[k] = running
    return adj


# ---------------------------------------------------------------------------
# Head-to-head
# ---------------------------------------------------------------------------

def focal_scores(df: pd.DataFrame, variant: str, focal: str, opp: str) -> list:
    """List of focal-perspective scores (1/0.5/0) for focal-vs-opp games."""
    sub = df[(df.variant == variant)
             & (((df.black == focal) & (df.white == opp))
                | ((df.black == opp) & (df.white == focal)))]
    scores = []
    for _, r in sub.iterrows():
        s = r.result_black if r.black == focal else 1.0 - r.result_black
        scores.append(s)
    return scores


def pair_summary(df, variant, focal, opp) -> dict:
    scores = focal_scores(df, variant, focal, opp)
    n = len(scores)
    succ = sum(scores)
    rate, lo, hi = wilson_ci(succ, n)
    return {"n": n, "rate": rate, "lo": lo, "hi": hi,
            "p": binom_p(succ, n), "succ": succ}


# ---------------------------------------------------------------------------
# Hypotheses
# ---------------------------------------------------------------------------

def evaluate_hypotheses(tour: pd.DataFrame, selfp: pd.DataFrame) -> dict:
    H = {}
    primary_p = {}

    # H1: UCT beats Naive-Buro; >=60% on cooldown; advantage larger on cooldown.
    h1c = pair_summary(tour, "cooldown", "uct", "naive_buro")
    h1k = pair_summary(tour, "classic", "uct", "naive_buro")
    H["H1"] = {
        "desc": "UCT beats Naive-Buro (>=60% on cooldown; bigger edge on cooldown)",
        "cooldown_rate": h1c["rate"], "cooldown_ci": (h1c["lo"], h1c["hi"]),
        "classic_rate": h1k["rate"],
        "edge_cooldown_vs_classic": h1c["rate"] - h1k["rate"],
        "supported": (h1c["rate"] >= 0.60) and (h1c["rate"] > h1k["rate"]),
        "p": h1c["p"], "n": h1c["n"],
    }
    primary_p["H1"] = h1c["p"]

    # H2: uct_pb_cooldown beats UCT on cooldown by >=10pp, more than uct_pb_naive does.
    h2cool = pair_summary(tour, "cooldown", "uct_pb_cooldown", "uct")
    h2naive = pair_summary(tour, "cooldown", "uct_pb_naive", "uct")
    H["H2"] = {
        "desc": "UCT-PB-cooldown > UCT on cooldown by >=10pp, more than UCT-PB-naive",
        "pb_cooldown_rate": h2cool["rate"], "pb_cooldown_ci": (h2cool["lo"], h2cool["hi"]),
        "pb_naive_rate": h2naive["rate"],
        "edge_pp": (h2cool["rate"] - 0.5) * 100,
        "supported": (h2cool["rate"] - 0.5 >= 0.10) and (h2cool["rate"] > h2naive["rate"]),
        "p": h2cool["p"], "n": h2cool["n"],
    }
    primary_p["H2"] = h2cool["p"]

    # H3: Cooldown-Buro beats Naive-Buro on cooldown (>=10pp) but ~equal on classic (<5pp).
    h3cool = pair_summary(tour, "cooldown", "cooldown_buro", "naive_buro")
    h3clas = pair_summary(tour, "classic", "cooldown_buro", "naive_buro")
    # McNemar paired by game seed (same seed in classic vs cooldown)
    b, c = _discordant(tour, "cooldown_buro", "naive_buro")
    H["H3"] = {
        "desc": "Cooldown-Buro > Naive-Buro on cooldown (>=10pp), ~equal on classic (<5pp)",
        "cooldown_rate": h3cool["rate"], "cooldown_ci": (h3cool["lo"], h3cool["hi"]),
        "classic_rate": h3clas["rate"],
        "cooldown_edge_pp": (h3cool["rate"] - 0.5) * 100,
        "classic_edge_pp": (h3clas["rate"] - 0.5) * 100,
        "supported": (h3cool["rate"] - 0.5 >= 0.10) and (abs(h3clas["rate"] - 0.5) < 0.05),
        "p": h3cool["p"], "mcnemar_p": mcnemar_p(b, c), "n": h3cool["n"],
    }
    primary_p["H3"] = h3cool["p"]

    # H4: second-player (White) win rate >=55% classic, <=50% cooldown (self-play).
    if selfp is not None and len(selfp):
        H["H4"] = {"desc": "2nd-player edge vanishes under cooldown (self-play)"}
        for variant in ("classic", "cooldown"):
            sub = selfp[selfp.variant == variant]
            n = len(sub)
            white_succ = float((1.0 - sub.result_black).sum())  # white score
            rate, lo, hi = wilson_ci(white_succ, n)
            H["H4"][variant] = {"white_rate": rate, "ci": (lo, hi), "n": n,
                                "p": binom_p(white_succ, n)}
        c_rate = H["H4"]["classic"]["white_rate"]
        k_rate = H["H4"]["cooldown"]["white_rate"]
        H["H4"]["supported"] = (c_rate >= 0.55) and (k_rate <= 0.50)
        H["H4"]["p"] = H["H4"]["classic"]["p"]   # significance that classic has a 2nd-player edge
        primary_p["H4"] = H["H4"]["classic"]["p"]

    H["_holm"] = holm_bonferroni(primary_p)
    return H


def _discordant(df, focal, opp):
    """McNemar discordant counts pairing classic vs cooldown by game seed."""
    def outcome(variant):
        sub = df[(df.variant == variant)
                 & (((df.black == focal) & (df.white == opp))
                    | ((df.black == opp) & (df.white == focal)))]
        out = {}
        for _, r in sub.iterrows():
            s = r.result_black if r.black == focal else 1.0 - r.result_black
            out[r.seed_game] = 1 if s == 1.0 else 0  # win vs not-win
        return out
    a, bm = outcome("classic"), outcome("cooldown")
    b = c = 0
    for k in set(a) & set(bm):
        if a[k] == 1 and bm[k] == 0:
            b += 1
        elif a[k] == 0 and bm[k] == 1:
            c += 1
    return b, c


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_heatmaps(tour: pd.DataFrame):
    players = [p for p in PLAYER_ORDER if p in set(tour.black) | set(tour.white)]
    for variant in sorted(tour.variant.unique()):
        M = np.full((len(players), len(players)), np.nan)
        for i, a in enumerate(players):
            for j, b in enumerate(players):
                if a == b:
                    continue
                s = pair_summary(tour, variant, a, b)
                if s["n"]:
                    M[i, j] = s["rate"]
        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=1)
        ax.set_xticks(range(len(players)))
        ax.set_yticks(range(len(players)))
        ax.set_xticklabels([PRETTY[p] for p in players], rotation=45, ha="right")
        ax.set_yticklabels([PRETTY[p] for p in players])
        for i in range(len(players)):
            for j in range(len(players)):
                if not np.isnan(M[i, j]):
                    ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=8)
        ax.set_title(f"Row win rate vs column — {variant} 6x6")
        fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        fig.savefig(os.path.join(FIGURES, f"heatmap_winrate_{variant}.png"), dpi=130)
        plt.close(fig)


def fig_margin_boxplots(tour: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, variant in zip(axes, sorted(tour.variant.unique())):
        data, labels = [], []
        for p in PLAYER_ORDER:
            sub = tour[(tour.variant == variant) & ((tour.black == p) | (tour.white == p))]
            margins = [(r.piece_diff_black if r.black == p else -r.piece_diff_black)
                       for _, r in sub.iterrows()]
            if margins:
                data.append(margins)
                labels.append(PRETTY[p])
        ax.boxplot(data, tick_labels=labels)  # vertical is the default (mpl-version safe)
        ax.axhline(0, color="grey", lw=0.8, ls="--")
        ax.set_title(f"End margin (focal − opp) — {variant}")
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "margin_boxplots.png"), dpi=130)
    plt.close(fig)


def fig_cooldown_metrics(tour: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    classic = tour[(tour.variant == "classic") & tour.whipsaw_rate.notna()]
    cool = tour[(tour.variant == "cooldown") & tour.cooldown_blocked_rate.notna()]
    axes[0].hist(classic.whipsaw_rate.values, bins=20, color="steelblue")
    axes[0].set_title("Whipsaw rate (classic games)")
    axes[0].set_xlabel("fraction of moves illegal under cooldown")
    axes[1].hist(cool.cooldown_blocked_rate.values, bins=20, color="indianred")
    axes[1].set_title("Cooldown-blocked rate (cooldown games)")
    axes[1].set_xlabel("fraction of decisions with a blocked move")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "cooldown_metrics.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def _tex_table(body_rows, header, caption, label) -> str:
    cols = "l" + "r" * (len(header) - 1)
    lines = [r"\begin{table}[h]", r"\centering", r"\small",
             rf"\begin{{tabular}}{{{cols}}}", r"\toprule",
             " & ".join(header) + r" \\", r"\midrule"]
    lines += [" & ".join(row) + r" \\" for row in body_rows]
    lines += [r"\bottomrule", r"\end{tabular}",
              rf"\caption{{{caption}}}", rf"\label{{{label}}}", r"\end{table}"]
    return "\n".join(lines)


def table_winrate_matrix(tour, variant) -> str:
    players = [p for p in PLAYER_ORDER if p in set(tour.black) | set(tour.white)]
    header = ["Player"] + [PRETTY[p] for p in players]
    rows = []
    for a in players:
        row = [PRETTY[a]]
        for b in players:
            if a == b:
                row.append("--")
            else:
                s = pair_summary(tour, variant, a, b)
                row.append(f"{s['rate']:.2f}" if s["n"] else "n/a")
        rows.append(row)
    return _tex_table(rows, header,
                      f"Row win rate vs column, {variant} 6x6.",
                      f"tab:winrate_{variant}")


def table_cooldown_metrics(tour) -> str:
    header = ["Variant", "whipsaw", "blocked", "lifespan(mean)", "lifespan(max)"]
    rows = []
    for variant in sorted(tour.variant.unique()):
        sub = tour[tour.variant == variant]
        wr = sub.whipsaw_rate.dropna()
        br = sub.cooldown_blocked_rate.dropna()
        rows.append([variant,
                     f"{wr.mean():.3f}" if len(wr) else "--",
                     f"{br.mean():.3f}" if len(br) else "--",
                     f"{sub.lifespan_mean.mean():.2f}",
                     f"{sub.lifespan_max.mean():.2f}"])
    return _tex_table(rows, header, "Cooldown-specific metrics by variant.",
                      "tab:cooldown_metrics")


def verdict_report(H: dict) -> str:
    lines = ["HYPOTHESIS VERDICTS", "=" * 60, ""]
    holm = H.get("_holm", {})
    for key in ("H1", "H2", "H3", "H4"):
        if key not in H:
            continue
        h = H[key]
        verdict = "SUPPORTED" if h.get("supported") else "not supported"
        lines.append(f"{key}: {verdict}")
        lines.append(f"   {h['desc']}")
        for k, v in h.items():
            if k in ("desc", "supported"):
                continue
            lines.append(f"     {k}: {v}")
        if key in holm:
            lines.append(f"     holm_adjusted_p: {holm[key]:.4f}")
        lines.append("")
    return "\n".join(lines)


def table_hypotheses(H: dict) -> str:
    header = ["Hip.", "Wynik", "kluczowy efekt", "$p$", "holm-$p$"]
    holm = H.get("_holm", {})
    rows = []
    eff = {
        "H1": lambda h: f"WR cooldown {h['cooldown_rate']:.2f}",
        "H2": lambda h: f"przewaga {h['edge_pp']:.0f} p.p.",
        "H3": lambda h: f"cool {h['cooldown_edge_pp']:.0f} / klasyk {h['classic_edge_pp']:.0f} p.p.",
        "H4": lambda h: f"biały {h['classic']['white_rate']:.2f} / {h['cooldown']['white_rate']:.2f}",
    }
    for key in ("H1", "H2", "H3", "H4"):
        if key not in H:
            continue
        h = H[key]
        p = h.get("p", float("nan"))
        rows.append([key, "tak" if h.get("supported") else "nie", eff[key](h),
                     f"{p:.3f}", f"{holm.get(key, float('nan')):.3f}"])
    return _tex_table(rows, header, "Weryfikacja hipotez (wielkość efektu + $p$).",
                      "tab:hypotheses")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Analyse Cooldown-Othello results")
    ap.add_argument("--tournament", required=True, help="tournament run dir")
    ap.add_argument("--selfplay", default=None, help="self-play run dir (for H4)")
    args = ap.parse_args()

    os.makedirs(TABLES, exist_ok=True)
    os.makedirs(FIGURES, exist_ok=True)

    tour = load_run(args.tournament)
    selfp = load_run(args.selfplay) if args.selfplay else None
    print(f"Loaded {len(tour)} tournament games"
          + (f", {len(selfp)} self-play games" if selfp is not None else ""))

    H = evaluate_hypotheses(tour, selfp)

    # tables
    for variant in sorted(tour.variant.unique()):
        with open(os.path.join(TABLES, f"winrate_{variant}.tex"), "w") as f:
            f.write(table_winrate_matrix(tour, variant))
    with open(os.path.join(TABLES, "cooldown_metrics.tex"), "w") as f:
        f.write(table_cooldown_metrics(tour))
    with open(os.path.join(TABLES, "hypotheses.tex"), "w") as f:
        f.write(table_hypotheses(H))
    report = verdict_report(H)
    with open(os.path.join(TABLES, "hypotheses.txt"), "w") as f:
        f.write(report)

    # figures
    fig_heatmaps(tour)
    fig_margin_boxplots(tour)
    fig_cooldown_metrics(tour)

    print("\n" + report)
    print(f"Tables  -> {TABLES}")
    print(f"Figures -> {FIGURES}")


if __name__ == "__main__":
    main()
