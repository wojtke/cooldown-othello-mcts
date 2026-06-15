# Cooldown Othello 6×6 — MCTS / UCT

MCTS/UCT agents for **Othello on a 6×6 board** with an original *cooldown rule* (*reguła stygnięcia*):
a disc that was just placed or flipped is briefly **chilled** and cannot be flipped again on the
opponent's immediate reply. This makes captures path-dependent (the state carries a cool-set), lowers
the branching factor, and protects fresh captures from instant whipsaw.

Coursework project **P2** for PW MSI2 (*Metody Sztucznej Inteligencji 2*). Author: **Wojciech Jasiński**.

- 🎮 **Play it:** https://wojtke.github.io/cooldown-othello-mcts/ — classic + cooldown, hotseat or vs. AI (six levels).
- 📄 **Report (PL, PDF):** [`06-report/report-v2.pdf`](06-report/report-v2.pdf) — full methodology, results, and hypothesis tests.

## What's inside

Six players compete: **Random**, two Buro positional heuristics (`naive` / `cooldown`), and three
MCTS variants (**UCT**, **UCT-PB-naive**, **UCT-PB-cooldown**, the last two with progressive bias).
All are tuned with Optuna (TPE), then run head-to-head on both rule-sets; results are analysed with
Wilson confidence intervals, McNemar's test, and Holm–Bonferroni correction.

**Headline findings:** UCT clearly beats the heuristics, and its edge is *larger* under the cooldown
rule. The strongest player is **UCT-PB-cooldown**, but the gain comes mainly from MCTS itself, not
from progressive bias. The cooldown rule measurably shrinks the branching factor and makes positions
more often tactically blocked (more forced passes). See the report for the full analysis.

## Repository layout

| Path | Contents |
|------|----------|
| `00-konspekt` | Locked research design. |
| `01-game` | Pure-Python rules engine (classic + cooldown), tests, golden vectors. |
| `02-players` | Random, Buro heuristics, UCT and UCT-PB players. |
| `03-tuning` | Optuna TPE hyperparameter cascade (resumable SQLite). |
| `04-experiments` | Tournament + self-play drivers (incremental, crash-resumable JSONL). |
| `05-analysis` | Wilson CI, McNemar, Holm, cooldown metrics; figures + tables. |
| `06-report` | LaTeX report (`report-v2.tex` → `report-v2.pdf`). |
| `07-slides` | Presentation. |
| `web` | Vite + TypeScript playable build (deployed to GitHub Pages). |

## Running

Python phases use a local `.venv` (Optuna, SciPy, pandas, matplotlib); `01-game` / `02-players` are
zero-dependency. Each numbered folder has its own README with exact commands; `STATUS.md` tracks
phase status and the full compute-pipeline runbook. The web app build/deploy steps live in
[`web/README.md`](web/README.md).
