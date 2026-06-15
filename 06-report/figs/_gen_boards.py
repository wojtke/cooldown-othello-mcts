#!/usr/bin/env python3
"""Generate TikZ board snippets (midgame w/ legal moves, stuck endgame) for fig_board.tex.

Uses the authoritative engine so every highlighted move is genuinely legal and the
endgame really has no legal placement for either side. Run from 06-report/figs/:
    python3 _gen_boards.py
Prints the two TikZ bodies; paste into fig_board.tex.
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "01-game"))
import engine as E

N = E.N
GLY = {E.BLACK: r"\othB", E.WHITE: r"\othW"}


def xy(s):
    r, c = E.rc(s)
    return c + 0.5, (N - 0.5 - r)


def discs(state):
    out = []
    for s in range(E.NN):
        v = state.board[s]
        if v != E.EMPTY:
            x, y = xy(s)
            out.append(f"{GLY[v]}{{{x}}}{{{y}}}")
    return out


def find_midgame(plies=18, lo=4, hi=6, max_diff=3, min_discs=18):
    """First seed whose state after `plies` random classic moves is a balanced midgame
    with lo<=#legal<=hi (so the highlighted moves are few enough to read clearly)."""
    for seed in range(5000):
        rng = random.Random(seed)
        st = E.initial_state()
        ok = True
        for _ in range(plies):
            mv = E.legal_moves(st, "classic")
            if mv == [E.PASS]:
                ok = False
                break
            st = E.apply_move(st, mv[rng.randrange(len(mv))], "classic")
        if not ok:
            continue
        mv = E.legal_moves(st, "classic")
        b, w = E.counts(st)
        if (mv != [E.PASS] and lo <= len(mv) <= hi
                and abs(b - w) <= max_diff and b + w >= min_discs):
            return seed, st, mv
    raise RuntimeError("no midgame found")


def find_stuck_endgame(min_empty=3, max_empty=6):
    """Most-balanced terminal classic game with some empty cells (both sides stuck).

    A terminal state is reached only after two consecutive passes, so at it neither
    player had a legal placement. We prefer empties in [min_empty,max_empty] and,
    among those, the smallest piece gap, so the board reads as a genuine stalemate
    rather than a one-sided wipeout."""
    best = None       # (|B-W|, seed, state) over the empty-range candidates
    fallback = None   # (empty, seed, state) if none fall in range
    for seed in range(5000):
        rng = random.Random(seed)
        st = E.initial_state()
        while not E.is_terminal(st):
            mv = E.legal_moves(st, "classic")
            st = E.apply_move(st, mv[rng.randrange(len(mv))], "classic")
        empty = st.board.count(E.EMPTY)
        b, w = E.counts(st)
        if min_empty <= empty <= max_empty:
            cand = (abs(b - w), seed, st)
            if best is None or cand[0] < best[0]:
                best = cand
        if fallback is None or empty > fallback[0]:
            fallback = (empty, seed, st)
    if best is not None:
        return best[1], best[2]
    return fallback[1], fallback[2]


seed_m, st_m, moves_m = find_midgame()
seed_e, st_e = find_stuck_endgame()
b_e, w_e = E.counts(st_e)
b_m, w_m = E.counts(st_m)

print(f"% MIDGAME seed={seed_m} to_move={'B' if st_m.to_move==E.BLACK else 'W'} "
      f"B={b_m} W={w_m} legal={len(moves_m)}")
print("\n".join(discs(st_m)))
print("% legalne ruchy strony na ruchu (czarny):" if st_m.to_move == E.BLACK
      else "% legalne ruchy strony na ruchu (bialy):")
for s in moves_m:
    x, y = xy(s)
    print(f"\\othmove{{{x}}}{{{y}}}")

print()
print(f"% ENDGAME seed={seed_e} empty={st_e.board.count(E.EMPTY)} B={b_e} W={w_e} "
      f"winner={'B' if E.winner(st_e)==E.BLACK else ('W' if E.winner(st_e)==E.WHITE else '=')}")
print("\n".join(discs(st_e)))
