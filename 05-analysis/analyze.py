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
import glob
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
                    "n_placements": r["n_placements"],
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

def _bare_tabular(body_rows, header, colspec=None) -> str:
    """Just the tabular block (no float, no caption) — for side-by-side minipages."""
    cols = colspec or ("l" + "r" * (len(header) - 1))
    lines = [rf"\begin{{tabular}}{{{cols}}}", r"\toprule",
             " & ".join(header) + r" \\", r"\midrule"]
    lines += [" & ".join(row) + r" \\" for row in body_rows]
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def _tex_table(body_rows, header, caption, label, colspec=None) -> str:
    lines = [r"\begin{table}[H]", r"\centering", r"\small",
             _bare_tabular(body_rows, header, colspec),
             rf"\caption{{{caption}}}", rf"\label{{{label}}}", r"\end{table}"]
    return "\n".join(lines)


def _comma(x, d) -> str:
    """Polish decimal comma, fixed precision."""
    return f"{x:.{d}f}".replace(".", ",")


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


def forced_pass_data(df) -> dict:
    """Forced-pass frequency per variant.

    A PASS is emitted exactly when the side to move has no legal placement
    (engine.legal_moves -> [PASS]); the game loop counts every PASS in n_plies
    but not in n_placements, so n_passes = n_plies - n_placements. Termination
    needs two *consecutive* passes, so every game ends with exactly 2 trailing
    passes (the board-full / mutual-stuck handshake); subtracting them isolates
    the mid-game situations where one side is frozen while play continues.
    """
    out = {}
    for v in sorted(df.variant.unique()):
        sub = df[df.variant == v]
        npass = sub.n_plies - sub.n_placements
        mid = (npass - 2).clip(lower=0)
        n = len(sub)
        ever = int((mid >= 1).sum())
        _, lo, hi = wilson_ci(ever, n)
        out[v] = {
            "n": n,
            "mean_pass": float(npass.mean()),
            "mean_mid": float(mid.mean()),
            "pct_ever": ever / n if n else 0.0,
            "ever_ci": (lo, hi),
            "pass_per_ply": float(npass.sum() / sub.n_plies.sum()) if len(sub) else 0.0,
        }
    return out


def table_forced_pass(df) -> str:
    """Forced-pass frequency, classic vs cooldown."""
    fp = forced_pass_data(df)
    header = ["Wariant", "śr. pasów mid-gry", "\\% partii z $\\geq$1", "pas/półruch"]
    rows = []
    for v in ("classic", "cooldown"):
        if v not in fp:
            continue
        d = fp[v]
        rows.append([v,
                     _comma(d["mean_mid"], 2),
                     _comma(100 * d["pct_ever"], 1),
                     _comma(100 * d["pass_per_ply"], 2)])
    return _tex_table(rows, header,
                      "Wymuszone pasy (brak legalnego ruchu) -- partie środkowe "
                      "(bez końcowych dwóch pasów).",
                      "tab:forced_pass")


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
    header = ["Hipoteza", "Wynik", "kluczowy efekt", "$p$", "holm-$p$"]
    holm = H.get("_holm", {})
    rows = []
    eff = {
        "H1": lambda h: f"WR {_comma(h['cooldown_rate'],2)}/{_comma(h['classic_rate'],2)} (cd/kl)",
        "H2": lambda h: f"+{h['edge_pp']:.0f}~p.p.\\ nad UCT",
        "H3": lambda h: f"+{h['cooldown_edge_pp']:.0f}/+{h['classic_edge_pp']:.0f}~p.p.\\ (cd/kl)",
        "H4": lambda h: (f"biały {_comma(h['classic']['white_rate'],2)}/"
                         f"{_comma(h['cooldown']['white_rate'],2)} (kl/cd)"),
    }
    for key in ("H1", "H2", "H3", "H4"):
        if key not in H:
            continue
        h = H[key]
        p = h.get("p", float("nan"))
        verdict = "potwierdzona" if h.get("supported") else "odrzucona"
        rows.append([key, verdict, eff[key](h),
                     f"{p:.3f}", f"{holm.get(key, float('nan')):.3f}"])
    # fixed-width wrapping column for the effect text so it never overflows
    body = _tex_table(rows, header, "Weryfikacja hipotez (wielkość efektu, "
                      "$p$-wartość testu i~$p$ po korekcie Holma--Bonferroniego).",
                      "tab:hypotheses", colspec="l l p{4.6cm} r r")
    return body


def player_avg_winrate(tour, variant, player):
    """Mean focal win rate of `player` over all its games in `variant`."""
    sub = tour[(tour.variant == variant)
               & ((tour.black == player) | (tour.white == player))]
    scores = [r.result_black if r.black == player else 1.0 - r.result_black
              for _, r in sub.iterrows()]
    n = len(scores)
    return (sum(scores) / n if n else 0.0), n


def ranking_data(tour):
    players = [p for p in PLAYER_ORDER if p in set(tour.black) | set(tour.white)]
    data = {p: {v: player_avg_winrate(tour, v, p)[0] for v in ("classic", "cooldown")}
            for p in players}
    order = sorted(players, key=lambda p: -(data[p]["classic"] + data[p]["cooldown"]) / 2)
    return order, data


