# 02-players — player variants

Pure-Python, zero deps. Imports the engine from `../01-game`.

## Files
- `heuristics.py` — Buro 6×6 positional weights + mobility + cooldown-aware term;
  `evaluate_move(state, move, variant, params, cooldown_aware)` is the single entry point,
  reused by the negamax players and by progressive bias.
- `mcts.py` — `UCTPlayer`: plain UCB1 MCTS with random-playout simulation; optional progressive
  bias `w_H * H(s,a)/(N+1)` with H = naive or cooldown-aware Buro. Tree nodes store the full
  `(board, cool)` state (path-dependent → no transposition tables).
- `players.py` — `RandomPlayer`, `BuroPlayer`, and `make_player(name, **overrides)`. Roster in
  `PLAYER_NAMES`; per-player tunable hyperparameters in `PLAYER_HYPERPARAMS`.
- `test_players.py` — determinism + Buro/UCT beat Random + all variants run.

## Roster (canonical names)
`random`, `naive_buro`, `cooldown_buro`, `uct`, `uct_pb_naive`, `uct_pb_cooldown`.

## Conventions
- `choose(state, variant, rng) -> move`. All randomness comes from the caller-supplied `rng`, so a
  game is fully determined by its seeds. Heuristic players break ties randomly (so seeded games
  vary).
- Defaults (`_def`): `budget=10000`, `c=√2`, `w_mob=1`, `lambda_c=1`, `w_H=1`. Tuning overrides
  these via `make_player`.

```bash
python3 test_players.py    # ~9s
```
