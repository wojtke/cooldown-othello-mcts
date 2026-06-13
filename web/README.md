# web — Cooldown Othello 6×6 (playable)

Vite + TypeScript. A standalone, static, decoupled implementation for **playing and getting a feel**
for the game (classic + cooldown), hostable on GitHub Pages. The rules engine (`src/engine.ts`) is a
TypeScript port of `../01-game/engine.py` and is validated to reproduce the Python **golden vectors**
exactly. The in-browser AI (`src/ai.ts`: random / greedy / short-MCTS) is a *toy for feel*, **not**
the tuned research player (that runs in Python; the human-study harness using it is a later phase).

## Develop
```bash
npm install
npm run validate     # TS engine == Python golden.json (rule parity)
npm run dev          # local dev server
npm run build        # -> dist/ (base = /cooldown-othello-mcts/)
```

## Deploy (GitHub Pages)
```bash
npm run build
npx gh-pages -d dist           # pushes to the gh-pages branch
```
Live: https://wojtke.github.io/cooldown-othello-mcts/

## Files
- `src/engine.ts` — rules (classic + cooldown), mirrors the Python authority.
- `src/ai.ts` — light AI (random / Buro-greedy / short UCT).
- `src/main.ts` — board UI, hotseat + vs-AI, legal-move / chilled / cooldown-blocked highlighting.
- `test/validate_golden.ts` — golden-vector parity check vs `../01-game/golden.json`.
