#!/usr/bin/env python
"""
Tests for the Buro heuristics, especially the cooldown term.

Regression test for the reviewer-found bug: a flip that is shielded along one
axis but re-flippable along another must be PENALIZED (vulnerability dominates),
not rewarded. Runs on stock python3 (no deps).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-game"))

import engine as E
from engine import BLACK, EMPTY, WHITE, State, sq

import heuristics as H
from heuristics import HeurParams, cooldown_term, evaluate_move, positional


def _board(cells: dict):
    b = [EMPTY] * E.NN
    for s, v in cells.items():
        b[s] = v
    return tuple(b)


def test_cooldown_penalizes_reflippable_flip():
    """
    Black plays sq(2,0), flipping the white at sq(2,1). That flip is shielded
    horizontally (own pieces at sq(2,0) and sq(2,2)) but vulnerable vertically:
    white sits above at sq(1,1) with an empty square below at sq(3,1), so once
    cooldown expires White replays at sq(3,1) and re-flips it. Net term = -1.
    """
    board = _board({sq(1, 1): WHITE, sq(2, 1): WHITE, sq(2, 2): BLACK})
    s = State(board=board, to_move=BLACK, cool=frozenset(), passes=0)
    # sanity: the move really flips exactly sq(2,1)
    assert E._flips_for(board, frozenset(), sq(2, 0), BLACK) == [sq(2, 1)]
    assert cooldown_term(s, sq(2, 0)) == -1


def test_cooldown_rewards_safe_flip():
    """Same flip but no vertical threat (sq(1,1) empty) -> permanently safe -> +1."""
    board = _board({sq(2, 1): WHITE, sq(2, 2): BLACK})
    s = State(board=board, to_move=BLACK, cool=frozenset(), passes=0)
    assert E._flips_for(board, frozenset(), sq(2, 0), BLACK) == [sq(2, 1)]
    assert cooldown_term(s, sq(2, 0)) == 1


def test_cooldown_aware_changes_evaluation():
    """Naive vs cooldown-aware evaluation differ by exactly lambda_c * term."""
    board = _board({sq(1, 1): WHITE, sq(2, 1): WHITE, sq(2, 2): BLACK})
    s = State(board=board, to_move=BLACK, cool=frozenset(), passes=0)
    params = HeurParams(w_mob=1.0, lambda_c=3.0)
    naive = evaluate_move(s, sq(2, 0), "cooldown", params, cooldown_aware=False)
    aware = evaluate_move(s, sq(2, 0), "cooldown", params, cooldown_aware=True)
    assert abs((aware - naive) - params.lambda_c * cooldown_term(s, sq(2, 0))) < 1e-9


def test_positional_perspective():
    # a black corner is good for black, bad for white
    board = _board({sq(0, 0): BLACK})
    assert positional(board, BLACK, H.WEIGHTS_6x6) == H.WEIGHTS_6x6[0]
    assert positional(board, WHITE, H.WEIGHTS_6x6) == -H.WEIGHTS_6x6[0]


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
