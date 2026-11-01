"""Per-trial summary of every run: one CSV row per trial with its settings and outcomes.

The raw run folders hold full agent transcripts and are mostly kept out of git; this table is what the calibration
log in APPROACH.md and the findings PDF are computed from, so every number there can be checked without them.

Rows of runs that are not on disk (e.g. in a fresh clone, where only the final run is in git) are kept from the
existing table, so the summary of the intermediate runs is never lost.

Usage (from second-test/):
    python3 harness/summary.py                       # reads runs/*/, updates results/trials_summary.csv
"""

import csv
import json
import sys
from pathlib import Path

import networks

HERE = Path(__file__).resolve().parent
PRICE_PER_M = {"input": 0.10, "cached": 0.01, "output": 0.50}  # gpt-6-luna list prices, USD (as first-test)
SETTINGS = ["model", "reasoning_effort", "effort_mix", "searches_per_tick", "repeat_search", "message_costs_time",
            "message_cap", "read_costs_time", "time_budget", "answers_first", "memory", "notepad_words",
            "others_may_know", "plain_pay", "susceptibility"]
FIELDS = (["run", "network", "trial", "seed", "status", "players"] + SETTINGS + ["personas"]
          + ["num_correct", "red_herring", "other", "none", "answered_min5", "answered_min10", "core_correct",
             "messages", "text_messages", "shares", "replies", "forwards", "searches",
             "hub_followers", "hub_follow_eligible", "copy_matches", "copy_changes",
             "calls", "input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens", "cost_usd"])


def category(m, answer):
    if not answer:
        return "none"
    return "correct" if answer[0] == m["culprit"] else "RH" if answer[0] == m["red_herring"] else "OA"


def hub_following(rec):
    """Hub-and-spoke only: spokes without the correct answer when the hub first had it, and how many ended correct."""
    if rec["network"] != "HubAndSpoke":
        return "", ""
    m, snaps = rec["mystery"], rec["snapshots"]
    t0 = next((t for t, s in enumerate(snaps) if category(m, s["murderer"]["1"]) == "correct"), None)
    if t0 is None:
        return 0, 0
    eligible = [n for n in range(2, 10) if category(m, snaps[t0]["murderer"][str(n)]) != "correct"]
    return sum(rec["outcome"]["final"][str(n)] == "correct" for n in eligible), len(eligible)


def copying(rec):
    """Murderer answer changes, and how many match an answer visible among the player's sources a turn earlier."""
    snaps, matches, changes = rec["snapshots"], 0, 0
    for a in rec["answers"]:
        t = a["seconds"] // 30 - 1
        if a["question"] != "murderer" or t < 1:
            continue
        visible = [v[0] for v in (snaps[t - 1]["murderer"][str(s)] for s in networks.sources(rec["network"], a["node"])) if v]
        if visible:
            changes += 1
            matches += a["answer"] in visible
    return matches, changes


def row(run, rec):
    r = {"run": run, **{k: rec.get(k) for k in ("network", "trial", "seed", "status")}, "players": len(rec["players"])}
    for k in SETTINGS:
        v = rec.get(k)
        r[k] = " ".join(v) if isinstance(v, list) else v
    r["personas"] = bool(rec.get("personas"))
    usage = {k: sum(a["usage"].get(k, 0) for a in rec["agents"].values())
             for k in ("calls", "input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens")}
    r.update(usage)
    r["cost_usd"] = round((PRICE_PER_M["input"] * (usage["input_tokens"] - usage["cached_tokens"])
                           + PRICE_PER_M["cached"] * usage["cached_tokens"] + PRICE_PER_M["output"] * usage["output_tokens"]) / 1e6, 5)
    if rec["status"] != "complete":
        return r
    m, snaps, out = rec["mystery"], rec["snapshots"], rec["outcome"]
    final = list(out["final"].values())
    r.update(num_correct=out["num_correct"], red_herring=final.count("RH"), other=final.count("OA"), none=final.count("none"),
             answered_min5=sum(1 for a in snaps[9]["murderer"].values() if a),
             answered_min10=sum(1 for a in snaps[19]["murderer"].values() if a),
             core_correct=sum(out["final"][str(n)] == "correct" for n in networks.core(rec["network"])) if networks.core(rec["network"]) else "")
    for k in ("messages", "text_messages", "shares", "replies", "forwards", "searches"):
        r[k] = out[k]
    r["hub_followers"], r["hub_follow_eligible"] = hub_following(rec)
    r["copy_matches"], r["copy_changes"] = copying(rec)
    return r


def main():
    runs = HERE.parent / "runs"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "results" / "trials_summary.csv"
    present = {p.name for p in runs.iterdir() if p.is_dir()}
    rows = [r for r in csv.DictReader(out.open())] if out.exists() else []
    rows = [r for r in rows if r["run"] not in present]
    kept = len(rows)
    for d in sorted(p for p in runs.iterdir() if p.is_dir()):
        for f in sorted(d.glob("*.json")):
            if f.name == "config.json":
                continue
            rec = json.loads(f.read_text())
            if rec.get("model") == "fake":
                continue
            rows.append(row(d.name, rec))
    rows.sort(key=lambda r: (r["run"], r["network"], int(r["trial"])))
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} trials from {len({r['run'] for r in rows})} runs ({kept} kept from runs not on disk) -> {out}")


if __name__ == "__main__":
    main()
