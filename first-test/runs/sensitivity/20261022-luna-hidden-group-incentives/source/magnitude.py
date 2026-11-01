"""Experiment 3: discussion outcomes by side-payment amount (APPROACH.md, experiment 3).

Usage (from first-test/):
    python3 harness/magnitude.py <run dir> [more run dirs ...] [--out results/exp3-report.md]

Reads discussion triads only; pass runs of one protocol (paper or open) at a time. The amount is the record's `discussion_side_gbp` (experiment 2 records predate it: £5),
and £0 for the control. When a cell (manipulation, amount) appears in several directories, the last one supplies it.
"""

import json
import statistics as st
import sys
from pathlib import Path

import manipulations as mp
from analysis import bootstrap, bv, ci_str, permutation_greater, votes

FIELDS = ("advocacy", "distortion", "disclosure", "strategic_intent")


def amount(r):
    return 0 if r["manipulation"] == "control" else r.get("discussion_side_gbp", 5)


def load(runs):
    cells, coding = {}, {}
    for run in runs:
        found = {}
        for p in sorted(run.glob("discussion-*-[0-9][0-9][0-9].json")):
            r = json.loads(p.read_text())
            r.setdefault("manipulation", "control")
            r["source"] = (run, p.name)
            if r["status"] == "complete":
                found.setdefault((r["manipulation"], amount(r)), []).append(r)
        cells.update(found)
        f = run / "coding.json"
        if f.exists():
            coding.update({(run, k): v for k, v in json.loads(f.read_text()).items()})
    return cells, coding


def paid(r):
    """(role, target) of every paid agent in a triad."""
    return [(int(k), mp.target(r["manipulation"], int(k))) for k, v in r["pay_keys"].items() if v]


def main(runs, out_path):
    cells, coding = load(runs)
    keys = sorted(cells, key=lambda k: (mp.MANIPULATIONS.index(k[0]), k[1]))
    out = ["# Experiment 3: side-payment magnitude (discussion)", "", "Runs: " + ", ".join(str(r) for r in runs), "",
           "## Outcomes", "",
           "| Manipulation | £ | Triads | B votes before | B votes after [95% CI] | Unanimous | Others ending on a paid agent's target (buy) | Paid agents ranking target first | Side payment earned | Group bonus paid |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        rs = cells[k]
        a = bv(rs)
        agents = [(r, role, t) for r in rs for role, t in paid(r)]
        # persuasion: agents not paid for the same target who end on it
        swayed = [(r["ranking_after"][o] or [None])[0] == t for r, role, t in agents for o in ("1", "2", "3")
                  if int(o) != role and mp.target(r["manipulation"], int(o)) != t]
        own = sum(1 for r, role, t in agents if (r["ranking_after"][str(role)] or [None])[0] == t)
        earned = sum(1 for r, role, t in agents if r["outcome"]["side_gbp"][str(role)] > 0)
        out.append(f"| {k[0]} | {k[1]} | {len(rs)} | {f"{st.mean(votes(r['ranking_before']) for r in rs):.2f}" if all("ranking_before" in r for r in rs) else "—"} | "
                   f"{st.mean(a):.2f} [{ci_str(*bootstrap([a], st.mean))}] | {sum(x == 3 for x in a)}/{len(rs)} | "
                   + ((f"{sum(swayed)}/{len(swayed)}" if k[0].endswith("buy") else "—") + f" | {own}/{len(agents)} | {earned}/{len(agents)}" if agents else "— | — | —")
                   + f" | {sum(x >= 2 for x in a)}/{len(rs)} |")

    out += ["", "## Change against £5 (B votes after discussion)", "",
            "| Manipulation | £ | Difference vs £5 [95% CI] | One-sided p (fewer B votes) |", "|---|---|---|---|"]
    for k in keys:
        base = cells.get((k[0], 5))
        if k[1] > 5 and base:
            d, p = permutation_greater(bv(base), bv(cells[k]))
            lo, hi = bootstrap([bv(cells[k]), bv(base)], lambda x, y: st.mean(x) - st.mean(y))
            out.append(f"| {k[0]} | {k[1]} | {-d:+.2f} [{ci_str(lo, hi)}] | {p:.3f} |")

    amounts = sorted({k[1] for k in keys if k[1] > 0})
    if all((m, x) in cells for m in mp.MANIPULATIONS[1:] for x in amounts):
        def contrast(wb, ws, sb, ss):  # buy minus sell, averaged over strength
            return (st.mean(wb) + st.mean(sb) - st.mean(ws) - st.mean(ss)) / 2
        out += ["", "## Buy minus sell (conflict vs placebo), averaged over weak and strong", "", "| £ | Buy − sell [95% CI] |", "|---|---|"]
        for x in amounts:
            g = [bv(cells[(m, x)]) for m in mp.MANIPULATIONS[1:]]
            out.append(f"| {x} | {contrast(*g):+.2f} [{ci_str(*bootstrap(g, contrast))}] |")

    if coding:
        out += ["", "## Coded transcripts (paid agents)", "", "| Manipulation | £ | Agents | Advocacy | Distortion | Disclosure | Strategic intent |", "|---|---|---|---|---|---|---|"]
        for k in keys:
            rs = [res for r in cells[k] for res in coding.get(r["source"], {}).values() if res["paid"]]
            if rs:
                n = len(rs)
                out.append(f"| {k[0]} | {k[1]} | {n} | " + " | ".join(f"{sum(x[f]['value'] for x in rs)}/{n}" for f in FIELDS) + " |")

    if any("cues" in v for roles in coding.values() for v in roles.values()):
        out += ["", "## Cue disclosure (share of each agent's nine own cues, coded)", "",
                "| Manipulation | £ | Agents | Paid | Shared | Misstated | Withheld | Strong-buy P2 misstates A personal skills |", "|---|---|---|---|---|---|---|---|"]
        for k in keys:
            for paid_flag in (True, False):
                rs = [(r, int(role), res) for r in cells[k] for role, res in coding.get(r["source"], {}).items()
                      if "cues" in res and res["paid"] == paid_flag]
                if not rs:
                    continue
                vals = [v for _, _, res in rs for v in res["cues"].values()]
                lie = [res["cues"]["A_personal_skills"] == "misstated" for r, role, res in rs if k[0] == "strong-buy" and role == 2]
                out.append(f"| {k[0]} | {k[1]} | {len(rs)} | {'yes' if paid_flag else 'no'} | "
                           + " | ".join(f"{vals.count(x) / len(vals):.0%}" for x in ("shared", "misstated", "withheld"))
                           + f" | {f'{sum(lie)}/{len(lie)}' if lie else '—'} |")

    text = "\n".join(out) + "\n"
    out_path.write_text(text)
    print(text)


if __name__ == "__main__":
    args = sys.argv[1:]
    out = Path(args[args.index("--out") + 1]) if "--out" in args else None
    runs = [Path(a) for a in args if not a.startswith("--") and (out is None or Path(a) != out)]
    main(runs, out or runs[-1] / "report.md")