def _ranking_rows(tour):
    order, data = ranking_data(tour)
    header = ["Metoda", "klasyk", "cooldown"]
    rows = [[PRETTY[p], _comma(data[p]["classic"], 3), _comma(data[p]["cooldown"], 3)]
            for p in order]
    return rows, header


def table_ranking(tour) -> str:
    rows, header = _ranking_rows(tour)
    return _tex_table(rows, header,
                      "Ranking: średni współczynnik wygranych każdej metody, uśredniony po "
                      "wszystkich jej partiach turniejowych (po obu kolorach i~wszystkich "
                      "przeciwnikach).", "tab:ranking")


def table_ranking_bare(tour) -> str:
    """Just the tabular (3 cols, ordered by mean WR) for a side-by-side minipage."""
    rows, header = _ranking_rows(tour)
    return _bare_tabular(rows, header)


def tuning_influence_data(tuned, untuned):
    """Per-method avg WR with tuned vs default (literature) params, both variants.

    Returns (order, data) where data[p][variant] = (wr_tuned, wr_default).
    `order` follows the tuned ranking (strongest first).
    """
    order, _ = ranking_data(tuned)
    data = {}
    for p in order:
        data[p] = {}
        for v in ("classic", "cooldown"):
            t = player_avg_winrate(tuned, v, p)[0]
            d = player_avg_winrate(untuned, v, p)[0]
            data[p][v] = (t, d)
    return order, data


def table_tuning_influence(tuned, untuned) -> str:
    """How much did tuning move each method's overall win rate vs literature defaults."""
    order, data = tuning_influence_data(tuned, untuned)
    header = ["Metoda", "klasyk: str.", "dom.", "$\\Delta$",
              "cooldown: str.", "dom.", "$\\Delta$"]
    rows = []
    dpp = lambda x: "0" if abs(x) < 0.5 else f"{x:+.0f}"
    for p in order:
        (tc, dc), (tk, dk) = data[p]["classic"], data[p]["cooldown"]
        rows.append([PRETTY[p],
                     _comma(tc, 3), _comma(dc, 3), dpp((tc - dc) * 100),
                     _comma(tk, 3), _comma(dk, 3), dpp((tk - dk) * 100)])
    return _tex_table(rows, header,
                      "Wpływ strojenia na wyniki końcowe: średni współczynnik wygranych każdej "
                      "metody z~parametrami \\emph{strojonymi} (str.) i~\\emph{domyślnymi} "
                      "literaturowymi (dom.: $c{=}\\sqrt2$, wagi${=}1{,}0$), wraz z~różnicą "
                      "$\\Delta$ w~punktach procentowych. Te same pary i~ziarna w~obu turniejach.",
                      "tab:tuning-influence")


_HP_PRETTY = {"naive_buro": "Naive-Buro", "cooldown_buro": "Cooldown-Buro", "uct": "UCT",
              "uct_pb_naive": "UCT-PB-naive", "uct_pb_cooldown": "UCT-PB-cooldown"}
_HP_ORDER = ["naive_buro", "cooldown_buro", "uct", "uct_pb_naive", "uct_pb_cooldown"]


def table_hyperparams() -> str:
    tuning = os.path.join(HERE, "..", "03-tuning", "results")
    items = [json.load(open(f)) for f in glob.glob(os.path.join(tuning, "tune_*.json"))]
    items.sort(key=lambda d: (_HP_ORDER.index(d["algo"]), d["variant"]))
    header = ["Metoda", "Wariant", "$c$", "$w_{\\mathrm{mob}}$", "$\\lambda_c$", "$w_H$",
              "WR (strojenie)"]
    rows = []
    for d in items:
        bp = d["best_params"]
        f = lambda k: f"{bp[k]:.2f}" if k in bp else "--"
        vlabel = "oba*" if d["algo"] in ("naive_buro", "cooldown_buro") else d["variant"]
        rows.append([_HP_PRETTY[d["algo"]], vlabel, f("c"), f("w_mob"), f("lambda_c"),
                     f("w_H"), f"{d['best_value']:.3f}"])
    return _tex_table(rows, header,
                      "Końcowe hiperparametry po strojeniu (Optuna TPE) oraz współczynnik "
                      "wygranych wobec zestawu kontrolnego. *heurystyki strojono raz na "
                      "Cooldown i~reużyto w~obu wariantach gry.", "tab:hyperparams")


