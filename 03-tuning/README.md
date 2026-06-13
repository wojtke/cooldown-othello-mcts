# 03-tuning — Optuna TPE cascade

Needs the venv (`../.venv`, optuna). Tunes each player against a fixed 3-opponent control set,
maximizing mean win rate. Games run on a process pool; studies are resumable.

## Files
- `tuning_common.py` — control-token resolution (`_t` loads a tuned JSON, `_def` uses defaults,
  `uct:_def:500` reduces budget), and parallel candidate evaluation (`evaluate`).
- `tune.py` — `tune_algorithm(...)`: one Optuna study (`TPESampler(seed=42)`, persistent SQLite at
  `optuna/tuning.db`, `load_if_exists`), search spaces per konspekt sec. 6.3. Writes
  `results/tune_<algo>[_<variant>].json`. Also a standalone CLI.
- `tune_cascade.py` — the full ordered cascade (konspekt Table 1): 8 runs = `naive_buro`,
  `cooldown_buro` (cooldown only) + `{uct, uct_pb_naive, uct_pb_cooldown} × {classic, cooldown}`.
  Each algorithm joins the control set of those tuned after it.

## Use
```bash
# dummy (fast)
../.venv/bin/python tune_cascade.py --budget 60 --trials 2 --games-per-control 2 --workers 4
# full (rented machine; konspekt settings: B_tune=2000, 30 trials, 60 games/trial)
../.venv/bin/python tune_cascade.py --budget 2000 --trials 30 --games-per-control 20 --workers 32
```
Re-running **resumes** each study (tops up to `--trials` completed trials). Buro heuristics are
tuned once on cooldown and reused for both variants; MCTS is tuned per variant. The experiment
drivers (`04-experiments`) load these JSONs to configure the tournament players.

## Notes
- `games_per_control` is per opponent; 3 controls → konspekt's 60 games/trial means
  `--games-per-control 20`.
- `best_params` holds only the tuned hyperparameters; the budget used during tuning is `B_tune`,
  separate from the experiment budget `B=10000`.
