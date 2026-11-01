"""Follow-up studies on weak-buy: information monopoly and persuasion. Outlines: ../monopoly-study, ../persuasion-study.

Usage (from first-test/):
    python3 harness/followup.py prepare --out runs/followup/<cohort> --jobs smoke [--fake]
    python3 harness/followup.py groups --out runs/followup/<cohort> [--fake]
"""

import argparse
import hashlib
import itertools
import json
import multiprocessing
import random
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import manipulations as mp
import task
from agent import EFFORT, MODEL, SECTIONS, fill
from group_incentives import FixedFake, LoggedModel
from incentive_diagnostics import atomic
from runner import run_triad

HERE = Path(__file__).resolve().parent
STUDY_FILES = {"design.json": HERE.parent / "monopoly-study/design.json", "prompts.json": HERE.parent / "persuasion-study/prompts.json"}
DESIGN = json.loads(STUDY_FILES["design.json"].read_text())
PROMPTS = json.loads(STUDY_FILES["prompts.json"].read_text())
MONOPOLY_CUES = {int(r): v for r, v in DESIGN["allocation"].items()}
SYSTEM = {"N": "system_participant", "D": "system_participant_differ", "M": "system_participant_differ"}
SEED = 2026102214
WORKERS = 4


def conditions():
    """Both studies' condition matrices, in the order of the outline tables."""
    out = [{"study": "persuasion", "condition": f"C{i:02d}", "side_gbp": b, "rounds": n, "prompt": p, "marked": False, "monopoly": False}
           for i, (b, n, p) in enumerate(itertools.product((0, 5, 10), (3, 5), "ND"), 1)]
    out += [{"study": "monopoly", "condition": f"M{i}", "side_gbp": b, "rounds": 5, "prompt": "M", "marked": m, "monopoly": True}
            for i, (b, m) in enumerate(itertools.product((0, 5, 10), (False, True)), 1)]
    return out


def jobs(kind):
    """full: 3 triads per persuasion condition, 6 per monopoly condition, opening speakers balanced. smoke: one triad per new code path."""
    by_id = {c["condition"]: c for c in conditions()}
    if kind == "smoke":
        picks = [("M6", 1, 1), ("M1", 1, 2), ("C10", 1, 3), ("C07", 1, 1)]
    else:
        picks = [(c["condition"], t, (t - 1) % 3 + 1) for c in conditions() for t in range(1, (6 if c["monopoly"] else 3) + 1)]
    result = [{**by_id[c], "triad": t, "first": f} for c, t, f in picks]
    random.Random(SEED).shuffle(result)
    return [{**j, "seed": SEED * 1000 + i} for i, j in enumerate(result)]


def sources():
    names = ("followup.py", "runner.py", "agent.py", "task.py", "manipulations.py", "instructions.md", "group_incentives.py", "incentive_diagnostics.py")
    files = {name: HERE / name for name in names} | STUDY_FILES
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}


def prepare(root, kind, fake=False):
    assert MODEL == "gpt-6-luna" and EFFORT == "high"
    # The prompts sent must be exactly the frozen outline texts.
    assert SECTIONS["system_participant"] == PROMPTS["conditions"]["N"]["system"]
    assert SECTIONS["system_participant_differ"] == PROMPTS["conditions"]["D"]["system"] == DESIGN["system"]
    assert SECTIONS["sole_marking"] == DESIGN["exclusivity_marking"]["marked"]
    root.mkdir(parents=True, exist_ok=False)
    (root / "source").mkdir()
    for name, path in ({name: HERE / name for name in sources() if name not in STUDY_FILES} | STUDY_FILES).items():
        shutil.copyfile(path, root / "source" / name)
    atomic(root / "config.json", {"created": datetime.now(timezone.utc).isoformat(), "model": MODEL, "reasoning_effort": EFFORT,
        "max_output_tokens": 8192, "http_attempts": 1, "workers": WORKERS, "kind": kind, "fake": fake, "manipulation": "weak-buy",
        "protocol": "no-quiz", "prompt_variant": "neutral-final", "source_sha256": sources(), "jobs": jobs(kind),
        "participant_calls_planned": sum(6 + 3 * j["rounds"] for j in jobs(kind))})
    return {"prepared": kind, "jobs": len(jobs(kind))}


