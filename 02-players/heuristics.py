#!/usr/bin/env python
"""
Domain heuristics for Othello 6x6 (Buro positional weights + mobility, and the
cooldown-aware extension), per konspekt sec. 4.

Both heuristics score a *move* `a` from a state `s` (from the mover's point of
view). They are used two ways:
  * directly, by the 1-ply negamax heuristic players (pick argmax over moves), and
  * indirectly, as the signal H(s, a) for progressive bias in the MCTS players.

`evaluate_move` is the single entry point.

The cooldown term is the konspekt's qualitative description made concrete (the
exact form is not pinned down by the spec; its weight lambda_c is tuned):
  * -1 (penalty) per flipped piece that is vulnerable — has an opponent piece on
    one side and an empty square on the opposite side along some axis, so once the
    cooldown marker expires the opponent can re-flip it;
  * +1 (bonus) per flipped piece that is NOT re-flippable and is shielded by own
    pieces along an axis (permanently safe).
Vulnerability takes precedence: a flip re-flippable on any axis is penalized even
if shielded on another axis — it is not permanently safe.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-game"))

import engine as E
from engine import BLACK, EMPTY, NN, PASS, WHITE, apply_move, opponent, rc

_WALL = 3  # off-board sentinel (distinct from EMPTY/BLACK/WHITE)

# 6x6 Buro-style positional weights: corners very valuable, X-squares (diagonal
# to a corner) and C-squares (orthogonally adjacent to a corner) deficit, edges
# mild positive, interior mildly negative. Scaled from the classic 8x8 table.
WEIGHTS_6x6 = (
    100, -20,  10,  10, -20, 100,
    -20, -50,  -2,  -2, -50, -20,
     10,  -2,  -1,  -1,  -2,  10,
     10,  -2,  -1,  -1,  -2,  10,
    -20, -50,  -2,  -2, -50, -20,
    100, -20,  10,  10, -20, 100,
)

# four line-axes as pairs of opposite (dr, dc) directions
_AXES = (
    ((-1, 0), (1, 0)),
    ((0, -1), (0, 1)),
    ((-1, -1), (1, 1)),
    ((-1, 1), (1, -1)),
)


@dataclass
class HeurParams:
    w_mob: float = 1.0           # mobility weight
    lambda_c: float = 1.0        # cooldown-term weight (Cooldown-Buro only)
    weights: tuple = field(default=WEIGHTS_6x6)


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

def positional(board: tuple, player: int, weights: tuple) -> float:
    """Weighted piece-square value from `player`'s perspective."""
    opp = opponent(player)
    s = 0.0
    for i, c in enumerate(board):
        if c == player:
            s += weights[i]
        elif c == opp:
            s -= weights[i]
    return s


def _placements(board: tuple, cool: frozenset, player: int) -> int:
    """Number of legal placements for `player` on this board (turn-agnostic)."""
    n = 0
    for p in range(NN):
        if board[p] == EMPTY and E._flips_for(board, cool, p, player):
            n += 1
    return n


def mobility(board: tuple, cool: frozenset, player: int) -> int:
    """Legal-move difference: player's placements minus opponent's."""
    return _placements(board, cool, player) - _placements(board, cool, opponent(player))


def _cell(board: tuple, r: int, c: int) -> int:
    if 0 <= r < E.N and 0 <= c < E.N:
        return board[E.sq(r, c)]
    return _WALL


def cooldown_term(state, move: int) -> int:
    """
    Net cooldown value of `move`: (safe flips) minus (re-flippable flips).

    For each flipped piece we look along all four axes:
      * vulnerable -> the opponent has a piece on one immediate side and an empty
        square on the opposite side, so once the cooldown marker expires it can
        re-flip this piece next turn (a losing trade);
      * protected  -> own pieces flank it (no axis offers a re-flip).
    Vulnerability TAKES PRECEDENCE over local shielding: a flip that can be
    re-flipped on *any* axis is penalized even if it happens to be shielded on
    another axis (it is not permanently safe). Penalty +1 / bonus +1; the term is
    bonus - penalty, weighted by lambda_c in evaluate_move.
    """
    player = state.to_move
    opp = opponent(player)
    flips = E._flips_for(state.board, state.cool, move, player)
    if not flips:
        return 0
    cb = list(state.board)
    cb[move] = player
    for i in flips:
        cb[i] = player

    bonus = penalty = 0
    for f in flips:
        r, c = rc(f)
        protected = vulnerable = False
        for (d1, d2) in _AXES:
            n1 = _cell(cb, r + d1[0], c + d1[1])
            n2 = _cell(cb, r + d2[0], c + d2[1])
            if n1 == player and n2 == player:
                protected = True
            if (n1 == opp and n2 == EMPTY) or (n2 == opp and n1 == EMPTY):
                vulnerable = True
        if vulnerable:               # re-flippable -> penalize regardless of shielding
            penalty += 1
        elif protected:
            bonus += 1
    return bonus - penalty


# ---------------------------------------------------------------------------
# Combined move evaluation (the public entry point)
# ---------------------------------------------------------------------------

def evaluate_move(state, move: int, variant: str, params: HeurParams,
                  cooldown_aware: bool) -> float:
    """
    Value of playing `move` from `state`, from the mover's perspective. Higher is
    better. PASS (only ever the forced move) evaluates to 0.0.
    """
    if move == PASS:
        return 0.0
    player = state.to_move
    child = apply_move(state, move, variant)
    score = positional(child.board, player, params.weights)
    score += params.w_mob * mobility(child.board, child.cool, player)
    if cooldown_aware:
        score += params.lambda_c * cooldown_term(state, move)
    return score
