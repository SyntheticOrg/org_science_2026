"""Checks for payoffs, game sequences, human benchmarks, and a fake-model run of every treatment.
Run from third-test/: python3 harness/test_core.py [run dirs to check instead]  (the data checks also need pandas and the replication package:
uv run --with pandas python harness/test_core.py)"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import game
import runner
from agent import FakeModel

PKG = Path(__file__).resolve().parent.parent / "source" / "zenodo" / "extracted" / "3-Replication-Package"

# The only cells of the English instruction tables that differ from the formula (APPROACH.md, Instructions, item 8).
MISPRINTS = {(f, 4, 5, 2): (8, -7, 5) for f in ("SC-S-D", "SC-A-D", "CH-S-D")}

# Table 2, rounds 10-18: coordinated %, efficient if coordinated %, total surplus, efficiency gain %.
TABLE2 = {1: (69.5, 39.1, 61.4, -108.3), 2: (77.8, 57.1, 65.7, -57.5), 3: (69.5, 58.7, 64.4, -77.4),
          4: (99.6, 45.9, 71.7, 6.5), 5: (97.5, 48.1, 72.2, 14.0), 6: (90.9, 60.6, 71.6, 2.8), 7: (100.0, 61.7, 75.2, 44.3)}
RECOMPUTED = {(3, 1): 58.6}  # SC/A-D: 99 / 169 efficient outcomes when coordinated; printed 58.7


def test_payoffs():
    assert game.payoffs(1, 1, 1) == (26, 54, 80) and game.payoffs(4, 5, 2) == (8, -3, 5)
    for g in game.GAMES:
        assert game.payoffs(g, g, g)[2] == 80 and game.payoffs(g, 3, 3)[2] == game.safe_surplus(g)
        assert max(game.payoffs(g, r, c)[2] for r in game.ACTIONS for c in game.ACTIONS if r != c) <= 55
    # The text tables carry exactly the formula's numbers, in order.
    nums = [int(x) for x in re.findall(r"-?\d+", re.sub(r"Game \d|[fc]\d", "", game.tables_text()))]
    assert nums == [v for g in game.GAMES for r in game.ACTIONS for c in game.ACTIONS for v in game.payoffs(g, r, c)]


def test_payoffs_against_instructions():
    """All 1,000 cells of the eight English PDFs, when the package and pdftotext are present."""
    if not PKG.exists() or not shutil.which("pdftotext"):
        print("  (skipped: no replication package or pdftotext)")
        return
    found = {}
    for pdf in sorted((PKG / "Instructions").glob("*-English.pdf")):
        text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        rows = [(int(m[1]), [int(x) for x in re.findall(r"-?\d+", m[2].replace("−", "-"))])
                for m in re.finditer(r"^\s*f([1-5])\s+(.*)$", text, flags=re.M)]
        assert len(rows) == 25, (pdf.name, len(rows))
        for i, (r, nums) in enumerate(rows):
            g = i // 5 + 1
            assert r == i % 5 + 1 and len(nums) == 15, (pdf.name, i)
            for c in game.ACTIONS:
                cell = tuple(nums[3 * c - 3:3 * c])
                if cell != game.payoffs(g, r, c):
                    found[(pdf.name.removesuffix("-English.pdf"), g, r, c)] = cell
    assert found == MISPRINTS, found


def _human():
    try:
        import pandas as pd
    except ImportError:
        return None
    if not PKG.exists():
        return None
    main = pd.read_stata(PKG / "BC Master Data, Main Experiment.dta", convert_categoricals=False)
    follow = pd.read_stata(PKG / "BC Master Data, Follow Up Experiment.dta", convert_categoricals=False)
    return [d.drop_duplicates(["session", "group", "period"]) for d in (main, follow)]


def test_sequences_against_data():
    data = _human()
    if data is None:
        print("  (skipped: no pandas or replication package)")
        return
    for d in data:
        for (session, group), x in d.sort_values("period").groupby(["session", "group"]):
            assert [int(v) for v in x.game] == game.SEQUENCES[int(group)], (session, group)


def test_table2_from_data():
    """The outcome code reproduces Table 2 from the human choices, except the one documented printing difference."""
    data = _human()
    if data is None:
        print("  (skipped: no pandas or replication package)")
        return
    late = data[0][data[0].period >= 10]
    for t, printed in TABLE2.items():
        d = late[late.true_treatment_ordered == t]
        kinds = [game.outcome(int(g), int(r), int(c)) for g, r, c in zip(d.game, d.strategy1, d.strategy2)]
        coord = [k for k in kinds if k != "failure"]
        assert all(game.payoffs(int(g), int(r), int(c))[2] == s for g, r, c, s in zip(d.game, d.strategy1, d.strategy2, d.payoff_manager))
        gains = [game.efficiency_gain(list(zip(x.game.astype(int), x.payoff_manager))) for _, x in d.groupby(["session", "group"])]
        got = (100 * len(coord) / len(kinds), 100 * coord.count("efficient") / len(coord),
               d.payoff_manager.mean(), 100 * sum(gains) / len(gains))
        for k, (p, v) in enumerate(zip(printed, got)):
            assert round(v, 1) == RECOMPUTED.get((t, k), p), (t, k, p, v)


CALLS = {"NC-D": 2, "SC/S-D": 8, "SC/A-D": 3, "SC-MC": 3}  # per period, exactly, plus any re-asks


def check_record(rec):
    """Integrity of one group record, fake or live: draws, payoffs, isolation, feedback, chat delivery."""
    t = rec["treatment"]
    assert rec["status"] == "complete", rec.get("error")
    assert [x["game"] for x in rec["rounds"]] == game.SEQUENCES[rec["position"]]
    assert set(rec["agents"]) == ({"F", "C", "A"} if t in runner.A_ACTS else {"F", "C"})
    n = sum(a["usage"]["calls"] - len(a["failures"]) for a in rec["agents"].values())
    assert n == 18 * CALLS[t] if t in CALLS else n <= 18 * (len(runner.WRITERS[t]) * rec["turns"] + 2), (t, n)
    prompts = {r: [m["content"] for m in a["messages"] if m["role"] == "user"] for r, a in rec["agents"].items()}
    everything = {r: "\n".join(p) for r, p in prompts.items()}
    for r, text in everything.items():
        assert "{" not in text.replace("```", ""), (t, r)  # no unfilled placeholders
        assert text.count("Thanks for coming") == 1 and text.count("Block 2. There will now be") == 1
    # A never learns the game before the period's result.
    assert "A" not in everything or "The computer selected Game" not in everything["A"], t
    for x in rec["rounds"]:
        assert (x["payoffs"]["F"], x["payoffs"]["C"], x["payoffs"]["A"]) == game.payoffs(x["game"], x["row"], x["column"])
        assert not rec["notes"] or all(a["note"] for a in x["actions"])
        result = f"Result of block {x['block']}, period {x['period']}:"
        for r, p in prompts.items():  # every player gets each result once, in a message of its own
            assert sum(result in m for m in p) == 1 and all(m.startswith(result) for m in p if result in m), (t, r)
        if t == "SC-MC":
            assert f"F reported Game {x['reports']['F']} and C reported Game {x['reports']['C']}." in everything["F"]
        if "chat" in x:
            log = x["chat"]
            assert {m["speaker"] for m in log} <= set(runner.WRITERS[t])
            last = [m for m in log if m["turn"] == log[-1]["turn"]]
            assert (x["chat_ended"] == "silence") == all(m["message"] is None for m in last)
            assert x["chat_ended"] == "silence" or log[-1]["turn"] == rec["turns"]
            if t == "EC-MC":
                assert all(m["message"] in runner.PRESET[m["speaker"]] for m in log if m["message"])
            for k, m in enumerate(log):  # every message reaches every other simulated reader, complete
                for r in rec["agents"]:
                    # Known gap (APPROACH.md, Deviations): when A decides, F and C have no screen after the chat,
                    # so what is written after their final turn of a budget-ended chat never reaches them.
                    after_last = t in runner.A_DECIDES and r != "A" and k > max(i for i, e in enumerate(log) if e["speaker"] == r)
                    if m["message"] and r != m["speaker"] and not after_last:
                        assert f"  {m['speaker']}: {m['message']}" in everything[r], (t, r, m)
    if t == "CH/S-D":
        assert "A" not in rec["agents"] and "A" in rec["chat_readers"]
        assert "Player A can read the chat but cannot write in it." in everything["F"]


def test_analysis_humans():
    """The analysis recomputes the printed human values, except the documented differences."""
    try:
        import analysis
    except ImportError:
        print("  (skipped: needs pandas and scipy)")
        return
    if not PKG.exists():
        print("  (skipped: no replication package)")
        return
    rounds, reports, chats = analysis.human_data()
    known = {("table2", "SC/A-D", 1): 58.6, ("table7", "CH-MC", 0, 1): 2.3, ("table7", "CH-MC", 1, 0): 43.3, ("table7", "CH-MC", 2, 0): 43.2}
    late = analysis.window(rounds, "10-18")
    for t, printed in analysis.PRINTED["table2"].items():
        for k, (p, v) in enumerate(zip(printed, analysis.table2_row(late[late.treatment == t]))):
            assert round(v, 1) == known.get(("table2", t, k), p), (t, k, v)
    for t, printed in analysis.PRINTED["table3"].items():
        assert tuple(round(v, 1) for v in analysis.table3_row(late[late.treatment == t])) == printed, t
    for t, rows in analysis.PRINTED["table7"].items():
        got = analysis.table7(reports, t)
        for g, pair in enumerate(rows):
            for k, c in enumerate(("truth", "lie")):
                assert round(got.loc[g + 1, c], 1) == known.get(("table7", t, g, k), pair[k]), (t, g, c)
    rep = analysis.window(reports, "10-18")
    for t, (rev, lie) in analysis.PRINTED["table9"].items():
        assert round(100 * late[late.treatment == t].revealed.mean(), 1) == rev and round(100 * rep[rep.treatment == t].lie.mean(), 1) == lie, t
    diff = lambda t: analysis.safe_diff(late[late.treatment == t])
    assert [round(analysis.signrank_p(diff(t)), 3) for t in ("SC-MC", "CH/S-D", "CH/A-D", "EC-MC")] == [.443, .116, .104, .375]
    surplus = lambda t: late[late.treatment == t].groupby("group").surplus.mean()
    assert [round(analysis.ranksum_p(surplus("CH-MC"), surplus(t)), 3) for t in ("SC-MC", "CH/S-D", "CH/A-D")] == [.003, .013, .162]


def test_fake_run():
    out = Path(tempfile.mkdtemp())
    for t in runner.TREATMENTS:
        _, rec = runner.run_group(t, 1, 7, FakeModel(t), out, notes=True)
        check_record(rec)
    shutil.rmtree(out)


if __name__ == "__main__":
    if len(sys.argv) > 1:  # check live records instead: python3 harness/test_core.py runs/<run>
        for d in sys.argv[1:]:
            for path in sorted(Path(d).glob("*-[0-9][0-9].json")):
                check_record(json.loads(path.read_text()))
                print(f"  {path.name} ok")
        sys.exit()
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            print(name)
            f()
    print("all checks passed")
