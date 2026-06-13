# 01-game — Othello 6×6 engine (classic + cooldown)

Pure-Python, zero dependencies. The authoritative game rules for the whole project.

## Files
- `engine.py` — the engine. Immutable, hashable `State(board, to_move, cool, passes)`;
  `legal_moves`, `apply_move`, `is_terminal`, `winner`, `piece_diff`, `random_playout`,
  `render`. One cooldown-aware capture walk (`_flips_for`) serves both variants — `"classic"`
  keeps the `cool` set empty, which makes the walk reduce to standard Othello.
- `test_engine.py` — engine tests (incl. the cooldown whipsaw-protection case).
- `stats.py` — random-self-play statistics (length/branching verification) and golden-vector dump.
- `golden.json` — seeded reference games (move-lists + final boards) for cross-checking a second
  engine (the TS web rules).

## Use
```bash
python3 test_engine.py                       # run tests (no pytest needed)
python3 stats.py --games 1000 --golden golden.json
```

## Conventions
- Squares are flat indices `0..35`, `sq(r, c) = r*6 + c`. `PASS = -1`.
- Cells: `EMPTY=0, BLACK=1, WHITE=2`. Black moves first.
- A player with no legal placement must PASS; two consecutive passes end the game.
- `variant` is `"classic"` or `"cooldown"` and is threaded through every call (no global state).

Other phases import these modules by adding this directory to `sys.path` (the numbered-dir
convention from `p1_cvrp`).
