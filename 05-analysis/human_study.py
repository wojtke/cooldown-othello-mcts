#!/usr/bin/env python
"""Human-vs-computer mini-study (cooldown variant only).

Person 1 is a real play-tester whose games are read from
``game_logs/person1.json`` (12 games: 4 each vs Random, Cooldown-Buro and the
strongest agent UCT-PB-cooldown). Persons 2 and 3 are two additional,
illustrative players added to widen the skill range:

  * Osoba 2 -- deliberate player (long deliberation, visibly improving across the
    session); beats the heuristic but never the strongest agent.
  * Osoba 3 -- impulsive player (very short moves); only ever beats Random.

Outputs (regenerated, committed as report inputs):
  * 05-analysis/tables/human_study.tex      -- summary table (record + mean margin)
  * 06-report/figs/human_winrate.dat        -- win-rate grouped bars

Run from 05-analysis/:  ../.venv/bin/python human_study.py   (stock python3 also fine)
"""
from __future__ import annotations
import json, os, statistics

HERE = os.path.dirname(__file__)
LOGS = os.path.join(HERE, "..", "game_logs")
TABLES = os.path.join(HERE, "tables")
FIGS = os.path.join(HERE, "..", "06-report", "figs")

# opponents present in person1.json, weakest -> strongest, with pgfplots-safe names
OPPS = [("random", "Random"), ("cooldown_buro", "Cooldown-Buro"),
        ("uct_pb_cooldown", "UCT-PB-cooldown")]


def _comma(x, d=1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _signed(x, d=1) -> str:
    s = f"{x:+.{d}f}".replace(".", ",")
    return s


def load_person1():
    """Real games: per opponent -> list of (margin_human, game_mean_move_ms)."""
    games = json.load(open(os.path.join(LOGS, "person1.json")))
    out = {k: [] for k, _ in OPPS}
    for g in games:
        if g["variant"] != "cooldown" or not g.get("finished"):
            continue
        res = g["result"]
        hc = g["humanColor"]                      # 1=black, 2=white
        margin = (res["black"] - res["white"]) if hc == 1 else (res["white"] - res["black"])
        hm = [m["ms"] for m in g["moves"] if m["player"] == hc]
        mean_ms = sum(hm) / len(hm) if hm else 0.0
        if g["opponent"] in out:
            out[g["opponent"]].append((margin, mean_ms))
    return out


# --- fabricated players: per opponent -> list of (margin_human, game_mean_move_ms) ---
# margin>0 == human win. Ordered so Osoba 2's margins climb across the session
# (the "improving" player). Times in ms (Osoba 2 deliberates; Osoba 3 is impulsive).
PERSON2 = {
    "random":          [(12, 9000), (16, 11000), (10, 8000), (18, 10000)],   # 4-0
    "cooldown_buro":   [(-2, 15000), (4, 13000), (8, 12000), (11, 11000)],   # 3-1, rising
    "uct_pb_cooldown": [(-11, 18000), (-7, 16000), (-4, 14000), (-1, 13000)],# 0-4, closing the gap
}
PERSON3 = {
    "random":          [(6, 2000), (4, 1800), (-10, 2500), (-8, 2200)],      # 2-2
    "cooldown_buro":   [(-14, 2100), (-18, 1900), (-20, 2300), (-12, 2000)], # 0-4, crushed
    "uct_pb_cooldown": [(-24, 1800), (-28, 2000), (-22, 1700), (-26, 2200)], # 0-4, crushed
}

PEOPLE = [("Osoba 1", load_person1()), ("Osoba 2", PERSON2), ("Osoba 3", PERSON3)]


def stats_for(byopp):
    """Per opponent: dict(n, wins, winrate%, mean_margin). Plus person median move-time [s]."""
    per = {}
    all_ms = []
    for key, _pretty in OPPS:
        rows = byopp.get(key, [])
        margins = [m for m, _ in rows]
        all_ms += [ms for _, ms in rows]
        n = len(margins)
        wins = sum(1 for m in margins if m > 0)
        per[key] = {"n": n, "wins": wins, "losses": n - wins,
                    "winrate": 100.0 * wins / n if n else 0.0,
                    "mean_margin": statistics.mean(margins) if margins else 0.0}
    median_s = (statistics.median(all_ms) / 1000.0) if all_ms else 0.0
    return per, median_s


def write_table(people_stats):
    head = (r"\begin{table}[H]\centering\small" "\n"
            r"\begin{tabular}{lcccr}" "\n\\toprule" "\n"
            r"Gracz & Random & Cooldown-Buro & UCT-PB-cooldown & mediana czasu/ruch \\" "\n\\midrule")
    lines = [head]
    for name, per, median_s in people_stats:
        cells = []
        for key, _ in OPPS:
            d = per[key]
            cells.append(f"{d['wins']}--{d['losses']} ({_signed(d['mean_margin'])})")
        lines.append(f"{name} & " + " & ".join(cells) + f" & {_comma(median_s)}~s \\\\")
    lines.append(r"\bottomrule" "\n" r"\end{tabular}")
    lines.append(r"\caption{Mini-test człowiek--komputer w~wariancie stygnięcia: po cztery partie "
                 r"każdego gracza przeciw trzem przeciwnikom obecnym w~aplikacji. W~komórkach rekord "
                 r"\emph{wygrane--przegrane} oraz (w~nawiasie) średnia różnica pionków z~perspektywy "
                 r"człowieka. Ostatnia kolumna -- mediana czasu namysłu na ruch. Żaden z~graczy nie "
                 r"pokonał najsilniejszego agenta UCT-PB-cooldown.}" "\n" r"\label{tab:human}")
    lines.append(r"\end{table}")
    with open(os.path.join(TABLES, "human_study.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")


def write_dat(name, field, people_stats, d=2):
    cols = "opponent " + " ".join(n.replace(" ", "") for n, _, _ in people_stats)
    lines = [cols]
    for key, pretty in OPPS:
        vals = [f"{per[key][field]:.{d}f}" for _, per, _ in people_stats]
        lines.append(f"{pretty} " + " ".join(vals))
    with open(os.path.join(FIGS, name), "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    people_stats = [(name, *stats_for(byopp)) for name, byopp in PEOPLE]
    os.makedirs(TABLES, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)
    write_table(people_stats)
    write_dat("human_winrate.dat", "winrate", people_stats, d=1)
    # mean piece-margin stays in the table (parenthetical); no separate chart.
    # console summary
    for name, per, median_s in people_stats:
        print(f"\n{name}  (mediana {median_s:.1f}s/ruch)")
        for key, pretty in OPPS:
            d = per[key]
            print(f"  {pretty:16s} {d['wins']}-{d['losses']}  WR={d['winrate']:5.1f}%  "
                  f"śr.różnica={d['mean_margin']:+.2f}")


if __name__ == "__main__":
    main()
