#!/usr/bin/env python
"""
Othello 6x6 engine — classic and Cooldown variants.

Pure Python, zero dependencies (runs on the stock macOS python3). Readability
first: the board is a flat length-36 tuple of cell values and the cooldown
markers are a frozenset of square indices, so a State is immutable and hashable
(usable as an MCTS tree key). The three hot functions — `legal_moves`,
`apply_move`, `random_playout` — are kept small and self-contained so a faster
(e.g. bitboard) implementation could replace just them later if profiling ever
asks for it. The default is this simple version.

Rules (konspekt sec. 3):
  * Board 6x6, standard central 4-piece start, Black (1) moves first.
  * Classic Othello capture, OR the Cooldown rule, in which pieces placed or
    flipped in the immediately previous turn carry a "cooldown" marker: they are
    transparent to line-closing geometry but cannot be flipped this turn, and
    a line is only legal/capturing if it contains at least one *non-chilled*
    opponent piece. Markers from the previous turn expire when the next move is
    made; the new markers are {placed square} + {squares flipped this move}.
  * A player with no legal placement must PASS. Two consecutive passes end the
    game. The player with more pieces wins.

`variant` is "classic" or "cooldown". The capture walk is identical for both;
the only difference is that "classic" never records cooldown markers (its
`cool` set stays empty), at which point the cooldown-aware walk reduces exactly
to classic Othello.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Board geometry
# ---------------------------------------------------------------------------

N = 6                       # board side
NN = N * N                  # number of squares (36)

EMPTY = 0
BLACK = 1
WHITE = 2

PASS = -1                   # sentinel "move"

VARIANTS = ("classic", "cooldown")

_DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1),
               (0, -1),           (0, 1),
               (1, -1),  (1, 0),  (1, 1)]


def sq(r: int, c: int) -> int:
    """Square index from (row, col)."""
    return r * N + c


def rc(s: int) -> tuple[int, int]:
    """(row, col) from square index."""
    return divmod(s, N)


def _build_rays() -> list[list[list[int]]]:
    """RAYS[square][k] = list of square indices walking direction k to the edge."""
    rays: list[list[list[int]]] = []
    for s in range(NN):
        r, c = rc(s)
        per_square: list[list[int]] = []
        for dr, dc in _DIRECTIONS:
            line: list[int] = []
            rr, cc = r + dr, c + dc
            while 0 <= rr < N and 0 <= cc < N:
                line.append(sq(rr, cc))
                rr += dr
                cc += dc
            per_square.append(line)
        rays.append(per_square)
    return rays


RAYS = _build_rays()        # module-level table, computed once at import


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class State:
    board: tuple            # length-36 tuple of EMPTY/BLACK/WHITE
    to_move: int            # BLACK or WHITE
    cool: frozenset         # squares carrying a cooldown marker (empty in classic)
    passes: int             # number of consecutive passes so far (0, 1 or 2)


def initial_state() -> State:
    """Standard 6x6 Othello opening; Black to move."""
    board = [EMPTY] * NN
    board[sq(2, 2)] = WHITE
    board[sq(2, 3)] = BLACK
    board[sq(3, 2)] = BLACK
    board[sq(3, 3)] = WHITE
    return State(board=tuple(board), to_move=BLACK, cool=frozenset(), passes=0)


def opponent(player: int) -> int:
    return BLACK if player == WHITE else WHITE


# ---------------------------------------------------------------------------
# Capture walk (shared by classic and cooldown)
# ---------------------------------------------------------------------------

def _flips_for(board: tuple, cool: frozenset, p: int, player: int) -> list[int]:
    """
    Squares that placing `player` at empty square `p` would flip.

    Returns [] if the placement is illegal. Cooldown-aware: a ray is only
    accepted if it contains at least one opponent piece NOT in `cool`, and only
    such non-chilled opponent pieces are returned as flips. With `cool` empty
    (classic) this is exactly standard Othello.
    """
    opp = opponent(player)
    flips: list[int] = []
    for ray in RAYS[p]:
        seg: list[int] = []
        saw_free_opp = False
        for idx in ray:
            c = board[idx]
            if c == opp:
                seg.append(idx)
                if idx not in cool:
                    saw_free_opp = True
                continue
            if c == player:
                # line closes on our own piece
                if seg and saw_free_opp:
                    flips.extend(i for i in seg if i not in cool)
                break
            # EMPTY -> this ray cannot close
            break
        # ray that runs off the edge contributes nothing
    return flips


# ---------------------------------------------------------------------------
# Public engine API
# ---------------------------------------------------------------------------

def legal_moves(state: State, variant: str) -> list[int]:
    """
    Legal moves in deterministic (ascending index) order. If the player has no
    legal placement, the only legal move is PASS, returned as [PASS].
    """
    moves = []
    board = state.board
    cool = state.cool
    player = state.to_move
    for p in range(NN):
        if board[p] != EMPTY:
            continue
        if _flips_for(board, cool, p, player):
            moves.append(p)
    return moves if moves else [PASS]


def apply_move(state: State, move: int, variant: str) -> State:
    """Return the successor state after `move` (PASS or a square index)."""
    opp = opponent(state.to_move)

    if move == PASS:
        # Markers expire; nothing placed. Passing never accumulates markers.
        return State(board=state.board, to_move=opp,
                     cool=frozenset(), passes=state.passes + 1)

    flips = _flips_for(state.board, state.cool, move, state.to_move)
    if not flips:
        raise ValueError(f"illegal move {move} for player {state.to_move}")

    new_board = list(state.board)
    new_board[move] = state.to_move
    for i in flips:
        new_board[i] = state.to_move

    if variant == "cooldown":
        new_cool = frozenset((move, *flips))
    else:
        new_cool = frozenset()

    return State(board=tuple(new_board), to_move=opp, cool=new_cool, passes=0)


def is_terminal(state: State) -> bool:
    """Game ends after two consecutive passes."""
    return state.passes >= 2


def counts(state: State) -> tuple[int, int]:
    """(black_count, white_count)."""
    b = state.board.count(BLACK)
    w = state.board.count(WHITE)
    return b, w


def piece_diff(state: State) -> int:
    """Black minus white piece count."""
    b, w = counts(state)
    return b - w


def winner(state: State) -> int:
    """BLACK, WHITE, or EMPTY for a draw (only meaningful at a terminal state)."""
    d = piece_diff(state)
    if d > 0:
        return BLACK
    if d < 0:
        return WHITE
    return EMPTY


def result_for(state: State, player: int) -> float:
    """Game result from `player`'s view: 1.0 win, 0.5 draw, 0.0 loss."""
    w = winner(state)
    if w == EMPTY:
        return 0.5
    return 1.0 if w == player else 0.0


# ---------------------------------------------------------------------------
# Random playout (MCTS simulation step)
# ---------------------------------------------------------------------------

def random_playout(state: State, variant: str, rng: random.Random) -> State:
    """Play uniformly-random legal moves until terminal; return the final state."""
    while not is_terminal(state):
        moves = legal_moves(state, variant)
        move = moves[rng.randrange(len(moves))]
        state = apply_move(state, move, variant)
    return state


# ---------------------------------------------------------------------------
# Pretty-printing (debugging / web / replays)
# ---------------------------------------------------------------------------

_GLYPH = {EMPTY: ".", BLACK: "B", WHITE: "W"}


def render(state: State) -> str:
    """Human-readable board; lowercase marks a cooled square."""
    rows = []
    for r in range(N):
        cells = []
        for c in range(N):
            s = sq(r, c)
            g = _GLYPH[state.board[s]]
            if s in state.cool and g != ".":
                g = g.lower()
            cells.append(g)
        rows.append(" ".join(cells))
    b, w = counts(state)
    header = f"  to_move={_GLYPH[state.to_move]} B={b} W={w} passes={state.passes}"
    return "\n".join(rows) + "\n" + header
