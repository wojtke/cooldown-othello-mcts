#!/usr/bin/env python
"""
MCTS / UCT for Othello 6x6, with optional progressive bias (konspekt sec. 2).

Plain UCB1 selection, random-playout simulation, written from scratch. The tree
is built by expanding children from a path, and every node stores its own
`State` — crucially the FULL (board, cool) state, because the cooldown rule makes
the game path-dependent, so two identical boards reached by different histories
are NOT interchangeable and transposition tables would be unsafe.

Progressive bias adds  w_H * H(s,a) / (N(s,a) + 1)  to the selection score, where
H is a domain heuristic (Naive- or Cooldown-Buro). H values are min-max
normalised across a node's children so the bias is on the same ~[0,1] scale as
the win-rate term and decays as visit counts grow.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-game"))

import engine as E
from engine import apply_move, is_terminal, legal_moves, random_playout, result_for

import heuristics as H


class _Node:
    __slots__ = ("state", "parent", "move", "children", "untried", "N", "W", "h")

    def __init__(self, state, parent, move, variant):
        self.state = state
        self.parent = parent
        self.move = move                       # move taken from parent to reach here
        self.children = []                     # list[_Node], fully expanded when untried == []
        self.untried = legal_moves(state, variant)
        self.N = 0
        self.W = 0.0                           # total reward from state.to_move's perspective
        self.h = 0.0                           # heuristic value of `move` (mover@parent view)


class UCTPlayer:
    """
    UCT player. If `heuristic_aware` is None, plain UCT; otherwise progressive
    bias with a Buro heuristic (False = naive Buro, True = cooldown-aware Buro).
    """

    def __init__(self, budget: int = 10000, c: float = math.sqrt(2),
                 w_H: float = 0.0, heuristic_aware=None,
                 heur_params: H.HeurParams = None, name: str = "UCT"):
        self.budget = budget
        self.c = c
        self.w_H = w_H
        self.heuristic_aware = heuristic_aware      # None | False | True
        self.heur_params = heur_params or H.HeurParams()
        self.name = name

    @property
    def use_pb(self) -> bool:
        return self.heuristic_aware is not None and self.w_H > 0.0

    # -- selection score for a child, from the parent's (mover's) perspective --
    def _ucb(self, parent: _Node, child: _Node, hmin: float, hspan: float) -> float:
        exploit = 1.0 - (child.W / child.N)     # child stats are opponent-view -> flip
        explore = self.c * math.sqrt(math.log(parent.N) / child.N)
        score = exploit + explore
        if self.use_pb:
            h_norm = (child.h - hmin) / hspan if hspan > 0 else 0.0
            score += self.w_H * h_norm / (child.N + 1)
        return score

    def _select_child(self, node: _Node) -> _Node:
        if self.use_pb:
            hs = [ch.h for ch in node.children]
            hmin, hmax = min(hs), max(hs)
            hspan = hmax - hmin
        else:
            hmin = hspan = 0.0
        best, best_score = None, -1.0
        for ch in node.children:
            s = self._ucb(node, ch, hmin, hspan)
            if s > best_score:
                best, best_score = ch, s
        return best

    def _expand(self, node: _Node, variant: str, rng) -> _Node:
        i = rng.randrange(len(node.untried))
        move = node.untried.pop(i)
        child = _Node(apply_move(node.state, move, variant), node, move, variant)
        if self.use_pb:
            child.h = H.evaluate_move(node.state, move, variant,
                                      self.heur_params, self.heuristic_aware)
        node.children.append(child)
        return child

    def choose(self, state, variant: str, rng) -> int:
        moves = legal_moves(state, variant)
        if len(moves) == 1:
            return moves[0]                     # forced (single move or PASS)

        root = _Node(state, None, None, variant)
        for _ in range(self.budget):
            node = root
            # selection: descend through fully-expanded, non-terminal nodes
            while not node.untried and node.children and not is_terminal(node.state):
                node = self._select_child(node)
            # expansion
            if node.untried and not is_terminal(node.state):
                node = self._expand(node, variant, rng)
            # simulation
            final = random_playout(node.state, variant, rng)
            # backpropagation
            while node is not None:
                node.N += 1
                node.W += result_for(final, node.state.to_move)
                node = node.parent

        # robust child: most-visited move from the root
        best = max(root.children, key=lambda ch: ch.N)
        return best.move
