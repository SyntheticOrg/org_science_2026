"""Checks for the kit. Run from the kit folder: python3 test_kit.py

Unit checks of each part; the toy study with fake and scripted (known-answer) models; and the research-record rules
end to end in a temporary study folder: pilot, calibration guard, freeze, main run, variant, and aborted launch.
Also the template for a study's harness/test_core.py: keep check_record and the known-answer check, rewritten for the
study's task.
"""

import contextlib
import io
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import agent
import analysis
import chat
import coding
import personas
import probe
import runner
import stats
import study
from agent import Agent, FakeModel, GroupFailed, InvalidReply

KIT = Path(__file__).resolve().parent
INT = agent.obj({"x": {"type": "integer"}})


# --- the toy study -------------------------------------------------------------------

def check_record(rec, treatment=None, notes=False):
    """Integrity of one toy record: information isolation, payoffs, results, chat delivery, notes. A record from a
    run folder carries its treatment; one from run_group directly needs it passed."""
    treatment = treatment or rec["treatment"]
    assert rec["status"] == "complete", rec.get("error")
    prompts = {r: "\n".join(m["content"] for m in a["messages"] if m["role"] == "user") for r, a in rec["agents"].items()}
    assert "The number this round is" not in prompts["D"]  # D never sees the draw before the result
    for x in rec["rounds"]:
        assert x["payoffs"] == study.payoffs(x["state"], x["choice"], treatment.startswith("conflict"))
        assert f"The number this round is {x['state']}" in prompts["A"]
        assert all(prompts[r].count(f"Result of round {x['round']}:") == 1 for r in prompts)
        assert all(f"  A: {m['message']}" in prompts["D"] for m in x.get("chat", []) if m["speaker"] == "A" and m["message"])
    if notes:
        assert all("note" in json.loads(m["content"]) for a in rec["agents"].values() for m in a["messages"] if m["role"] == "assistant")


def truthful(messages, schema_name):
    """Scripted participants whose results are known in advance: A tells the truth, D follows A."""
    role = re.search(r"as player (\w)", messages[0]["content"]).group(1)
    last, everything = messages[-1]["content"], "\n".join(m["content"] for m in messages)
    drawn = re.findall(r"The number this round is (\d)", everything)
    if schema_name == "report":
        return {"number": int(drawn[-1])}
    if schema_name == "chat":
        return {"message": f"It is {drawn[-1]}." if role == "A" and "A (you): It is" not in last else None}
    return {"number": int(re.findall(r"(?:reports the number|A: It is) (\d)", last)[-1])}


def test_fake_run_of_every_treatment():
    for t in study.TREATMENTS:
        for notes in (False, True):
            check_record(study.run_group(runner.Group(t, 1, 3, FakeModel(t), notes, None)), t, notes)


def test_known_answers():
    for t in study.TREATMENTS:
        rec = study.run_group(runner.Group(t, 1, 7, FakeModel(script=truthful), False, None))
        check_record(rec, t)
        assert all(x["payoffs"]["D"] == 10 for x in rec["rounds"])
        assert all(x["payoffs"]["A"] == (10 if t == "aligned-report" or x["state"] == 5 else 0) for x in rec["rounds"])


# --- the parts -----------------------------------------------------------------------

def test_fill():
    assert agent.fill("a {x} b", x="{y}") == "a {y} b"
    with contextlib.suppress(AssertionError):
        agent.fill("a {x}")
        raise RuntimeError("a missing placeholder passed")


def test_agent_retry_record_memory_notepad():
    replies = iter([InvalidReply("refusal", dict(agent.ZERO_USAGE), {"returned_model": "m"}), '{"x": 1}'])

    def flaky(messages, name, schema):
        r = next(replies)
        if isinstance(r, Exception):
            raise r
        return r, dict(agent.ZERO_USAGE), {"returned_model": "m-2026"}

    a = Agent("A", flaky, "system")
    assert a.ask("q", "s", INT) == {"x": 1}
    assert [c["ok"] for c in a.calls] == [False, True] and a.calls[1]["returned_model"] == "m-2026" and len(a.failures) == 1
    with contextlib.suppress(GroupFailed):
        Agent("B", lambda m, n, s: ("not json", dict(agent.ZERO_USAGE), {}), "system").ask("q", "s", INT)
        raise RuntimeError("two unusable replies did not raise GroupFailed")
    m = Agent("C", FakeModel(), "system", memory=1)
    m.ask("rules", "s", INT, pin=True)
    for i in range(3):
        m.ask(f"turn {i}", "s", INT)
    assert [x["content"] for x in m.context() if x["role"] == "user"] == ["rules", "turn 2"]
    assert len(m.messages) == 9  # the full history is still recorded
    pad = agent.Notepad(3)
    assert pad.add(1, "one two three four") and pad.text() == "- 1: one two three"


