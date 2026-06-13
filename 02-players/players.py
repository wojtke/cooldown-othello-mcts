#!/usr/bin/env python
"""
Player variants for the tournament (konspekt sec. 6.1) and the factory/registry
that builds them by canonical name.

Every player exposes `choose(state, variant, rng) -> move`. Randomness is always
supplied by the caller's `rng` (a `random.Random`), so a game is fully determined
by its seeds. Heuristic players break ties randomly so that repeated games with
the same opponents but different seeds differ (otherwise deterministic players
would replay one identical game).

The six players:
  random            uniform random legal move
  naive_buro        1-ply negamax, classic Buro eval (cooldown-unaware)
  cooldown_buro     1-ply negamax, cooldown-aware Buro eval
  uct               plain UCT
  uct_pb_naive      UCT + progressive bias, naive Buro as H
  uct_pb_cooldown   UCT + progressive bias, cooldown-aware Buro as H
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-game"))

from engine import PASS, legal_moves

import heuristics as H
from mcts import UCTPlayer

# konspekt defaults (the "_def" configuration)
DEFAULT_BUDGET = 10000
DEFAULT_C = math.sqrt(2)
DEFAULT_W_MOB = 1.0
DEFAULT_LAMBDA_C = 1.0
DEFAULT_W_H = 1.0


class RandomPlayer:
    name = "random"

    def choose(self, state, variant, rng):
        moves = legal_moves(state, variant)
        return moves[rng.randrange(len(moves))]


class BuroPlayer:
    """1-ply negamax over the Buro evaluation; random tie-break."""

    def __init__(self, cooldown_aware: bool, params: H.HeurParams = None, name: str = None):
        self.cooldown_aware = cooldown_aware
        self.params = params or H.HeurParams()
        self.name = name or ("cooldown_buro" if cooldown_aware else "naive_buro")

    def choose(self, state, variant, rng):
        moves = legal_moves(state, variant)
        if len(moves) == 1:
            return moves[0]                       # forced move / PASS
        scored = [(H.evaluate_move(state, m, variant, self.params, self.cooldown_aware), m)
                  for m in moves]
        best = max(s for s, _ in scored)
        top = [m for s, m in scored if s >= best - 1e-9]
        return top[rng.randrange(len(top))]


# ---------------------------------------------------------------------------
# Registry / factory
# ---------------------------------------------------------------------------

def make_player(name: str, *, budget: int = DEFAULT_BUDGET, c: float = DEFAULT_C,
                w_mob: float = DEFAULT_W_MOB, lambda_c: float = DEFAULT_LAMBDA_C,
                w_H: float = DEFAULT_W_H):
    """Build a player by canonical name with optional hyperparameter overrides."""
    hp = H.HeurParams(w_mob=w_mob, lambda_c=lambda_c)

    if name == "random":
        return RandomPlayer()
    if name == "naive_buro":
        return BuroPlayer(cooldown_aware=False, params=hp)
    if name == "cooldown_buro":
        return BuroPlayer(cooldown_aware=True, params=hp)
    if name == "uct":
        return UCTPlayer(budget=budget, c=c, heuristic_aware=None, name="uct")
    if name == "uct_pb_naive":
        return UCTPlayer(budget=budget, c=c, w_H=w_H, heuristic_aware=False,
                         heur_params=hp, name="uct_pb_naive")
    if name == "uct_pb_cooldown":
        return UCTPlayer(budget=budget, c=c, w_H=w_H, heuristic_aware=True,
                         heur_params=hp, name="uct_pb_cooldown")
    raise ValueError(f"unknown player: {name}")


# canonical roster (tournament order)
PLAYER_NAMES = (
    "random",
    "naive_buro",
    "cooldown_buro",
    "uct",
    "uct_pb_naive",
    "uct_pb_cooldown",
)

# which hyperparameters each player actually has (drives tuning search spaces)
PLAYER_HYPERPARAMS = {
    "random": (),
    "naive_buro": ("w_mob",),
    "cooldown_buro": ("lambda_c", "w_mob"),
    "uct": ("c",),
    "uct_pb_naive": ("c", "w_H"),
    "uct_pb_cooldown": ("c", "w_H"),
}