def group_job(root, job, fake):
    # The runner reads a module-level amount: live jobs run in separate processes, fake ones restore it afterwards.
    previous, mp.DISCUSSION_SIDE_GBP = mp.DISCUSSION_SIDE_GBP, job["side_gbp"]
    label = f"{job['condition']}-{job['triad']:03d}"
    try:
        model = FixedFake(job["seed"]) if fake else LoggedModel(root / "calls" / label)
        (root / "groups" / job["condition"]).mkdir(parents=True, exist_ok=True)
        path, status, _ = run_triad("discussion", job["triad"], job["seed"], model, root / "groups" / job["condition"], "weak-buy",
                                    "no-quiz", "neutral-final", "distributed", system_section=SYSTEM[job["prompt"]], rounds=job["rounds"],
                                    first=job["first"], cues=MONOPOLY_CUES if job["monopoly"] else None, marked=job["marked"])
    finally:
        mp.DISCUSSION_SIDE_GBP = previous
    rec = json.loads(path.read_text())
    rec["job"] = job
    if status == "complete" and any(not rec["ranking_after"][str(r)] for r in task.ROLES):
        rec.update(status="failed", error="Final ranking missing after visible ranking retries")
    atomic(path, rec)
    return path


def check(rec, job):
    """Format and delivery checks for one record; returns a list of problems (empty when fine)."""
    problems = []
    if rec["status"] != "complete":
        return [f"status {rec['status']}: {rec.get('error')}"]
    n, first, side = job["rounds"], job["first"], job["side_gbp"]
    cues = MONOPOLY_CUES if job["monopoly"] else task.CUES
    order = [(first - 1 + rnd + i) % 3 + 1 for rnd in range(n) for i in range(3)]
    if [m["speaker"] for m in rec["discussion"]["transcript"]] != order:
        problems.append("speaking order")
    for r in task.ROLES:
        msgs = rec["agents"][str(r)]["messages"]
        initial, turns = msgs[1]["content"], [m["content"] for m in msgs if m["role"] == "user"][1:1 + n]
        expected_info = task.information(r, cues=cues, marked=job["marked"])
        checks = {
            "system prompt": msgs[0]["content"] == fill(SYSTEM[job["prompt"]], role=r),
            "announced rounds": f"The discussion has {n} rounds." in initial,
            "own information": expected_info in initial,
            "marking line": (fill("sole_marking") in initial) == job["marked"],
            "private rule": ("Your private payment" in initial) == (r == 1) and (r != 1 or f"£{side} if two or more participants rank applicant A" in initial),
            "turn counters": [f"Discussion round {k} of {n}." in t for k, t in enumerate(turns, 1)] == [True] * n,
            "reminders": all(("Reminder of your private payment" in t) == (r == 1) for t in turns),
            "final transcript": "Complete public discussion transcript" in [m for m in msgs if m["role"] == "user"][-1]["content"],
            "final ranking": task.is_ranking(rec["ranking_after"][str(r)] or []),
        }
        problems += [f"role {r}: {name}" for name, ok in checks.items() if not ok]
    firsts = [rec["ranking_after"][str(r)][0] for r in task.ROLES]
    if rec["outcome"]["side_gbp"] != {str(r): (side if r == 1 and firsts.count("A") >= 2 else 0) for r in task.ROLES}:
        problems.append("side payment")
    if rec["outcome"]["bonus_gbp"] != (4 if firsts.count("B") >= 2 else 0):
        problems.append("group bonus")
    return problems


def groups(root, fake=False):
    cfg = json.loads((root / "config.json").read_text())
    assert cfg["source_sha256"] == sources(), "Sources changed; preserve this cohort and start a new one"
    assert cfg["fake"] == fake, "Live and fake records must be separate"
    if fake:
        paths = [group_job(root, job, True) for job in cfg["jobs"]]
    else:
        with ProcessPoolExecutor(WORKERS, mp_context=multiprocessing.get_context("spawn")) as pool:
            paths = [f.result() for f in as_completed([pool.submit(group_job, root, job, False) for job in cfg["jobs"]])]
    results = []
    for path in sorted(paths):
        rec = json.loads(path.read_text())
        problems = check(rec, rec["job"])
        firsts = {r: (x or ["?"])[0] for r, x in (rec.get("ranking_after") or {}).items()}
        calls = sum(a["usage"]["calls"] for a in rec["agents"].values())
        results.append({"record": str(path.relative_to(root)), "status": rec["status"], "problems": problems, "calls": calls,
                        "initial_firsts": {r: (x or ["?"])[0] for r, x in (rec.get("ranking_before") or {}).items()}, "final_firsts": firsts})
        print(f"{rec['job']['condition']} triad {rec['job']['triad']} (P{rec['job']['first']} opens): {rec['status']}, {calls} calls, "
              f"final firsts {firsts}, {'OK' if not problems else problems}", flush=True)
    atomic(root / "checks.json", results)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "groups"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--jobs", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--fake", action="store_true")
    args = parser.parse_args()
    print(prepare(args.out, args.jobs, args.fake) if args.stage == "prepare" else f"{sum(not r['problems'] for r in groups(args.out, args.fake))} records passed")
