# 05-analysis — statistics + figures

Needs the venv (`../.venv`: pandas, scipy, matplotlib). Reads the JSONL from `04-experiments`
and emits report-ready `tables/*.tex` and `figures/*.png`.

## Files
- `analyze.py` — loads run dirs → pandas; statistics primitives (`wilson_ci`, `binom_p`,
  `mcnemar_p`, `holm_bonferroni`); head-to-head win rates; H1–H4 verdicts with effect sizes +
  p-values; figures and LaTeX tables.

## Outputs
- `tables/winrate_<variant>.tex` — row-beats-column win-rate matrices.
- `tables/cooldown_metrics.tex` — whipsaw / blocked / lifespan by variant.
- `tables/hypotheses.tex` + `hypotheses.txt` — H1–H4 verdicts (effect size, p, Holm-adjusted p).
- `figures/heatmap_winrate_<variant>.png`, `margin_boxplots.png`, `cooldown_metrics.png`.

## Use
```bash
../.venv/bin/python analyze.py \
    --tournament ../04-experiments/results/tournament \
    --selfplay   ../04-experiments/results/selfplay
```

## Stats notes
- Win rate counts a draw as 0.5; Wilson 95% CI on (rate, n). "Beats chance" via binomial test.
- McNemar pairs classic-vs-cooldown by **game seed** (`_discordant`). Holm-Bonferroni is applied
  across the primary H1–H4 p-values. Always report effect size with the p-value.
- Operationalizations of H1–H4 follow the konspekt thresholds and are documented in
  `evaluate_hypotheses`; refine wording for the final report once real (B=10000) data is in.
