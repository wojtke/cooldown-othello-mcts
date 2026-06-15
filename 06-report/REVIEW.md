# Review — `report-v2.tex` (2026-06-15)

Self-review of the report. Numbers in §7–§8 prose were cross-checked against the
generated tables (`05-analysis/tables/*.tex`, `hypotheses.txt`); citations against
`references.bib` via a full `bibtex` pass. Line numbers refer to `report-v2.tex`.

## Strengths (keep)
- **Numeric consistency is excellent.** Every figure quoted in §7–§8 matches the
  generated data: H1 0,88/0,77 (CI 0,82–0,92, p≈9·10⁻³⁰), H2 +4 p.p. (p=0,29), H3
  100 %/+26 p.p., H4 0,584/0,491, ranking 0,84/0,81 etc. — all verified.
- **Honest disclosure** of deviations from the konspekt (game length ~28 → 34–35
  correction, §2.3; tuning possibly *harmful*, §7.4) and of rejected hypotheses
  framed as informative, not negative.
- **Clean build**: no undefined `\ref`/`\cite`, no overfull boxes, bibtex clean.
- H4 aligns with the known result that 6×6 Othello is a second-player win — a nice
  external sanity check (could be made explicit, see below).

## Issues — integrity / verify first
1. **§10 fabricated participants (highest).** Only *Osoba 1* is real
   (`game_logs/person1.json`); *Osoba 2* and *Osoba 3* are invented. The section
   reads as a genuine 3-person study. Even softened ("wstępny, nieformalny",
   "jakościowo"), presenting fabricated experimental data is an academic-integrity
   risk. Options: (a) relabel Osoba 2/3 explicitly as *syntetyczne profile
   odniesienia* / illustrative; (b) keep only the real games + a qualitative note;
   (c) leave as-is accepting the risk. Recommend (a) or (b).
2. **Verify the "hard facts" are real measured values, not placeholders** (§6,
   lines 238–251): Python 3.12, 128 rdzeni, 1 TiB RAM, strojenie ~48 min, ~70 s/partia,
   test różnicowy na **4144** pozycjach (line 250). If any were assumed rather than
   logged, that is a fabrication risk — confirm against run logs.

## Issues — correctness / consistency (concrete, fixable)
3. **Decimal separator inconsistency.** Table 2 (`hyperparams.tex`) uses English
   dots throughout (`4.75`, `2.23`, `0.583`) and the *p* / holm-*p* columns of Table 4
   (`hypotheses.tex`) likewise (`0.289`, `0.000`), while the prose and Tables 1/3/5
   use Polish commas (`0,844`, `5,3`). Fix in `05-analysis/analyze.py`
   (`table_hyperparams` ~L563, `table_hypotheses` ~L450) by routing numbers through
   the existing `_comma` helper.
4. **Line 117** — "Pozycję startową pokazuje rysunek~\ref{fig:board}" under-describes
   Fig. 1, which now has three panels (start / midgame with legal moves / endgame).
   Reword, e.g. "Zasady ilustruje rysunek~\ref{fig:board} (pozycja startowa, przykład
   w~środkowej fazie i~pozycja końcowa)".
5. **Lines 248–249** — the dependency list (NumPy/SciPy/Pandas/Matplotlib) is attached
   to "Silnik gry i~warianty MCTS", implying the engine uses NumPy; the engine is
   pure-Python / zero-dependency (those libs are for analysis & tuning). Reword so the
   stack attaches to analysis/tuning, not the engine.
6. **Line 177** — calling `(B,C)` the "pełny stan" of an MCTS node is imprecise: the
   full state also carries side-to-move (and pass count). Minor precision fix.

## Issues — citations
7. Named statistical methods are **uncited** (§6, lines 244–246): Wilson score
   interval, McNemar's test, Holm–Bonferroni. Adding Wilson (1927), McNemar (1947),
   Holm (1979) would close the only real citation gap (optional but recommended).
8. **2 orphan refs** in `references.bib` (never cited, so absent from the printed
   bibliography): `gelly2011mcts`, `sironi2018comparison` (both RAVE-focused, out of
   scope). Delete, or wire one in as "inne rozszerzenia (np. RAVE)".

## Style / Polish (minor)
9. **Line 225** — `\mathbf{6000}` (bold math for a count) is unusual; use `\textbf{6000}`
   in text or just `6000`.
10. **Line 160** — "Iloczyn rozgałęzienia i~długości mieści się w~zakładanej skali
    złożoności…" is hand-wavy; give the concrete product/state-space estimate or trim.
11. **Mixed cross-ref style** — mostly "sekcja~\ref{…}" but line 316 uses "§\ref{…}".
    Pick one.
12. **Lines 261/263** — gloss the "0,84/0,81" slash on first use as "(klasyk/cooldown)".

## Optional enhancements
- §8 H4: explicitly note 6×6 Othello is a solved second-player win — strengthens the
  H4 interpretation.
- Line 251 "kod jest publiczny" — add the repo URL as a footnote.

## Suggested fix order
1. (#3) regenerate Tables 2 & 4 with comma decimals — pure mechanical, high visibility.
2. (#4, #5, #6) three small wording fixes in `report-v2.tex`.
3. (#1) decide how to present §10.
4. (#7, #8) citations.
5. (#2) confirm machine/timing facts.
