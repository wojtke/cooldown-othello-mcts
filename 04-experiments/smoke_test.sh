#!/usr/bin/env bash
# Fast correctness gate for the experiment pipeline — tiny budget, few games.
# This is the "small dummy run" deliverable before renting the big machine.
set -euo pipefail
cd "$(dirname "$0")"

echo "=== tournament smoke (3 players, B=60, 4 games/pair, both variants) ==="
python3 run_tournament.py --players random naive_buro uct \
    --budget 60 --games 4 --workers 2 --run-name smoke

echo
echo "=== resume check (re-run: should skip everything) ==="
python3 run_tournament.py --players random naive_buro uct \
    --budget 60 --games 4 --workers 2 --run-name smoke

echo
echo "=== self-play smoke (uct, B=60, 4 games/variant) ==="
python3 run_selfplay.py --player uct --budget 60 --games 4 \
    --workers 2 --run-name smoke_selfplay

echo
echo "=== verify ==="
python3 verify_results.py results/smoke
python3 verify_results.py results/smoke_selfplay
