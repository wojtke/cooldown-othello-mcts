#!/usr/bin/env bash
# Full experiment pipeline for the rented machine: tune -> tournament -> self-play
# -> analyze. Every stage is resumable (re-running this script continues where it
# stopped), so it's safe to run inside tmux and reconnect. Logs go to ./logs/.
#
# Usage:
#   WORKERS=128 ./run_all.sh                 # full konspekt settings
#   WORKERS=128 GAMES=200 ./run_all.sh       # override a knob
set -euo pipefail
cd "$(dirname "$0")"

WORKERS="${WORKERS:-$(nproc)}"
PY=python3
VENV=./.venv/bin/python

# konspekt knobs (override via env)
TUNE_BUDGET="${TUNE_BUDGET:-2000}"
TRIALS="${TRIALS:-30}"
GAMES_PER_CONTROL="${GAMES_PER_CONTROL:-20}"
BUDGET="${BUDGET:-10000}"
GAMES="${GAMES:-200}"
SELFPLAY_GAMES="${SELFPLAY_GAMES:-2000}"
STRONGEST="${STRONGEST:-uct_pb_cooldown}"

mkdir -p logs
ts() { date +%Y%m%dT%H%M%S; }
echo "WORKERS=$WORKERS  TUNE_BUDGET=$TUNE_BUDGET  BUDGET=$BUDGET  GAMES=$GAMES  SELFPLAY_GAMES=$SELFPLAY_GAMES"

echo "=== [1/4] tuning cascade ($(ts)) ==="
$VENV 03-tuning/tune_cascade.py --budget "$TUNE_BUDGET" --trials "$TRIALS" \
    --games-per-control "$GAMES_PER_CONTROL" --workers "$WORKERS" 2>&1 | tee -a logs/tune.log

echo "=== [2/4] main tournament ($(ts)) ==="
$PY 04-experiments/run_tournament.py --variant both --games "$GAMES" --budget "$BUDGET" \
    --workers "$WORKERS" --run-name tournament 2>&1 | tee -a logs/tournament.log

echo "=== [3/4] H4 self-play ($(ts)) ==="
$PY 04-experiments/run_selfplay.py --player "$STRONGEST" --variant both \
    --games "$SELFPLAY_GAMES" --budget "$BUDGET" --workers "$WORKERS" \
    --run-name selfplay 2>&1 | tee -a logs/selfplay.log

echo "=== [4/4] analysis ($(ts)) ==="
$VENV 05-analysis/analyze.py \
    --tournament 04-experiments/results/tournament \
    --selfplay 04-experiments/results/selfplay 2>&1 | tee -a logs/analyze.log

echo "=== DONE ($(ts)). Artifacts in 05-analysis/{tables,figures}/ ==="
