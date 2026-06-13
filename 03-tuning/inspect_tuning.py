#!/usr/bin/env python
"""Sanity-check the tuned configs (red-flag checklist) + objective sensitivity."""
from __future__ import annotations
import glob, json, os
import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)
HERE = os.path.dirname(__file__)

# (param -> (low, high)) search bounds per algorithm
BOUNDS = {
    "naive_buro": {"w_mob": (0.0, 5.0)},
    "cooldown_buro": {"lambda_c": (0.1, 4.0), "w_mob": (0.0, 5.0)},
    "uct": {"c": (0.5, 2.5)},
    "uct_pb_naive": {"c": (0.5, 2.5), "w_H": (0.1, 10.0)},
    "uct_pb_cooldown": {"c": (0.5, 2.5), "w_H": (0.1, 10.0)},
}
HAS_RANDOM = {"naive_buro", "cooldown_buro", "uct"}  # controls include Random


def near_bound(v, lo, hi, frac=0.03):
    span = hi - lo
    return v <= lo + frac * span or v >= hi - frac * span


print("=== TUNED CONFIGS ===")
flags = []
for f in sorted(glob.glob(os.path.join(HERE, "results", "*.json"))):
    d = json.load(open(f))
    algo, variant = d["algo"], d["variant"]
    ctrl = ", ".join(
        c["name"] + "".join(" %s=%.2f" % (k, v) for k, v in c.items() if k not in ("name", "budget"))
        for c in d["controls"])
    params = {k: round(v, 3) for k, v in d["best_params"].items()}
    print(f"\n{os.path.basename(f)}")
    print(f"   best_value={d['best_value']:.3f}  params={params}")
    print(f"   controls: {ctrl}")
    # red flags
    for k, v in d["best_params"].items():
        lo, hi = BOUNDS[algo][k]
        if near_bound(v, lo, hi):
            flags.append(f"{algo}/{variant}: {k}={v:.3f} near bound [{lo},{hi}]")
    if algo in HAS_RANDOM and d["best_value"] < 0.5:
        flags.append(f"{algo}/{variant}: best_value {d['best_value']:.3f} < 0.5 despite Random in controls")
    # cascade wiring: any control should carry tuned (non-default) params
    tuned_ctrl = [c["name"] for c in d["controls"]
                  if any(k not in ("name", "budget") for k in c)]

print("\n=== OBJECTIVE SENSITIVITY (flat => param under-constrained) ===")
storage = f"sqlite:///{os.path.join(HERE, 'optuna', 'tuning.db')}"
for f in sorted(glob.glob(os.path.join(HERE, "results", "*.json"))):
    d = json.load(open(f))
    name = f"{d['algo']}_{d['variant']}"
    try:
        s = optuna.load_study(study_name=name, storage=storage)
    except Exception:
        continue
    vals = sorted([t.value for t in s.trials if t.value is not None], reverse=True)
    if not vals:
        continue
    within = sum(1 for v in vals if v >= vals[0] - 0.02)
    print(f"  {name:26s} best={vals[0]:.3f} median={vals[len(vals)//2]:.3f} "
          f"min={vals[-1]:.3f}  within0.02={within}/{len(vals)}")

print("\n=== RED FLAGS ===")
if flags:
    for fl in flags:
        print("  ⚠ " + fl)
else:
    print("  none")
