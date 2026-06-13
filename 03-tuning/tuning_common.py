#!/usr/bin/env python
"""
Shared helpers for the Optuna tuning cascade (konspekt sec. 6.3).

The objective for every algorithm is the mean win rate of a candidate
configuration against a fixed control set of 3 opponents (averaging guards
against over-specialising to one opponent; self-play is avoided because its
~50% equilibrium gives TPE a weak signal). The 60 games per trial are played in
parallel with a process pool — games are independent.

Control tokens (konspekt Table 1):
  ("random",)                      Random
  ("<algo>", "_t")                 a previously-tuned algorithm (loads its JSON)
  ("<algo>", "_def")               default config
  ("uct", "_def", 500)             default UCT at a reduced budget
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04-experiments"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-players"))

from game import derive_seeds, normalize_spec, play_game  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

# Buro heuristics are tuned once (on cooldown) and reused for both variants.
_BURO = ("naive_buro", "cooldown_buro")


def tuned_json_path(algo: str, variant: str) -> str:
    """Where the tuned-params JSON for (algo, variant) lives."""
    if algo in _BURO:
        return os.path.join(RESULTS_DIR, f"tune_{algo}.json")
    return os.path.join(RESULTS_DIR, f"tune_{algo}_{variant}.json")


def load_tuned_params(algo: str, variant: str) -> dict:
    path = tuned_json_path(algo, variant)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"cascade dependency missing: {path} (tune {algo} before this step)")
    return json.load(open(path))["best_params"]


def resolve_control(token: tuple, variant: str, budget: int) -> dict:
    """Turn a control token into a normalized player spec."""
    name = token[0]
    kind = token[1] if len(token) > 1 else None
    if kind == "_t":
        params = dict(load_tuned_params(name, variant))
        if name not in _BURO:
            params.setdefault("budget", budget)
        return normalize_spec(name, params)
    if kind == "_def":
        overrides = {}
        if len(token) > 2:
            overrides["budget"] = token[2]
        elif name not in _BURO:
            overrides["budget"] = budget
        return normalize_spec(name, overrides)
    # bare token, e.g. ("random",)
    overrides = {"budget": budget} if name not in _BURO else {}
    return normalize_spec(name, overrides)


# ---------------------------------------------------------------------------
# Candidate evaluation (parallel games vs the control set)
# ---------------------------------------------------------------------------

def _score_task(task: dict) -> float:
    """Play one game; return the candidate's score (1 win / 0.5 draw / 0 loss)."""
    rec = play_game(task["variant"], task["black"], task["white"], task["seeds"],
                    collect_metrics=False)
    return rec["result_black"] if task["cand_is_black"] else (1.0 - rec["result_black"])


def build_eval_tasks(cand_spec: dict, control_specs: list, variant: str,
                     games_per_control: int, seed_base: int) -> list:
    """One game per (control, game_index); candidate alternates colors."""
    tasks = []
    for ci, ctrl in enumerate(control_specs):
        for g in range(games_per_control):
            seeds = derive_seeds(seed_base + 1000 * ci + g)
            cand_is_black = (g % 2 == 0)
            black, white = (cand_spec, ctrl) if cand_is_black else (ctrl, cand_spec)
            tasks.append({"variant": variant, "black": black, "white": white,
                          "seeds": seeds, "cand_is_black": cand_is_black})
    return tasks


def evaluate(cand_spec: dict, control_specs: list, variant: str,
             games_per_control: int, seed_base: int, pool=None) -> float:
    """Mean candidate win rate over all games vs the control set."""
    tasks = build_eval_tasks(cand_spec, control_specs, variant,
                             games_per_control, seed_base)
    if pool is None:
        scores = [_score_task(t) for t in tasks]
    else:
        scores = list(pool.imap_unordered(_score_task, tasks))
    return sum(scores) / len(scores)
