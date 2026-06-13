# 04-experiments — game runner + tournament / self-play drivers

Imports the engine (`../01-game`) and players (`../02-players`). Multiprocessing across
independent games is the scaling lever; writes are incremental + crash-resumable.

## Files
- `game.py` — `play_game(variant, black_spec, white_spec, seeds)` → one JSONL record with a
  stable `game_id`, winner/piece-diff, per-color move times, and cooldown metrics (whipsaw_rate
  for classic, cooldown_blocked_rate for cooldown, piece-lifespan). Players are built from plain
  `spec` dicts (`normalize_spec`) so tasks are picklable for workers. `play_game_task` is the
  worker entry point.
- `runner.py` — `run_tasks`: process Pool over tasks, incremental sharded JSONL writing
  (`ShardWriter`, flush + periodic fsync), resume by skipping completed `game_id`s
  (`load_done_ids`), and `repair_run_dir` which truncates a dangling partial line left by a hard
  kill (so the next append can't merge/corrupt records).
- `run_tournament.py` — round-robin over selected players × variants, `--games` per pairing with
  alternating colors and game-index-keyed seeds (paired across variants for McNemar). One shard
  per pairing.
- `run_selfplay.py` — H4 self-play of the strongest variant vs itself, distinct color RNG streams.
- `verify_results.py` — schema / duplicate / corrupt-line / count check on a run dir.
- `smoke_test.sh` — tiny end-to-end gate (tournament + resume check + self-play + verify).

## Use
```bash
./smoke_test.sh                                  # dummy run, ~6s
# full run on the rented machine:
python3 run_tournament.py --variant both --games 200 --budget 10000 --workers 32 --run-name tournament
python3 run_selfplay.py --player uct_pb_cooldown --games 2000 --budget 10000 --workers 32 --run-name selfplay
```
Re-running the same command **resumes** (skips finished games). Results land in
`results/<run-name>/<variant>__<pairing>.jsonl`.

## Notes
- macOS uses the `spawn` start method; the worker (`play_game_task`) and tasks (plain dicts) are
  picklable, and driver code is guarded under `__main__`.
- `--budget` only affects MCTS players; heuristics/random ignore it.
