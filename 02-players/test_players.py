#!/usr/bin/env python
"""
Sanity tests for the player variants (players.py / mcts.py / heuristics.py).

Runnable with pytest or as `python3 test_players.py`. Budgets are kept tiny so
this finishes in a few seconds on a laptop.
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-game"))

from engine import BLACK, WHITE, apply_move, initial_state, is_terminal, winner

import heuristics as H
from players import PLAYER_NAMES, make_player


def play(black, white, variant, black_seed, white_seed):
    """Play one full game; return the terminal state."""
    s = initial_state()
    rngs = {BLACK: random.Random(black_seed), WHITE: random.Random(white_seed)}
    players = {BLACK: black, WHITE: white}
    while not is_terminal(s):
        p = players[s.to_move]
        m = p.choose(s, variant, rngs[s.to_move])
        s = apply_move(s, m, variant)
    return s


def match(name_a, name_b, variant, n_games, budget=80, base=1000):
    """Play n_games with alternating colors; return a's win count and draws."""
    a = make_player(name_a, budget=budget)
    b = make_player(name_b, budget=budget)
    a_wins = draws = 0
    for g in range(n_games):
        if g % 2 == 0:
            black, white, a_is_black = a, b, True
        else:
            black, white, a_is_black = b, a, False
        s = play(black, white, variant, base + 2 * g, base + 2 * g + 1)
        w = winner(s)
        if w == BLACK and a_is_black or w == WHITE and not a_is_black:
            a_wins += 1
        elif w == 0:
            draws += 1
    return a_wins, draws


def test_all_players_run_both_variants():
    for variant in ("classic", "cooldown"):
        for name in PLAYER_NAMES:
            p = make_player(name, budget=30)
            s = play(p, make_player("random"), variant, 7, 8)
            assert is_terminal(s)


def test_seed_determinism():
    for name in ("random", "naive_buro", "uct", "uct_pb_cooldown"):
        p = make_player(name, budget=40)
        q = make_player("random")
        s1 = play(p, q, "cooldown", 123, 456)
        s2 = play(p, q, "cooldown", 123, 456)
        assert s1 == s2, f"{name} not deterministic under fixed seeds"


def test_naive_buro_beats_random():
    wins, draws = match("naive_buro", "random", "classic", n_games=20)
    assert wins >= 14, f"naive_buro only won {wins}/20 vs random"


def test_cooldown_buro_beats_random_on_cooldown():
    wins, draws = match("cooldown_buro", "random", "cooldown", n_games=20)
    assert wins >= 14, f"cooldown_buro only won {wins}/20 vs random"


def test_uct_beats_random():
    wins, draws = match("uct", "random", "classic", n_games=12, budget=120)
    assert wins >= 8, f"uct only won {wins}/12 vs random"


def test_uct_stronger_with_more_budget():
    """More search should be stronger: UCT@300 beats UCT@15 head-to-head."""
    from mcts import UCTPlayer
    strong = UCTPlayer(budget=300, name="strong")
    weak = UCTPlayer(budget=15, name="weak")
    strong_wins = 0
    n = 10
    for g in range(n):
        if g % 2 == 0:
            s = play(strong, weak, "cooldown", 500 + 2 * g, 500 + 2 * g + 1)
            won = winner(s) == BLACK
        else:
            s = play(weak, strong, "cooldown", 500 + 2 * g, 500 + 2 * g + 1)
            won = winner(s) == WHITE
        strong_wins += int(won)
    assert strong_wins >= 6, f"stronger UCT only won {strong_wins}/{n}"


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
