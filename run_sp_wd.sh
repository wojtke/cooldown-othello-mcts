#!/usr/bin/env bash
# Self-play watchdog: robust to post-migration hangs and network drops (runs on-box).
# Ensures self-play reaches the target, restarting the (resumable) stage if it
# stalls, then runs the final analysis. Idempotent; safe to relaunch.
cd "$(dirname "$0")"
TARGET="${TARGET:-4000}"   # total self-play games (2000 classic + 2000 cooldown)
W="${WORKERS:-128}"

# clear any stuck prior run
pkill -9 -f run_main.sh 2>/dev/null
pkill -9 -f run_selfplay.py 2>/dev/null
pkill -9 -f run_tournament.py 2>/dev/null
sleep 3

last=-1; stall=0
while true; do
  n=$(cat 04-experiments/results/selfplay/*.jsonl 2>/dev/null | wc -l)
  echo "[wd $(date -u +%H:%M:%SZ)] selfplay=$n/$TARGET stall=$stall"
  if [ "$n" -ge "$TARGET" ]; then echo "[wd] SELFPLAY_DONE n=$n"; break; fi

  if ! pgrep -f run_selfplay.py >/dev/null 2>&1; then
    echo "[wd] (re)launching self-play at n=$n"
    pkill -9 python3 2>/dev/null; sleep 2
    nohup python3 04-experiments/run_selfplay.py --player uct_pb_cooldown --variant both \
      --games 2000 --budget 10000 --workers "$W" --run-name selfplay >> logs/sp.log 2>&1 &
    last=$n; stall=0; sleep 90; continue
  fi

  if [ "$n" -le "$last" ]; then stall=$((stall + 1)); else stall=0; fi
  last=$n
  if [ "$stall" -ge 3 ]; then           # ~3 min no progress -> assume hung, restart
    echo "[wd] STALL at n=$n -> killing + restarting"
    pkill -9 python3 2>/dev/null; sleep 2; stall=0
  fi
  sleep 60
done

echo "[wd] running analysis"
.venv/bin/python 05-analysis/analyze.py \
  --tournament 04-experiments/results/tournament \
  --selfplay 04-experiments/results/selfplay >> logs/analyze.log 2>&1
echo "[wd] ALL_DONE_WD $(date -u +%H:%M:%SZ)"
