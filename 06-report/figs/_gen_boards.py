#!/usr/bin/env python3
"""Generate TikZ board snippets for fig_board.tex.

Panel (b) -- a balanced midgame with the legal moves of the side to move, pulled
from a fixed-seed engine playout so every highlighted move is genuinely legal.
Panel (c) -- a real final position replayed from the author's human-vs-computer
games (game_logs/person1.json), so the end state is authentic.

Run from 06-report/figs/:  python3 _gen_boards.py
Prints the two TikZ bodies; paste into fig_board.tex.
"""
import sys, os, json, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "01-game"))
import engine as E

N = E.N
LOGS = os.path.join(os.path.dirname(__file__), "..", "..", "game_logs")
GLY = {E.BLACK: r"\othB", E.WHITE: r"\othW"}
ENDGAME_ID = "ofdusbbd"          # a close human(black)-vs-UCT-PB-cooldown game, final 17:19


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


def replay_endgame(game_id):
    """Replay a recorded cooldown game to its terminal state (real human-vs-computer data)."""
    games = {g["id"]: g for g in json.load(open(os.path.join(LOGS, "person1.json")))}
    g = games[game_id]
    st = E.initial_state()
    for m in g["moves"]:
        mv = E.PASS if m["move"] in (-1, None) else m["move"]
        st = E.apply_move(st, mv, "cooldown")
    return g, st


seed_m, st_m, moves_m = find_midgame()
g_e, st_e = replay_endgame(ENDGAME_ID)
b_e, w_e = E.counts(st_e)
b_m, w_m = E.counts(st_m)

print(f"% MIDGAME seed={seed_m} to_move={'B' if st_m.to_move==E.BLACK else 'W'} "
      f"B={b_m} W={w_m} legal={len(moves_m)}")
print("\n".join(discs(st_m)))
print("% legalne ruchy strony na ruchu (czarny):")
for s in moves_m:
    x, y = xy(s)
    print(f"\\othmove{{{x}}}{{{y}}}")

print()
print(f"% ENDGAME (real) id={g_e['id']} opp={g_e['opponent']} B={b_e} W={w_e} "
      f"winner={'B' if E.winner(st_e)==E.BLACK else ('W' if E.winner(st_e)==E.WHITE else '=')}")
print("\n".join(discs(st_e)))
