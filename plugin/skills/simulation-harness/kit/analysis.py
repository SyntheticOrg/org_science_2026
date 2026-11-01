"""Analysis of the toy reporting game: the decider's accuracy per treatment and the focal contrast, by group.

Adapt the outcome, contrasts, and benchmarks to APPROACH.md and verify them against known-answer records.
This is not a generic analyser. Usage, from the study folder (keep primary and sensitivity runs separate):
    python3 harness/analysis.py runs/<run> [runs/<run> ...] > results/<name>.md
The unit of observation is the group. Incomplete groups are counted, not dropped silently. Resampling is seeded in
stats.py so output is deterministic.
"""

import sys
from pathlib import Path

import runner
import stats

HUMAN = {}  # optional treatment -> benchmark string or value from the existing finding (simulation-harness, benchmarks.md)


def main(dirs):
    accuracy, statuses = {}, {}
    for d in dirs:
        for rec in runner.records(d):
            counts = statuses.setdefault(rec["treatment"], {})
            counts[rec["status"]] = counts.get(rec["status"], 0) + 1
            if rec["status"] == "complete":
                rounds = rec["rounds"]
                accuracy.setdefault(rec["treatment"], []).append(sum(r["payoffs"]["D"] == 10 for r in rounds) / len(rounds))
    print("| Treatment | Status | Groups |")
    print("|---|---|---|")
    for treatment, counts in sorted(statuses.items()):
        for status, count in sorted(counts.items()):
            print(f"| {treatment} | {status} | {count} |")
    print()
    print("| Treatment | Groups | Decider accuracy | 95% CI | Human anchor |")
    print("|---|---|---|---|---|")
    for t, v in sorted(accuracy.items()):
        lo, hi = stats.bootstrap_ci([v], lambda x: sum(x) / len(x), reps=2000)
        print(f"| {t} | {len(v)} | {sum(v) / len(v):.2f} | {lo:.2f} to {hi:.2f} | {HUMAN.get(t, 'n/a')} |")
    if {"conflict-chat", "conflict-report"} <= accuracy.keys():
        diff, p = stats.permutation_diff(accuracy["conflict-chat"], accuracy["conflict-report"], reps=2000)
        lo, hi = stats.bootstrap_ci([accuracy["conflict-chat"], accuracy["conflict-report"]],
                                   lambda a, b: sum(a) / len(a) - sum(b) / len(b), reps=2000)
        print(f"\nFocal contrast, chat minus report under conflict: {diff:+.2f} "
              f"(95% CI {lo:+.2f} to {hi:+.2f}; permutation p = {p:.3f}).")


if __name__ == "__main__":
    main([Path(a) for a in sys.argv[1:]])
