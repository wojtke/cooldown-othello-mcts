#!/usr/bin/env python
"""
Tests for the Othello 6x6 engine (engine.py).

Runnable two ways:
  * `pytest test_engine.py`           (if pytest is installed)
  * `python3 test_engine.py`          (no dependencies; prints a summary)

Covers: opening legality, classic captures, the cooldown whipsaw-protection
edge case (the rule's whole point), pass/termination, and seed determinism.
"""

from __future__ import annotations

import random

import engine as E
from engine import (BLACK, EMPTY, PASS, WHITE, apply_move, counts, initial_state,
                    is_terminal, legal_moves, piece_diff, random_playout, sq, winner)


def test_initial_state():
    s = initial_state()
    assert counts(s) == (2, 2)
    assert s.to_move == BLACK
    assert s.passes == 0
    assert s.cool == frozenset()


def test_opening_moves_both_variants():
    s = initial_state()
    expected = sorted([sq(1, 2), sq(2, 1), sq(3, 4), sq(4, 3)])  # [8, 13, 22, 27]
    assert legal_moves(s, "classic") == expected
    # cooldown markers are empty at the start, so the opening is identical
    assert legal_moves(s, "cooldown") == expected


def test_classic_capture_flips_and_turn():
    s = initial_state()
    s2 = apply_move(s, sq(1, 2), "classic")          # Black plays above the white at (2,2)
    assert s2.board[sq(1, 2)] == BLACK               # placed
    assert s2.board[sq(2, 2)] == BLACK               # flipped white -> black
    assert counts(s2) == (4, 1)
    assert piece_diff(s2) == 3
    assert s2.to_move == WHITE
    assert s2.cool == frozenset()                    # classic never marks


def test_cooldown_marks_placed_and_flipped():
    s = initial_state()
    s2 = apply_move(s, sq(1, 2), "cooldown")
    # markers = placed square + every square flipped this move
    assert s2.cool == frozenset([sq(1, 2), sq(2, 2)])


def test_cooldown_blocks_immediate_reflip():
    """
    The defining case. After Black captures the white at (2,2), that square is
    chilled. White's diagonal reply from (1,1) would re-flip it under classic
    rules, but the line contains ONLY a chilled opponent piece, so it is illegal
    under cooldown (whipsaw is suppressed).
    """
    s = initial_state()
    after_classic = apply_move(s, sq(1, 2), "classic")
    after_cool = apply_move(s, sq(1, 2), "cooldown")

    reply = sq(1, 1)  # White (1,1): diagonal down-right hits (2,2) then own (3,3)
    assert reply in legal_moves(after_classic, "classic")
    assert reply not in legal_moves(after_cool, "cooldown")

    # and under classic the reply really does flip it back (the whipsaw)
    s3 = apply_move(after_classic, reply, "classic")
    assert s3.board[sq(2, 2)] == WHITE


def test_pass_and_termination():
    # Synthetic full board: no empty squares -> both players can only PASS.
    board = [BLACK] * E.NN
    board[0] = WHITE
    s = E.State(board=tuple(board), to_move=BLACK, cool=frozenset(), passes=0)
    assert legal_moves(s, "classic") == [PASS]
    assert not is_terminal(s)
    s = apply_move(s, PASS, "classic")
    assert s.passes == 1 and not is_terminal(s)
    s = apply_move(s, PASS, "classic")
    assert s.passes == 2 and is_terminal(s)
    assert winner(s) == BLACK  # 35 black vs 1 white


def test_pass_clears_cooldown():
    s = initial_state()
    s2 = apply_move(s, sq(1, 2), "cooldown")
    assert s2.cool  # non-empty
    s3 = apply_move(s2, PASS, "cooldown")
    assert s3.cool == frozenset()  # passing never accumulates markers


def _play_seeded(variant: str, seed: int):
    rng = random.Random(seed)
    s = initial_state()
    moves = []
    while not is_terminal(s):
        ms = legal_moves(s, variant)
        m = ms[rng.randrange(len(ms))]
        moves.append(m)
        s = apply_move(s, m, variant)
    return moves, s


def test_playout_terminates_and_is_deterministic():
    for variant in ("classic", "cooldown"):
        m1, s1 = _play_seeded(variant, 12345)
        m2, s2 = _play_seeded(variant, 12345)
        assert m1 == m2 and s1 == s2          # same seed -> identical game
        assert is_terminal(s1)
        b, w = counts(s1)
        assert 0 <= b + w <= E.NN
        # random_playout helper reaches the same terminal as the manual loop
        assert random_playout(initial_state(), variant, random.Random(12345)) == s1


def test_no_illegal_move_accepted():
    s = initial_state()
    # a clearly empty, non-capturing corner is illegal at the opening
    try:
        apply_move(s, sq(0, 0), "classic")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on illegal move")


# ---------------------------------------------------------------------------
# Plain-script runner (no pytest required)
# ---------------------------------------------------------------------------

def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
