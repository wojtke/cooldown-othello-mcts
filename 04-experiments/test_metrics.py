#!/usr/bin/env python
"""
Tests for the per-game cooldown metrics in game.py.

Strategy: replay the same deterministic game independently and recompute the
metrics, then assert play_game's reported metrics match. Lifespan is recomputed
by board diffing (independent of the engine's flip function), so a wiring bug in
play_game would show up. Also checks metric ranges and that whipsaw / blocking
actually occur over many random games.

Runs on stock python3 (no deps).
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-game"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-players"))

import engine as E
from engine import BLACK, PASS, WHITE, apply_move, initial_state, is_terminal, legal_moves
from players import make_player

from game import derive_seeds, normalize_spec, play_game


def reference_metrics(variant, seeds):
    """Independent replay of a Random-vs-Random game; recompute metrics plainly."""
    black = make_player("random")
    white = make_player("random")
    rngs = {BLACK: random.Random(seeds["black"]), WHITE: random.Random(seeds["white"])}
    players = {BLACK: black, WHITE: white}

    s = initial_state()
    flip_counts = {}
    shadow = frozenset()
    whip = whip_dec = 0
    blocked = blocked_dec = 0

    while not is_terminal(s):
        player = s.to_move
        opp = E.opponent(player)
        board = s.board
        move = players[player].choose(s, variant, rngs[player])

        if move != PASS:
            if variant == "classic":
                cool_legal = [p for p in range(E.NN)
                              if board[p] == E.EMPTY and E._flips_for(board, shadow, p, player)]
                whip_dec += 1
                if move not in cool_legal:
                    whip += 1
            else:
                classic_legal = [p for p in range(E.NN)
                                 if board[p] == E.EMPTY and E._flips_for(board, frozenset(), p, player)]
                cool_legal = [p for p in range(E.NN)
                              if board[p] == E.EMPTY and E._flips_for(board, s.cool, p, player)]
                if classic_legal:
                    blocked_dec += 1
                    if set(classic_legal) - set(cool_legal):
                        blocked += 1

        nxt = apply_move(s, move, variant)
        if move != PASS:
            # independent flip detection by board diff (opp -> player)
            flipped = [i for i in range(E.NN) if board[i] == opp and nxt.board[i] == player]
            for i in flipped:
                flip_counts[i] = flip_counts.get(i, 0) + 1
            if variant == "classic":
                shadow = frozenset([move, *flipped])
        elif variant == "classic":
            shadow = frozenset()
        s = nxt

    lifespans = sorted(flip_counts.values())
    m = {"lifespan_mean": round(sum(lifespans) / len(lifespans), 3) if lifespans else 0.0,
         "lifespan_max": max(lifespans) if lifespans else 0,
         "lifespan_total_flips": sum(lifespans)}
    if variant == "classic":
        m["whipsaw_rate"] = round(whip / whip_dec, 4) if whip_dec else 0.0
    else:
        m["cooldown_blocked_rate"] = round(blocked / blocked_dec, 4) if blocked_dec else 0.0
    return m


def test_metrics_match_independent_replay():
    spec = normalize_spec("random")
    for variant in ("classic", "cooldown"):
        for gi in range(8):
            seeds = derive_seeds(gi)
            rec = play_game(variant, spec, spec, seeds, collect_metrics=True)
            ref = reference_metrics(variant, seeds)
            assert rec["metrics"] == ref, (
                f"{variant} game {gi}\n play_game: {rec['metrics']}\n reference: {ref}")


def test_metric_ranges_and_prevalence():
    spec = normalize_spec("random")
    whip_rates, blocked_rates = [], []
    for gi in range(40):
        rc = play_game("classic", spec, spec, derive_seeds(gi))["metrics"]
        cd = play_game("cooldown", spec, spec, derive_seeds(gi))["metrics"]
        assert 0.0 <= rc["whipsaw_rate"] <= 1.0
        assert 0.0 <= cd["cooldown_blocked_rate"] <= 1.0
        assert rc["lifespan_max"] >= 1 and cd["lifespan_max"] >= 1
        whip_rates.append(rc["whipsaw_rate"])
        blocked_rates.append(cd["cooldown_blocked_rate"])
    # whipsaw and cooldown-blocking really do happen in random play
    assert sum(whip_rates) / len(whip_rates) > 0.0
    assert sum(blocked_rates) / len(blocked_rates) > 0.0


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
