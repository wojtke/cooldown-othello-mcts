#!/usr/bin/env python
"""
Partial-dependence / slice plots of the tuning objective vs each hyperparameter,
straight from the Optuna trials. These visualise how strongly the win-rate
objective depends on each hyperparameter — flat curves mean the parameter is
under-constrained (the 'c'-saturation story for UCT). Outputs to 05-analysis/figures.
"""
from __future__ import annotations
import glob, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)
HERE = os.path.dirname(__file__)
STORAGE = f"sqlite:///{os.path.join(HERE, 'optuna', 'tuning.db')}"
OUT = os.path.join(HERE, "..", "05-analysis", "figures")
os.makedirs(OUT, exist_ok=True)

PRETTY = {"naive_buro": "Naive-Buro", "cooldown_buro": "Cooldown-Buro", "uct": "UCT",
          "uct_pb_naive": "UCT-PB-naive", "uct_pb_cooldown": "UCT-PB-cooldown"}


def study_names():
    names = []
    for f in sorted(glob.glob(os.path.join(HERE, "results", "*.json"))):
        d = json.load(open(f))
        names.append((f"{d['algo']}_{d['variant']}", d["algo"], d["variant"]))
    return names


def slice_plot(study, title, path):
    """One panel per hyperparameter: objective vs param value (scatter + best)."""
    params = list(study.best_params.keys())
    fig, axes = plt.subplots(1, len(params), figsize=(4.2 * len(params), 3.6), squeeze=False)
    for ax, p in zip(axes[0], params):
        xs = [t.params[p] for t in study.trials if t.value is not None and p in t.params]
        ys = [t.value for t in study.trials if t.value is not None and p in t.params]
        ax.scatter(xs, ys, s=22, alpha=0.7, color="#4a78c2")
        bx = study.best_params[p]
        ax.axvline(bx, color="#d9534f", ls="--", lw=1.2, label=f"best {p}={bx:.2f}")
        ax.set_xlabel(p)
        ax.set_ylabel("mean win rate vs controls")
        ax.set_ylim(0.3, 1.0)
        ax.legend(fontsize=8, loc="lower right")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    made = []
    for name, algo, variant in study_names():
        try:
            study = optuna.load_study(study_name=name, storage=STORAGE)
        except Exception:
            continue
        title = f"{PRETTY.get(algo, algo)} @ {variant} — tuning objective dependence"
        path = os.path.join(OUT, f"tuning_slice_{name}.png")
        slice_plot(study, title, path)
        made.append(os.path.basename(path))

    # combined c-sensitivity panel for UCT (the saturation story)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, variant in zip(axes, ["classic", "cooldown"]):
        try:
            s = optuna.load_study(study_name=f"uct_{variant}", storage=STORAGE)
        except Exception:
            continue
        xs = [t.params["c"] for t in s.trials if t.value is not None]
        ys = [t.value for t in s.trials if t.value is not None]
        ax.scatter(xs, ys, s=24, alpha=0.75, color="#4a78c2")
        ax.axvline(s.best_params["c"], color="#d9534f", ls="--", lw=1.2,
                   label=f"best c={s.best_params['c']:.2f}")
        ax.axvline(np.sqrt(2), color="grey", ls=":", lw=1, label="√2 (literature)")
        ax.set_title(f"UCT @ {variant} 6×6")
        ax.set_xlabel("exploration constant c")
        ax.set_ylim(0.7, 1.0)
        ax.legend(fontsize=8, loc="lower center")
    axes[0].set_ylabel("mean win rate vs controls")
    fig.suptitle("UCT objective is nearly flat in c (win-rate saturates) → c under-constrained", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "tuning_uct_c_sensitivity.png"), dpi=130)
    plt.close(fig)
    made.append("tuning_uct_c_sensitivity.png")

    print("wrote:", ", ".join(made))


if __name__ == "__main__":
    main()
