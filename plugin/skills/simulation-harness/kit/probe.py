"""Probe: single-agent choices over a grid of conditions, for diagnostics before the freeze (standard library only).

Kit file of the synthetic-organisations plugin, generalised from first-test/harness/incentive_diagnostics.py. Every
(cell, repetition) gets a fresh agent, so no answer depends on an earlier one. This is the diagnostic shape of the
validity-audit modules that compare direct choices across conditions (incentive levels, wrong advice, relabelled
payoffs). Results go to runs/<time>-probe-<name>/: config.json and one line per call in probe.jsonl; the launch is
logged in runs/ledger.jsonl like every other run.
"""

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import agent
import runner


def run_probe(root, name, cells, reps, ask, model=None, seed=1, workers=8):
    """cells: list of dicts (the conditions). ask(model, cell, rep) -> (answer, Agent). With model=None every call
    gets its own FakeModel. Unusable replies are kept as rows with an error. Returns the run folder."""
    root = Path(root)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-probe-{name}" + ("-fake" if model is None else "")
    out = root / "runs" / run_id
    out.mkdir(parents=True)
    (out / "config.json").write_text(json.dumps(
        {"run_id": run_id, "mode": "probe", "probe": name, "cells": cells, "reps": reps, "seed": seed,
         "model": model.describe() if model else {"backend": "fake"}, "files": runner.hashes(root),
         "provenance": runner.provenance(root), "started": agent.now()}, indent=1, ensure_ascii=False))
    runner.ledger(root, {"event": "start", "run_id": run_id, "dir": out.relative_to(root).as_posix(), "mode": "probe",
                         "fake": model is None, "calls": len(cells) * reps})

    def one(i, cell, rep):
        m = model or agent.FakeModel(f"{seed}-{name}-{i}-{rep}")
        try:
            answer, a = ask(m, cell, rep)
            return {"cell": i, "rep": rep, "status": "complete", "answer": answer, "agent": a.record()}
        except (agent.GroupFailed, agent.ModelError) as e:
            return {"cell": i, "rep": rep, "status": "incomplete", "error": str(e)}

    statuses = Counter()
    with ThreadPoolExecutor(workers) as pool, open(out / "probe.jsonl", "a") as f:
        for fut in as_completed([pool.submit(one, i, c, r) for i, c in enumerate(cells) for r in range(reps)]):
            row = fut.result()
            statuses[row["status"]] += 1
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    runner.ledger(root, {"event": "end", "run_id": run_id, "statuses": dict(statuses)})
    return out


def tally(run_dir, field):
    """Counts of answer[field] per cell index, from a probe's probe.jsonl; incomplete rows count as None."""
    counts = {}
    for line in (Path(run_dir) / "probe.jsonl").read_text().splitlines():
        row = json.loads(line)
        counts.setdefault(row["cell"], Counter())[row.get("answer", {}).get(field)] += 1
    return dict(sorted(counts.items()))