def test_chat():
    said = []

    def say(role, turn, log):
        said.append(turn)
        return "hi" if turn == 1 else None

    log, ended = chat.run_chat(say, ("A", "B"), 5, random.Random(1))
    assert ended == "silence" and max(said) == 2
    log, ended = chat.run_chat(lambda r, t, l: "x", ("A", "B"), 3, random.Random(1), cap=1)
    assert ended == "silence" and sum(m["message"] is not None for m in log) == 2
    assert "A (you): x" in chat.transcript(log, "A")


def test_stats():
    lo, hi = stats.wilson(5, 10)
    assert abs(lo - 0.2366) < 1e-3 and abs(hi - 0.7634) < 1e-3
    assert abs(stats.fisher_greater(5, 5, 0, 5) - 1 / 252) < 1e-12
    diff, p = stats.permutation_diff([1, 1, 1], [0, 0, 0], reps=2000)
    assert diff == 1 and p < 0.2
    mean = lambda x: sum(x) / len(x)
    assert stats.bootstrap_ci([[1, 2, 3, 4]], mean, reps=500) == stats.bootstrap_ci([[1, 2, 3, 4]], mean, reps=500)
    assert stats.extreme_share([0, 1, 0.5], 0, 1) == 2 / 3


def test_personas():
    assert "year-old" in personas.describe(personas.draw(random.Random(1)))


def test_probe(tmp):
    root = tmp / "probe-study"
    (root / "harness").mkdir(parents=True)

    def ask(model, cell, rep):
        a = Agent("A", model, "system")
        return a.ask(f"Disclosing costs {cell['cost']}.", "disclose", agent.obj({"disclose": agent.enum(["yes", "no"])})), a

    out = probe.run_probe(root, "disclosure", [{"cost": 0}, {"cost": 5}], 4, ask)
    counts = probe.tally(out, "disclose")
    assert sorted(counts) == [0, 1] and all(sum(c.values()) == 4 for c in counts.values())
    assert [json.loads(l)["event"] for l in (root / "runs" / "ledger.jsonl").read_text().splitlines()] == ["start", "end"]


def test_coding(tmp):
    units = {f"u{i:02d}": f"text {i}" for i in range(20)}
    schema, out = {"claims": {"type": "integer", "enum": [0, 1, 2]}}, tmp / "coding.json"
    first = coding.code_units(FakeModel(1), units, "Count the claims.", schema, out)
    assert len(first["units"]) == 20
    assert coding.code_units(FakeModel(2), units, "Count the claims.", schema, out)["units"] == json.loads(out.read_text())["units"]
    with contextlib.suppress(SystemExit):
        coding.code_units(FakeModel(3), units, "Another rubric.", schema, out)
        raise RuntimeError("a changed rubric was accepted")
    with contextlib.redirect_stdout(io.StringIO()):
        _, sample = coding.review(out, units, lambda coded: coded["claims"] > 0)
    (tmp / "hand.json").write_text(json.dumps({k: True for k in sample}))
    assert coding.agreement(tmp / "hand.json") == (1.0, 2)


def test_analysis_known_answers(tmp):
    root = tmp / "known-analysis"
    root.mkdir()
    records = [
        ("conflict-chat", "complete", [10, 0]),
        ("conflict-chat", "complete", [10]),
        ("conflict-report", "complete", [0, 0]),
        ("conflict-report", "incomplete", []),
        ("conflict-report", "error", []),
        ("aligned-report", "incomplete", []),
    ]
    for number, (treatment, status, payoffs) in enumerate(records, 1):
        rec = {"treatment": treatment, "status": status,
               "rounds": [{"payoffs": {"D": p}} for p in payoffs]}
        (root / runner.record_name(treatment, number)).write_text(json.dumps(rec))
    report = io.StringIO()
    with contextlib.redirect_stdout(report):
        analysis.main([root])
    text = report.getvalue()
    assert "| conflict-chat | 2 | 0.75 | 0.50 to 1.00 |" in text  # equal group weights, not round weights
    assert "| conflict-report | 1 | 0.00 | 0.00 to 0.00 |" in text
    assert "| conflict-report | incomplete | 1 |" in text and "| conflict-report | error | 1 |" in text
    assert "| aligned-report | incomplete | 1 |" in text  # retain treatments with no complete groups
    assert "chat minus report under conflict: +0.75 (95% CI +0.50 to +1.00;" in text


# --- the research record, end to end ---------------------------------------------------------

def cli(root, *args):
    return subprocess.run([sys.executable, "harness/study.py", *args], cwd=root, capture_output=True, text=True)


