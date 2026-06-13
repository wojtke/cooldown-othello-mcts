#!/usr/bin/env python
"""
Single-game runner + structured record (the unit of work for every experiment).

A game is fully determined by `(variant, black_spec, white_spec, seeds)`, so it
has a stable `game_id` (a hash of those) used for crash-resume dedup. Each record
is one JSON object (one JSONL line). Players are built from plain-dict *specs*, so
tasks are picklable and reconstructable in worker processes.

Per-game cooldown metrics (konspekt sec. 6.5), computed cheaply alongside play:
  * classic games  -> whipsaw_rate: fraction of placements that WOULD be illegal
    under the cooldown rule (how often the rule "would activate"),
  * cooldown games -> cooldown_blocked_rate: fraction of decisions where at least
    one classically-legal placement is blocked by the cooldown rule,
  * both -> piece-lifespan: how many times each square gets flipped in the game.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
import time
from statistics import mean

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-game"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-players"))

import engine as E
from engine import (BLACK, EMPTY, PASS, WHITE, apply_move, initial_state,
                    is_terminal, legal_moves, piece_diff, winner)
from players import (DEFAULT_BUDGET, DEFAULT_C, DEFAULT_LAMBDA_C, DEFAULT_W_H,
                     DEFAULT_W_MOB, PLAYER_HYPERPARAMS, make_player)

_DEFAULTS = {"budget": DEFAULT_BUDGET, "c": DEFAULT_C, "w_mob": DEFAULT_W_MOB,
             "lambda_c": DEFAULT_LAMBDA_C, "w_H": DEFAULT_W_H}
_HAS_BUDGET = {"uct", "uct_pb_naive", "uct_pb_cooldown"}


# ---------------------------------------------------------------------------
# Player specs (canonical, minimal, picklable)
# ---------------------------------------------------------------------------

def normalize_spec(name: str, overrides: dict = None) -> dict:
    """Minimal canonical spec: name + only the hyperparameters this player uses."""
    overrides = overrides or {}
    spec = {"name": name}
    for k in PLAYER_HYPERPARAMS[name]:
        spec[k] = float(overrides.get(k, _DEFAULTS[k]))
    if name in _HAS_BUDGET:
        spec["budget"] = int(overrides.get("budget", _DEFAULTS["budget"]))
    return spec


_BURO_ALGOS = ("naive_buro", "cooldown_buro")


def load_tuned_overrides(name: str, variant: str, tuning_dir: str) -> dict:
    """
    Best params for (player, variant) from 03-tuning, or {} if absent. Buro
    heuristics are tuned once (variant-independent file); MCTS files are
    per-variant. Tolerant: missing file -> {} (caller falls back to defaults).
    """
    if not tuning_dir or name == "random":
        return {}
    fn = f"tune_{name}.json" if name in _BURO_ALGOS else f"tune_{name}_{variant}.json"
    path = os.path.join(tuning_dir, fn)
    if not os.path.exists(path):
        return {}
    return json.load(open(path)).get("best_params", {})


def build_from_spec(spec: dict):
    kwargs = {k: v for k, v in spec.items() if k != "name"}
    return make_player(spec["name"], **kwargs)


def spec_label(spec: dict) -> str:
    """Short filesystem-safe label for a spec (used in shard filenames)."""
    extras = "".join(f"_{k}{spec[k]}" for k in sorted(spec) if k not in ("name",))
    return spec["name"] + extras


# ---------------------------------------------------------------------------
# Game id + seeds
# ---------------------------------------------------------------------------

def game_id(variant: str, black: dict, white: dict, seeds: dict) -> str:
    payload = json.dumps({"variant": variant, "black": black, "white": white,
                          "seeds": seeds}, sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def derive_seeds(game_index: int) -> dict:
    """Seeds keyed only by game index, so the same index pairs across variants/pairs."""
    return {"game": 1_000_000 + game_index,
            "black": 2_000_000 + game_index,
            "white": 3_000_000 + game_index}


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def _placements(board, cool, player):
    return [p for p in range(E.NN) if board[p] == EMPTY and E._flips_for(board, cool, p, player)]


# ---------------------------------------------------------------------------
# Play one game
# ---------------------------------------------------------------------------

def play_game(variant: str, black_spec: dict, white_spec: dict, seeds: dict,
              collect_metrics: bool = True) -> dict:
    import random

    black = build_from_spec(black_spec)
    white = build_from_spec(white_spec)
    rngs = {BLACK: random.Random(seeds["black"]), WHITE: random.Random(seeds["white"])}
    players = {BLACK: black, WHITE: white}

    started = datetime.datetime.now().isoformat(timespec="milliseconds")
    t0 = time.perf_counter()

    s = initial_state()
    move_times = {BLACK: [], WHITE: []}
    n_plies = n_placements = 0

    # metrics accumulators
    flip_counts = {}                 # square -> times flipped
    shadow_cool = frozenset()        # classic: cooldown markers we WOULD have
    whipsaw_moves = whipsaw_decisions = 0
    blocked_states = blocked_decisions = 0

    while not is_terminal(s):
        player = s.to_move
        board = s.board
        tm = time.perf_counter()
        move = players[player].choose(s, variant, rngs[player])
        move_times[player].append(time.perf_counter() - tm)

        if move != PASS:
            n_placements += 1
            actual_flips = E._flips_for(board, s.cool, move, player)
            if collect_metrics:
                for f in actual_flips:
                    flip_counts[f] = flip_counts.get(f, 0) + 1
                if variant == "classic":
                    cooldown_legal = _placements(board, shadow_cool, player)
                    whipsaw_decisions += 1
                    if move not in cooldown_legal:
                        whipsaw_moves += 1
                    classic_flips = actual_flips  # classic: s.cool is empty
                    shadow_cool = frozenset((move, *classic_flips))
                else:  # cooldown
                    classic_legal = _placements(board, frozenset(), player)
                    cooldown_legal = _placements(board, s.cool, player)
                    if classic_legal:
                        blocked_decisions += 1
                        if set(classic_legal) - set(cooldown_legal):
                            blocked_states += 1
        else:
            if collect_metrics and variant == "classic":
                shadow_cool = frozenset()

        s = apply_move(s, move, variant)
        n_plies += 1

    finished = datetime.datetime.now().isoformat(timespec="milliseconds")
    wall = time.perf_counter() - t0

    w = winner(s)
    win_str = "black" if w == BLACK else "white" if w == WHITE else "draw"
    diff = piece_diff(s)

    rec = {
        "game_id": game_id(variant, black_spec, white_spec, seeds),
        "variant": variant,
        "black": black_spec,
        "white": white_spec,
        "seeds": seeds,
        "winner": win_str,
        "result_black": 1.0 if w == BLACK else 0.0 if w == WHITE else 0.5,
        "piece_diff_black": diff,
        "n_plies": n_plies,
        "n_placements": n_placements,
        "move_time_s": {
            "black_mean": round(mean(move_times[BLACK]), 6) if move_times[BLACK] else 0.0,
            "white_mean": round(mean(move_times[WHITE]), 6) if move_times[WHITE] else 0.0,
            "black_max": round(max(move_times[BLACK]), 6) if move_times[BLACK] else 0.0,
            "white_max": round(max(move_times[WHITE]), 6) if move_times[WHITE] else 0.0,
        },
        "started_at": started,
        "finished_at": finished,
        "wall_s": round(wall, 4),
    }

    if collect_metrics:
        lifespans = sorted(flip_counts.values())
        metrics = {
            "lifespan_mean": round(mean(lifespans), 3) if lifespans else 0.0,
            "lifespan_max": max(lifespans) if lifespans else 0,
            "lifespan_total_flips": sum(lifespans),
        }
        if variant == "classic":
            metrics["whipsaw_rate"] = round(whipsaw_moves / whipsaw_decisions, 4) \
                if whipsaw_decisions else 0.0
        else:
            metrics["cooldown_blocked_rate"] = round(blocked_states / blocked_decisions, 4) \
                if blocked_decisions else 0.0
        rec["metrics"] = metrics

    return rec


# ---------------------------------------------------------------------------
# Worker entry point (top-level so it pickles under spawn)
# ---------------------------------------------------------------------------

def play_game_task(task: dict) -> dict:
    """task: {shard, variant, black, white, seeds, collect_metrics}."""
    rec = play_game(task["variant"], task["black"], task["white"], task["seeds"],
                    collect_metrics=task.get("collect_metrics", True))
    return {"shard": task["shard"], "record": rec}
