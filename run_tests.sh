#!/usr/bin/env bash
# Run the whole test suite. Engine/players/metrics are pure-Python (stock python3);
# stats needs the venv. Exits non-zero if any suite fails.
set -euo pipefail
cd "$(dirname "$0")"

PY=python3
VENV=./.venv/bin/python

echo "### 01-game engine"
$PY 01-game/test_engine.py
echo
echo "### 01-game engine (differential vs independent reference)"
$PY 01-game/test_engine_diff.py
echo
echo "### 02-players heuristics"
$PY 02-players/test_heuristics.py
echo
echo "### 02-players"
$PY 02-players/test_players.py
echo
echo "### 04-experiments metrics"
$PY 04-experiments/test_metrics.py
echo
echo "### 05-analysis stats"
if [ -x "$VENV" ]; then
    $VENV 05-analysis/test_stats.py
else
    echo "  (skipped: venv not found at $VENV)"
fi
echo
echo "ALL SUITES PASSED"
