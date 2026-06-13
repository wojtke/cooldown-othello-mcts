#!/usr/bin/env python
"""
Shared experiment infrastructure: incremental + resumable, multiprocessing.

Design goals (so a long rented-machine run survives crashes):
  * never accumulate-in-RAM-then-dump: each finished game is appended as one
    JSONL line and flushed immediately (periodic fsync too);
  * shard output by logical group (one file per pairing) so a corrupt tail is
    isolated and groups can be re-run independently;
  * resume by skipping completed `game_id`s: the full task list is enumerated
    deterministically, existing shards are scanned on startup, and only missing
    games are dispatched — re-running the same command continues, never
    duplicates;
  * truncated trailing lines from a hard kill are detected and skipped on load.
"""

from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))

from game import play_game_task


def repair_run_dir(run_dir: str) -> int:
    """
    Truncate any dangling partial last line in each shard (a hard kill can leave
    a newline-less partial record; appending after it would merge and corrupt the
    next record). Returns the number of shards repaired.
    """
    if not os.path.isdir(run_dir):
        return 0
    repaired = 0
    for fn in sorted(os.listdir(run_dir)):
        if not fn.endswith(".jsonl"):
            continue
        path = os.path.join(run_dir, fn)
        with open(path, "rb+") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                continue
            # find the last newline scanning backwards
            pos, last_nl, chunk = size, -1, 4096
            while pos > 0 and last_nl == -1:
                step = min(chunk, pos)
                pos -= step
                f.seek(pos)
                idx = f.read(step).rfind(b"\n")
                if idx != -1:
                    last_nl = pos + idx
            if last_nl == -1:
                f.truncate(0)                 # whole file is one unterminated line
                repaired += 1
            elif last_nl != size - 1:
                f.truncate(last_nl + 1)       # drop the unterminated tail
                repaired += 1
    return repaired


def load_done_ids(run_dir: str):
    """Set of game_ids already present in the run dir's shards (skips bad lines)."""
    done = set()
    skipped = 0
    if not os.path.isdir(run_dir):
        return done, skipped
    for fn in sorted(os.listdir(run_dir)):
        if not fn.endswith(".jsonl"):
            continue
        path = os.path.join(run_dir, fn)
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1        # truncated/corrupt line (e.g. last line after a kill)
                    continue
                gid = rec.get("game_id")
                if gid:
                    done.add(gid)
    return done, skipped


class ShardWriter:
    """Append-only writer with one file handle per shard, flush + periodic fsync."""

    def __init__(self, run_dir: str, fsync_every: int = 50):
        self.run_dir = run_dir
        self.fsync_every = fsync_every
        self._files = {}
        self._since_sync = 0
        os.makedirs(run_dir, exist_ok=True)

    def write(self, shard: str, record: dict):
        f = self._files.get(shard)
        if f is None:
            f = open(os.path.join(self.run_dir, f"{shard}.jsonl"), "a")
            self._files[shard] = f
        f.write(json.dumps(record) + "\n")
        f.flush()
        self._since_sync += 1
        if self._since_sync >= self.fsync_every:
            for fh in self._files.values():
                os.fsync(fh.fileno())
            self._since_sync = 0

    def close(self):
        for fh in self._files.values():
            os.fsync(fh.fileno())
            fh.close()
        self._files.clear()


def run_tasks(tasks: list, run_dir: str, workers: int = 1, resume: bool = True,
              progress_every: int = 25) -> dict:
    """
    Execute game tasks (each a dict with a 'game_id' and 'shard' key) with a
    process pool, writing results incrementally. Returns a summary dict.
    """
    if resume:
        repaired = repair_run_dir(run_dir)
        if repaired:
            print(f"Repaired  : {repaired} shard(s) with a dangling partial line")
        done, skipped = load_done_ids(run_dir)
    else:
        done, skipped = set(), 0
    todo = [t for t in tasks if t["game_id"] not in done]

    print(f"Run dir   : {run_dir}")
    print(f"Tasks     : {len(tasks)} total, {len(done)} already done"
          + (f" ({skipped} corrupt lines skipped)" if skipped else "")
          + f", {len(todo)} to run")
    print(f"Workers   : {workers}")
    if not todo:
        print("Nothing to do.")
        return {"total": len(tasks), "done_before": len(done), "ran": 0}

    writer = ShardWriter(run_dir)
    ran = 0
    t0 = time.perf_counter()
    try:
        if workers <= 1:
            it = (play_game_task(t) for t in todo)
        else:
            pool = Pool(workers)
            it = pool.imap_unordered(play_game_task, todo)
        for out in it:
            writer.write(out["shard"], out["record"])
            ran += 1
            if ran % progress_every == 0 or ran == len(todo):
                el = time.perf_counter() - t0
                rate = ran / el if el > 0 else 0.0
                eta = (len(todo) - ran) / rate if rate > 0 else 0.0
                print(f"  {ran}/{len(todo)}  {rate:.1f} games/s  elapsed {el:.0f}s  eta {eta:.0f}s")
    finally:
        writer.close()
        if workers > 1:
            pool.close()
            pool.join()

    el = time.perf_counter() - t0
    print(f"Ran {ran} games in {el:.1f}s ({ran/el:.1f} games/s)" if el > 0 else f"Ran {ran} games")
    return {"total": len(tasks), "done_before": len(done), "ran": ran, "wall_s": el}
