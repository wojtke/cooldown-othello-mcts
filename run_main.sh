#!/usr/bin/env bash
# Self-healing post-tuning run: tournament -> self-play -> analysis.
# Every stage is resumable (game_id skip), so on a transient death we just retry
# and continue. Intended to be launched detached: nohup setsid bash run_main.sh
set -uo pipefail
cd "$(dirname "$0")"
W="${WORKERS:-128}"

for attempt in $(seq 1 8); do
  echo "=== attempt $attempt @ $(date -u +%H:%M:%SZ) (workers=$W) ==="
  if python3 04-experiments/run_tournament.py --variant both --games 200 --budget 10000 --workers "$W" --run-name tournament \
     && python3 04-experiments/run_selfplay.py --player uct_pb_cooldown --variant both --games 2000 --budget 10000 --workers "$W" --run-name selfplay \
     && .venv/bin/python 05-analysis/analyze.py --tournament 04-experiments/results/tournament --selfplay 04-experiments/results/selfplay; then
    echo "=== ALL_DONE @ $(date -u +%H:%M:%SZ) ==="
    exit 0
  fi
  echo "=== stage failed/interrupted, retrying in 15s @ $(date -u +%H:%M:%SZ) ==="
  sleep 15
done
echo "=== GAVE UP after retries @ $(date -u +%H:%M:%SZ) ==="
exit 1