def fig_lifespan(tour):
    import numpy as _np
    fig, ax = plt.subplots(figsize=(7, 3.4))
    hi = int(tour.lifespan_max.max())
    bins = _np.arange(0.5, hi + 1.5, 1)
    for variant, color in (("classic", "#4a78c2"), ("cooldown", "#d9534f")):
        sub = tour[tour.variant == variant]
        ax.hist(sub.lifespan_max.values, bins=bins, alpha=0.55, density=True,
                label=variant, color=color)
    ax.set_xlabel("max times any square is flipped in a game")
    ax.set_ylabel("density")
    ax.set_title("Piece 'lifespan' — most-flipped square per game")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "lifespan.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Analyse Cooldown-Othello results")
    ap.add_argument("--tournament", required=True, help="tournament run dir")
    ap.add_argument("--selfplay", default=None, help="self-play run dir (for H4)")
    ap.add_argument("--tournament-untuned", default=None,
                    help="counterfactual tournament run dir (default/literature params)")
    args = ap.parse_args()

    os.makedirs(TABLES, exist_ok=True)
    os.makedirs(FIGURES, exist_ok=True)

    tour = load_run(args.tournament)
    selfp = load_run(args.selfplay) if args.selfplay else None
    untuned = load_run(args.tournament_untuned) if args.tournament_untuned else None
    print(f"Loaded {len(tour)} tournament games"
          + (f", {len(selfp)} self-play games" if selfp is not None else "")
          + (f", {len(untuned)} untuned games" if untuned is not None else ""))

    H = evaluate_hypotheses(tour, selfp)

    # tables
    for variant in sorted(tour.variant.unique()):
        with open(os.path.join(TABLES, f"winrate_{variant}.tex"), "w") as f:
            f.write(table_winrate_matrix(tour, variant))
    with open(os.path.join(TABLES, "cooldown_metrics.tex"), "w") as f:
        f.write(table_cooldown_metrics(tour))
    with open(os.path.join(TABLES, "forced_pass.tex"), "w") as f:
        f.write(table_forced_pass(tour))
    with open(os.path.join(TABLES, "hypotheses.tex"), "w") as f:
        f.write(table_hypotheses(H))
    with open(os.path.join(TABLES, "ranking.tex"), "w") as f:
        f.write(table_ranking(tour))
    with open(os.path.join(TABLES, "ranking_tabular.tex"), "w") as f:
        f.write(table_ranking_bare(tour))
    if untuned is not None:
        with open(os.path.join(TABLES, "tuning_influence.tex"), "w") as f:
            f.write(table_tuning_influence(tour, untuned))
    try:
        with open(os.path.join(TABLES, "hyperparams.tex"), "w") as f:
            f.write(table_hyperparams())
    except Exception as e:
        print(f"  (skipped hyperparams table: {e})")
    report = verdict_report(H)
    with open(os.path.join(TABLES, "hypotheses.txt"), "w") as f:
        f.write(report)

    # figures
    fig_heatmaps(tour)
    fig_margin_boxplots(tour)
    fig_cooldown_metrics(tour)
    fig_lifespan(tour)

    # ranking numbers (handy for embedding a pgfplots bar chart)
    order, data = ranking_data(tour)
    print("\nRANKING (avg win rate over all tournament games):")
    print(f"  {'method':16s} {'classic':>8s} {'cooldown':>8s}")
    for p in order:
        print(f"  {p:16s} {data[p]['classic']:8.3f} {data[p]['cooldown']:8.3f}")

    # cooldown-activity numbers for the §7.3 inline sentence
    wr = tour[(tour.variant == "classic")].whipsaw_rate.dropna()
    br = tour[(tour.variant == "cooldown")].cooldown_blocked_rate.dropna()
    if len(wr):
        print(f"\nWHIPSAW (classic): median={wr.median():.3f} mean={wr.mean():.3f}")
    if len(br):
        print(f"BLOCKED (cooldown): median={br.median():.3f} mean={br.mean():.3f}")

    # forced-pass frequency for the §7.3 finding (tournament + self-play check)
    for label, df in (("TOURNAMENT", tour), ("SELF-PLAY", selfp)):
        if df is None:
            continue
        fp = forced_pass_data(df)
        print(f"\nFORCED PASS ({label}):")
        for v in ("classic", "cooldown"):
            if v not in fp:
                continue
            d = fp[v]
            lo, hi = d["ever_ci"]
            print(f"  {v:8s} n={d['n']:5d}  mean_mid={d['mean_mid']:.3f}  "
                  f"%games>=1={100*d['pct_ever']:.1f} (CI {100*lo:.1f}-{100*hi:.1f})  "
                  f"pass/ply={100*d['pass_per_ply']:.2f}%  mean_total={d['mean_pass']:.3f}")

    # tuning-influence summary for the §7.4 text
    if untuned is not None:
        order, data = tuning_influence_data(tour, untuned)
        deltas = []
        print("\nTUNING INFLUENCE (avg WR tuned vs default, p.p.):")
        for p in order:
            for v in ("classic", "cooldown"):
                t, d = data[p][v]
                dpp = (t - d) * 100
                deltas.append(abs(dpp))
                print(f"  {p:16s} {v:8s} tuned={t:.3f} default={d:.3f}  d={dpp:+.1f}pp")
        print(f"  mean|Δ|={np.mean(deltas):.1f}pp  max|Δ|={np.max(deltas):.1f}pp")

    print("\n" + report)
    print(f"Tables  -> {TABLES}")
    print(f"Figures -> {FIGURES}")


if __name__ == "__main__":
    main()