def test_research_record(tmp):
    root = tmp / "toy"
    (root / "harness").mkdir(parents=True)
    for f in KIT.iterdir():
        if f.suffix in (".py", ".md") and f.name != "test_kit.py":
            shutil.copy(f, root / "harness" / f.name)
    (root / "APPROACH.md").write_text("Study plan: decider accuracy by group; focal contrast: chat minus report.\n")
    (root / "analysis_plan.md").write_text("Legacy analysis plan retained for compatibility.\n")

    r = cli(root, "--fake")
    assert r.returncode == 0, r.stderr
    pilot = next((root / "runs").glob("*-pilot-fake"))
    config = json.loads((pilot / "config.json").read_text())
    assert {"harness/study.py", "APPROACH.md", "analysis_plan.md"} <= set(config["files"])
    assert all(c["returned_model"] == "fake" for rec in runner.records(pilot) for a in rec["agents"].values() for c in a["calls"])

    for treatment in study.FOCAL:
        r = cli(root, "--calibration", "--treatments", treatment, "--fake")
        assert r.returncode != 0 and "focal" in r.stderr
    assert cli(root, "--calibration", "--treatments", "aligned-report", "--fake").returncode == 0
    assert cli(root, "--main", "--fake").returncode != 0  # no freeze yet

    assert cli(root, "--freeze", "--groups", "2").returncode == 0
    r = cli(root, "--main", "--fake")
    assert r.returncode == 0, r.stderr
    main = next((root / "runs").glob("*-main-fake"))
    assert len(list(runner.records(main))) == 6  # the frozen 2 groups x 3 treatments
    assert not any(rec["notes"] for rec in runner.records(main))
    assert cli(root, "--main", "--fake", "--notes").returncode != 0

    for name in ("APPROACH.md", "analysis_plan.md"):
        plan = root / name
        original_plan = plan.read_text()
        plan.write_text(original_plan + "Changed outcome definition.\n")
        r = cli(root, "--main", "--fake")
        assert r.returncode != 0 and name in r.stderr
        plan.write_text(original_plan)

    instructions = root / "harness" / "instructions.md"
    original = instructions.read_text()
    instructions.write_text(original + "\nBe brief.\n")
    r = cli(root, "--main", "--fake")
    assert r.returncode != 0 and "harness/instructions.md" in r.stderr
    assert cli(root, "--main", "--fake", "--variant", "brief").returncode == 0
    assert json.loads((next((root / "runs").glob("*-main-brief-fake")) / "config.json").read_text())["variant"] == "brief"
    instructions.write_text(original)

    abort = ("import sys; sys.path.insert(0, 'harness'); import runner, study\n"
             "def boom(group): raise KeyboardInterrupt\nstudy.run_group = boom\n"
             "runner.main(study, ['--fake', '--variant', 'aborted-check'])")
    assert subprocess.run([sys.executable, "-c", abort], cwd=root, capture_output=True).returncode != 0
    events = [json.loads(line) for line in (root / "runs" / "ledger.jsonl").read_text().splitlines()]
    unfinished = {e["run_id"] for e in events if e["event"] == "start"} - {e["run_id"] for e in events if e["event"] == "end"}
    assert len(unfinished) == 1  # the aborted launch, and only it


def test_replication_only(tmp):
    root = tmp / "replication"
    shutil.copytree(KIT, root / "harness", ignore=shutil.ignore_patterns("__pycache__", "test_kit.py"))
    path = root / "harness" / "study.py"
    text = re.sub(r"^TREATMENTS =.*$", 'TREATMENTS = ("aligned-report", "conflict-report")', path.read_text(), flags=re.M)
    text = re.sub(r"^FOCAL =.*$", 'FOCAL = ("conflict-report",)', text, flags=re.M)
    path.write_text(text)
    path = root / "harness" / "analysis.py"
    text = path.read_text().replace('"conflict-report"', '"aligned-report"').replace('"conflict-chat"', '"conflict-report"')
    path.write_text(text.replace("chat minus report under conflict", "conflict minus aligned reports"))
    (root / "APPROACH.md").write_text("Replication only: accuracy under aligned versus conflicting incentives.\n")
    assert cli(root, "--calibration", "--treatments", "aligned-report", "--fake").returncode == 0
    assert cli(root, "--calibration", "--treatments", "conflict-report", "--fake").returncode != 0
    assert cli(root, "--freeze", "--groups", "2").returncode == 0
    r = cli(root, "--main", "--fake")
    assert r.returncode == 0, r.stderr
    main = next((root / "runs").glob("*-main-fake"))
    assert len(list(runner.records(main))) == 4
    config = json.loads((main / "config.json").read_text())
    assert "APPROACH.md" in config["files"] and "analysis_plan.md" not in config["files"]
    r = subprocess.run([sys.executable, "harness/analysis.py", str(main)], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0 and "aligned-report" in r.stdout and "conflict-report" in r.stdout
    assert "conflict minus aligned reports:" in r.stdout
    assert "conflict-chat" not in r.stdout


if __name__ == "__main__":
    if len(sys.argv) > 1:  # check the records of live runs instead: python3 harness/test_core.py runs/<run> ...
        statuses = {}
        for d in sys.argv[1:]:
            for rec in runner.records(d):
                statuses[rec["status"]] = statuses.get(rec["status"], 0) + 1
                if rec["status"] == "complete":
                    check_record(rec, notes=rec["notes"])
        print(f"records checked: {statuses}")
        sys.exit()
    tmp = Path(tempfile.mkdtemp())
    try:
        for name, f in list(globals().items()):
            if name.startswith("test_"):
                print(name, flush=True)
                f(tmp) if f.__code__.co_argcount else f()
        print("all kit checks passed")
    finally:
        shutil.rmtree(tmp)
