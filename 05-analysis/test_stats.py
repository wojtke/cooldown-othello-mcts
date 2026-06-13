#!/usr/bin/env python
"""
Known-value tests for the analysis statistics primitives (analyze.py).
Run with the venv: ../.venv/bin/python test_stats.py  (or pytest).
"""

from __future__ import annotations

import math

from analyze import binom_p, holm_bonferroni, mcnemar_p, wilson_ci


def approx(a, b, tol=1e-3):
    return abs(a - b) <= tol


def test_wilson_symmetric_half():
    rate, lo, hi = wilson_ci(50, 100)
    assert rate == 0.5
    # textbook Wilson 95% interval for 50/100 is [0.404, 0.596]
    assert approx(lo, 0.4038, 2e-3), lo
    assert approx(hi, 0.5962, 2e-3), hi


def test_wilson_zero_and_full():
    r0, lo0, hi0 = wilson_ci(0, 10)
    assert r0 == 0.0 and lo0 == 0.0 and hi0 > 0.0
    r1, lo1, hi1 = wilson_ci(10, 10)
    assert r1 == 1.0 and hi1 == 1.0 and lo1 < 1.0


def test_wilson_empty():
    assert wilson_ci(0, 0) == (0.0, 0.0, 0.0)


def test_mcnemar_known():
    assert mcnemar_p(5, 5) == 1.0                 # perfectly concordant counts -> 1
    # b=10, c=0 -> 2 * 0.5^10
    assert approx(mcnemar_p(10, 0), 2 * 0.5 ** 10, 1e-6)
    assert mcnemar_p(0, 0) == 1.0


def test_holm_known():
    adj = holm_bonferroni({"a": 0.01, "b": 0.02, "c": 0.04})
    # sorted ascending: a*3=0.03, b*2=0.04, c*1=0.04 (monotone non-decreasing)
    assert approx(adj["a"], 0.03)
    assert approx(adj["b"], 0.04)
    assert approx(adj["c"], 0.04)
    # already-large p stays capped at 1
    adj2 = holm_bonferroni({"x": 0.9, "y": 0.8})
    assert adj2["x"] <= 1.0 and adj2["y"] <= 1.0


def test_holm_monotone():
    adj = holm_bonferroni({"a": 0.04, "b": 0.001, "c": 0.5})
    # values, in ascending raw order, must be non-decreasing after adjustment
    order = sorted(["a", "b", "c"], key=lambda k: {"a": 0.04, "b": 0.001, "c": 0.5}[k])
    seq = [adj[k] for k in order]
    assert all(seq[i] <= seq[i + 1] + 1e-12 for i in range(len(seq) - 1)), seq


def test_binom():
    assert approx(binom_p(50, 100), 1.0, 1e-9)    # exactly chance
    assert binom_p(90, 100) < 1e-10               # extreme -> tiny p
    assert binom_p(0, 0) == 1.0


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
