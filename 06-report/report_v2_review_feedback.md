# Review feedback for `report-v2.pdf`

## Overall verdict

The report is solid and much better than a simple “toy MCTS report”. The project idea is clear, the experimental setup is mostly sensible, the visuals are useful, and the report honestly discusses that progressive bias did not help much. The biggest fixes are not about the core idea, but about rigor and precision:

1. Rename or qualify the “Buro” heuristic.
2. Clarify the cooldown rule with pseudocode.
3. Make statistical testing precise and verifiable.
4. Soften over-strong claims about “structural” balance.
5. Fix PDF encoding / Polish character copy-paste issues.

After those changes, the report should read as a solid, defensible project report rather than just a collection of MCTS plots.

---

## High-priority issues

### 1. “Buro heuristic” is probably overstated / inaccurate

The report describes “Buro” as a simple positional-weight + mobility heuristic: corners +100, X-squares −50, edges +10, etc. But Michael Buro’s Othello work is not just a hand-written square-weight table; his evaluation function for Logistello was statistically learned from features/patterns and is much more sophisticated.

So the current wording risks implying that the implemented heuristic is Buro’s actual evaluation function. It is safer to describe it as a simplified heuristic inspired by Buro/Othello literature.

Recommended replacement wording:

> heurystyka inspirowana klasycznymi cechami Othello/Buro

or:

> uproszczona heurystyka pozycyjna inspirowana literaturą Othello

Avoid implying that this is the exact evaluation function from Buro’s papers.

---

### 2. Cooldown rule needs pseudocode

The rule says cooled pieces are “transparent”: they do not close a line, do not make it illegal, and cannot be flipped. But the legal-line condition is subtle.

A reader may wonder whether a cooled opponent piece can be skipped over, allowing later non-cooled opponent pieces to be flipped. If yes, this creates non-standard non-contiguous capture behavior. That is fine if intended, but it must be explicit.

Add pseudocode like this:

```text
for direction d:
    seen_flippable_enemy = false
    captured = []
    q = p + d

    while q on board:
        if q is empty:
            reject direction

        if q has own piece:
            accept direction iff seen_flippable_enemy

        if q has enemy piece:
            if q not in cooldown:
                seen_flippable_enemy = true
                captured.append(q)
            else:
                # cooled enemy piece is transparent
                # it does not close, block, or get captured
                pass

        q = q + d
```

Then add a sentence such as:

> Znacznik cooldown nie przerywa skanowania linii; pionek chroniony może zostać pominięty, a odwracane są wyłącznie niechronione pionki przeciwnika znalezione na zaakceptowanej linii.

Without this, someone may implement a different game.

---

### 3. Statistical testing section claims more than the report shows

The report says that win rates are reported with Wilson 95% confidence intervals, and that significance is tested with binomial tests / McNemar tests plus Holm–Bonferroni correction. But most main tables and heatmaps show only point estimates. Table 4 gives p-values, but not enough detail to verify the tests.

Concrete issues:

- Do not write `p = 0.000`. Use `p < 0.001` or `p < 10^{-k}`.
- McNemar requires paired binary outcomes. It is appropriate only when the same paired seeds / colors / matchups are compared.
- If H1 compares UCT vs Naive-Buro in classic and cooldown using independent games, McNemar is probably not the right test for that cross-variant comparison.
- Remis counted as half a win complicates binomial testing because the result is no longer a Bernoulli variable unless draws are handled separately.

Add a short “Statystyka — szczegóły” paragraph explaining exactly how tests were done.

Possible wording if draws were ignored for tests:

> Remisy liczymy jako pół punktu wyłącznie przy raportowaniu współczynnika wygranych. W testach istotności traktujemy remisy jako osobną kategorię i test wykonujemy na liczbie wygranych oraz przegranych po odrzuceniu remisów.

Possible wording if draws were included as half-points:

