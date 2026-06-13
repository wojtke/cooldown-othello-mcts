#!/usr/bin/env python
"""
Validate a results run directory: schema, duplicates, corrupt lines, counts.

Usage: python3 verify_results.py results/<run-name>
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

REQUIRED = ("game_id", "variant", "black", "white", "seeds", "winner",
            "result_black", "piece_diff_black", "n_plies", "move_time_s")


def verify(run_dir: str) -> int:
    if not os.path.isdir(run_dir):
        print(f"ERROR: not a directory: {run_dir}", file=sys.stderr)
        return 2

    n_records = n_corrupt = n_bad_schema = 0
    ids = Counter()
    per_variant = Counter()
    per_shard = Counter()

    for fn in sorted(os.listdir(run_dir)):
        if not fn.endswith(".jsonl"):
            continue
        with open(os.path.join(run_dir, fn)) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    n_corrupt += 1
                    continue
                n_records += 1
                missing = [k for k in REQUIRED if k not in rec]
                if missing:
                    n_bad_schema += 1
                    print(f"  bad schema in {fn}: missing {missing}")
                ids[rec.get("game_id")] += 1
                per_variant[rec.get("variant")] += 1
                per_shard[fn] += 1

    dupes = {gid: c for gid, c in ids.items() if c > 1}

    print(f"Run dir   : {run_dir}")
    print(f"Records   : {n_records}")
    print(f"Corrupt   : {n_corrupt} line(s)")
    print(f"Bad schema: {n_bad_schema}")
    print(f"Duplicates: {len(dupes)} game_id(s) appearing >1x")
    print(f"By variant: {dict(per_variant)}")
    print(f"Shards    : {len(per_shard)}")
    for shard, c in sorted(per_shard.items()):
        print(f"    {c:6d}  {shard}")

    ok = (n_bad_schema == 0 and len(dupes) == 0)
    print("\nRESULT:", "OK" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 verify_results.py results/<run-name>", file=sys.stderr)
        sys.exit(2)
    sys.exit(verify(sys.argv[1]))
