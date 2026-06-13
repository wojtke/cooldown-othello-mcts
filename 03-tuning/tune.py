#!/usr/bin/env python
"""
Tune one algorithm with Optuna TPE against a fixed control set.

Search spaces (konspekt sec. 6.3 / Table 1):
  naive_buro       w_mob   in [0, 5]        (linear)
  cooldown_buro    lambda_c in [0.1, 4], w_mob in [0, 5]   (linear)
  uct              c       in [0.5, 2.5]    (linear)
  uct_pb_naive     c in [0.5, 2.5], w_H in [0.1, 10]       (w_H log)
  uct_pb_cooldown  c in [0.5, 2.5], w_H in [0.1, 10]       (w_H log)

Resumable: the study lives in a persistent SQLite DB (`results/optuna/tuning.db`)
keyed by `<algo>_<variant>`; re-running tops up to `--trials` completed trials.
Within a trial the games run on a process pool.

Usage (standalone; normally driven by tune_cascade.py):
  python3 tune.py --algo uct --variant cooldown --budget 2000 --trials 30 \
      --games-per-control 20 --workers 8 \
      --controls random naive_buro:_t cooldown_buro:_t
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))

from tuning_common import RESULTS_DIR, evaluate, resolve_control, tuned_json_path

import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)

_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "optuna")


def _sample(trial, algo: str) -> dict:
    if algo == "naive_buro":
        return {"w_mob": trial.suggest_float("w_mob", 0.0, 5.0)}
    if algo == "cooldown_buro":
        return {"lambda_c": trial.suggest_float("lambda_c", 0.1, 4.0),
                "w_mob": trial.suggest_float("w_mob", 0.0, 5.0)}
    if algo == "uct":
        return {"c": trial.suggest_float("c", 0.5, 2.5)}
    if algo in ("uct_pb_naive", "uct_pb_cooldown"):
        return {"c": trial.suggest_float("c", 0.5, 2.5),
                "w_H": trial.suggest_float("w_H", 0.1, 10.0, log=True)}
    raise ValueError(f"no search space for {algo}")


SEARCH_SPACE_DOC = {
    "naive_buro": {"w_mob": "[0,5] linear"},
    "cooldown_buro": {"lambda_c": "[0.1,4] linear", "w_mob": "[0,5] linear"},
    "uct": {"c": "[0.5,2.5] linear"},
    "uct_pb_naive": {"c": "[0.5,2.5] linear", "w_H": "[0.1,10] log"},
    "uct_pb_cooldown": {"c": "[0.5,2.5] linear", "w_H": "[0.1,10] log"},
}


def tune_algorithm(algo: str, variant: str, control_tokens: list, budget: int,
                   trials: int, games_per_control: int, workers: int,
                   seed_base: int = 0) -> dict:
    from game import normalize_spec

    controls = [resolve_control(t, variant, budget) for t in control_tokens]
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    storage = f"sqlite:///{os.path.join(_STORAGE_DIR, 'tuning.db')}"
    study_name = f"{algo}_{variant}"

    study = optuna.create_study(
        study_name=study_name, storage=storage, load_if_exists=True,
        direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))

    pool = Pool(workers) if workers > 1 else None

    def objective(trial):
        params = _sample(trial, algo)
        cand = normalize_spec(algo, {**params, "budget": budget})
        return evaluate(cand, controls, variant, games_per_control, seed_base, pool)

    done = len([t for t in study.trials
                if t.state == optuna.trial.TrialState.COMPLETE])
    remaining = max(0, trials - done)
    print(f"[{algo} @ {variant}] controls={[c['name'] for c in controls]} "
          f"budget={budget} trials={trials} (done={done}, running {remaining}) "
          f"games/control={games_per_control} workers={workers}")
    if remaining:
        study.optimize(objective, n_trials=remaining, show_progress_bar=True)
    if pool is not None:
        pool.close()
        pool.join()

    result = {
        "algo": algo,
        "variant": variant,
        "best_value": study.best_value,
        "best_params": study.best_params,
        "controls": [c for c in controls],
        "budget": budget,
        "trials": trials,
        "games_per_control": games_per_control,
        "seed_base": seed_base,
        "search_space": SEARCH_SPACE_DOC[algo],
        "sampler": "TPESampler(seed=42)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out_path = tuned_json_path(algo, variant)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  best={study.best_value:.3f}  params={study.best_params}  -> {out_path}")
    return result


def _parse_control(tok: str) -> tuple:
    # "random" | "naive_buro:_t" | "uct:_def:500"
    parts = tok.split(":")
    if len(parts) == 1:
        return (parts[0],)
    if len(parts) == 3:
        return (parts[0], parts[1], int(parts[2]))
    return (parts[0], parts[1])


def main():
    ap = argparse.ArgumentParser(description="Tune one algorithm with Optuna TPE")
    ap.add_argument("--algo", required=True)
    ap.add_argument("--variant", choices=["classic", "cooldown"], required=True)
    ap.add_argument("--controls", nargs="+", required=True,
                    help="control tokens, e.g. random naive_buro:_t uct:_def:500")
    ap.add_argument("--budget", type=int, default=2000)
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--games-per-control", type=int, default=20)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--seed-base", type=int, default=0)
    args = ap.parse_args()

    tune_algorithm(args.algo, args.variant, [_parse_control(t) for t in args.controls],
                   args.budget, args.trials, args.games_per_control, args.workers,
                   args.seed_base)


if __name__ == "__main__":
    main()