> Ponieważ remisy są liczone jako pół punktu, raportowane testy należy traktować jako testy na punktach meczowych, a nie jako klasyczne testy Bernoulliego dla zmiennej wygrana/przegrana.

Pick the version that matches the code.

---

### 4. Hyperparameter tuning may bias some hypothesis tests

The heuristics were tuned on Cooldown and reused in both variants. This is not automatically wrong, but it weakens the confirmatory interpretation of H3, especially if Naive-Buro or related weak heuristics were part of the tuning control set.

The report should disclose exactly which three opponents were used during tuning.

If Naive-Buro was in the control set, add a caveat like:

> Ponieważ Cooldown-Buro był strojony na zestawie obejmującym słabsze heurystyki, wynik H3 należy traktować jako potwierdzenie skuteczności strojonej heurystyki, a nie jako niezależny test czystej konstrukcji ręcznej.

Even better: add a short untuned comparison for H3.

---

### 5. “Structural advantage of second player” is too strong

The H4 result is interesting: white wins 58.4% in classic self-play and 49.1% with cooldown. But this is still agent self-play, not a proof of game-theoretic balance.

Use softer wording.

Instead of:

> Reguła zmienia balans gry — znika strukturalna przewaga drugiego gracza.

Use:

> W samogrze badanego agenta reguła wyraźnie zmniejsza przewagę drugiego gracza obserwowaną w klasycznym 6×6.

Or:

> W badanym ustawieniu eksperymentalnym obserwowana przewaga drugiego gracza zanika pod regułą stygnięcia.

If you want to connect this to known 6×6 Othello results, say clearly that the report’s cooldown result is empirical, not a solved-game result.

---

### 6. UCT reward perspective should be specified

In two-player zero-sum MCTS, a common implementation ambiguity is whether `Q(s,a)` is stored from the perspective of:

- the player to move at node `s`,
- the root player,
- or a fixed color.

The report should state this explicitly, because a wrong perspective can silently break MCTS.

Add one sentence, depending on implementation.

If node-player perspective:

> Wartość `Q(s,a)` przechowujemy z perspektywy gracza wykonującego ruch w stanie `s`; podczas backpropagacji wynik jest odwracany przy przejściu przez kolejne poziomy drzewa.

If root-player perspective:

> Wartość `Q(s,a)` przechowujemy z perspektywy gracza korzenia; podczas selekcji w węzłach przeciwnika wybór maksymalizuje wartość odpowiednią dla aktualnego gracza przez zmianę znaku / transformację wyniku.

Use the version matching the code.

---

## Medium-priority issues

### 7. Progressive bias needs heuristic normalization details

The formula uses:

```text
w_H H(s,a) / (N(s,a)+1)
```

This only makes sense if `H(s,a)` has a controlled scale, e.g. `[-1, 1]` or `[0, 1]`. Otherwise `w_H=8.71` is hard to interpret.

Add one of the following:

If normalized:

> Przed użyciem w progressive bias wartości heurystyki normalizowano w obrębie zbioru legalnych ruchów do zakresu `[−1,1]`.

If not normalized:

> Wartości `H(s,a)` używano w skali surowej, a jej wpływ kontrolowano przez strojenie parametru `w_H`; z tego powodu wartości `w_H` należy interpretować wyłącznie względem skali konkretnej heurystyki.

Normalization would be cleaner.

---

### 8. Ranking by average win rate is okay, but Elo / Bradley–Terry would be cleaner

Because the tournament is a balanced round-robin, average win rate is acceptable. But it hides matchup structure. The heatmaps help, but an Elo or Bradley–Terry ranking would look more rigorous.

Not mandatory, but worth adding if there is time.

---

### 9. Some claims are slightly stronger than the data supports

#### Claim: “Najsilniejszy jest UCT-PB-cooldown”

In classic, Table 1 shows UCT-PB-naive has `0.859`, while UCT-PB-cooldown has `0.844`.

Better:

