#!/usr/bin/env python
"""
Differential test of the engine against an independent reference.

The reference re-derives legal moves and flips by walking the 8 directions with
explicit (row, col) arithmetic — NOT using the precomputed RAYS table or the
engine's `_flips_for`. Over many positions reached in random self-play (both
variants), the engine and reference must agree on the legal-move set and on the
flips of every legal move. This validates the RAYS precomputation and the
cooldown-aware capture walk from scratch.

Runs on stock python3.
"""

from __future__ import annotations

import random

import engine as E
from engine import (BLACK, EMPTY, PASS, WHITE, apply_move, initial_state,
                    is_terminal, legal_moves)

_DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def ref_flips(board, cool, p, player):
    """Independent flip computation via direct (row, col) ray walking."""
    opp = BLACK if player == WHITE else WHITE
    r0, c0 = divmod(p, E.N)
    flips = []
    for dr, dc in _DIRS:
        r, c = r0 + dr, c0 + dc
        seg = []
        saw_free = False
        while 0 <= r < E.N and 0 <= c < E.N:
            i = r * E.N + c
            v = board[i]
            if v == opp:
                seg.append(i)
                if i not in cool:
                    saw_free = True
                r += dr
                c += dc
                continue
            if v == player:
                if seg and saw_free:
                    flips.extend(j for j in seg if j not in cool)
                break
            break  # EMPTY
    return sorted(flips)


def ref_legal(board, cool, player):
    moves = [p for p in range(E.NN)
             if board[p] == EMPTY and ref_flips(board, cool, p, player)]
    return moves if moves else [PASS]


def test_engine_matches_reference_over_random_play():
    checked_positions = 0
    checked_moves = 0
    for variant in ("classic", "cooldown"):
        rng = random.Random(2024)
        for _ in range(60):                    # 60 random games per variant
            s = initial_state()
            while not is_terminal(s):
                eng_moves = legal_moves(s, variant)
                ref_moves = ref_legal(s.board, s.cool, s.to_move)
                assert eng_moves == ref_moves, (
                    f"{variant} legal-move mismatch\n eng={eng_moves}\n ref={ref_moves}\n"
                    f"{E.render(s)}")
                for m in eng_moves:
                    if m == PASS:
                        continue
                    eng_f = sorted(E._flips_for(s.board, s.cool, m, s.to_move))
                    ref_f = ref_flips(s.board, s.cool, m, s.to_move)
                    assert eng_f == ref_f, (
                        f"{variant} flip mismatch at {m}\n eng={eng_f}\n ref={ref_f}")
                    checked_moves += 1
                checked_positions += 1
                m = eng_moves[rng.randrange(len(eng_moves))]
                s = apply_move(s, m, variant)
    print(f"  checked {checked_positions} positions, {checked_moves} move-flips")


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