> Najbardziej stabilnym graczem w obu wariantach jest UCT-PB-cooldown; w klasyku bardzo mocny jest też UCT-PB-naive.

#### Claim: transposition tables are weakened

The report says cooldown weakens transposition tables because state depends on history. This is basically true, but transposition tables are still possible if keyed by `(board, cooldown, side_to_move)`.

Better:

> zależność od znaczników cooldown zmniejsza użyteczność prostych tablic transpozycji opartych wyłącznie na konfiguracji planszy.

#### Claim: “plansza i tak się zapełnia”

Games can end before a full board due to double pass, and the histogram includes shorter games.

Better:

> gra zwykle zbliża się do zapełnienia planszy

or:

> reguła nie skraca gry znacząco, ponieważ większość partii nadal trwa blisko maksymalnej długości planszy 6×6.

---

### 10. Human-computer experiment should stay clearly informal

The section is useful and readable, but with 3 people × 4 games per opponent it cannot support general claims about human difficulty.

Add:

> Próba jest zbyt mała, aby estymować realną siłę agentów wobec ludzi; traktujemy ją jako test użyteczności interfejsu i jakościową ilustrację poziomów trudności.

---

## Presentation / LaTeX issues

### 11. PDF text extraction is broken for Polish characters

The parsed text has mojibake like:

- `Jasi«ski`
- `stygni¦cia`
- `±redni`
- `wspóªczynnik`

The visual PDF may look fine, but copy-paste/search/accessibility is broken. This can matter for grading, search, plagiarism systems, and general professionalism.

For pdfLaTeX, use:

```latex
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[polish]{babel}
```

For LuaLaTeX/XeLaTeX, use:

```latex
\usepackage{fontspec}
\usepackage[polish]{babel}
```

Then rebuild and test copy-paste from the generated PDF.

---

### 12. Table 1 should include uncertainty

Table 1 is central. Add confidence intervals or standard errors for the aggregate win rates. The heatmaps can stay as point estimates.

Possible compact format:

```text
UCT-PB-cooldown   0.844 [0.82, 0.86]   0.814 [0.79, 0.84]
```

---

## Suggested conclusion edits

Current conclusion is mostly good, but two claims should be softened.

Instead of:

> Reguła zmienia balans gry — znika strukturalna przewaga drugiego gracza.

Use:

> W samogrze badanego agenta reguła wyraźnie zmniejsza przewagę drugiego gracza obserwowaną w klasycznym 6×6.

Instead of:

> Najsilniejszym graczem jest UCT-PB-cooldown.

Use:

> Najbardziej stabilnym graczem w obu wariantach jest UCT-PB-cooldown; w klasyku bardzo mocny jest też UCT-PB-naive.

---

## Suggested task list for the agent

### Must fix

- [ ] Rename “Buro heuristic” to “Buro-inspired / Othello-inspired positional heuristic”.
- [ ] Add cooldown rule pseudocode.
- [ ] Clarify whether cooled pieces can be skipped over in a line.
- [ ] Add UCT reward perspective during backpropagation.
- [ ] Clarify statistical testing details.
- [ ] Replace all `p = 0.000` with `p < 0.001` or more precise scientific notation.
- [ ] Soften “structural advantage disappears” claims.
- [ ] Fix PDF encoding so Polish characters copy-paste correctly.

### Should fix

- [ ] Add confidence intervals to Table 1.
- [ ] Add normalization details for progressive bias heuristic values.
- [ ] Disclose the exact tuning control opponents.
- [ ] Add caveat about tuning possibly biasing H3.
- [ ] Soften “najsilniejszy” wording for UCT-PB-cooldown.
- [ ] Clarify that transposition tables are weakened, not impossible.
- [ ] Mark human-computer experiment as qualitative / informal.

### Nice to have

- [ ] Add Elo or Bradley–Terry ranking.
- [ ] Add untuned comparison for H3.
- [ ] Add a short appendix/table with exact number of wins/draws/losses for H1–H4.
