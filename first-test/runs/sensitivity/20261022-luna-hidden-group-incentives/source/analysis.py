"""Analyse one or more run directories: outcomes per cell, tests, manipulation checks, spreads, failures, usage.

Usage (from first-test/):
    python3 harness/analysis.py runs/<exp>/<run_id> [more run dirs ...] [--out results/<name>.md]

When a cell (institution, manipulation) appears in several directories, the directory listed last supplies it.
Without --out, report.md is written to the last directory.
"""

import json
import random
import re
import statistics as st
import sys
from math import comb, sqrt
from pathlib import Path

import manipulations as mp
import task

PRICE_PER_M = {"input": 0.10, "cached": 0.01, "output": 0.50}  # gpt-6-luna list prices, USD
MANIPS = mp.MANIPULATIONS
# Mean B votes per triad, Figure 2 (digitised; see APPROACH.md).
HUMAN_VOTES = {
    ("discussion", "control"): 2.27, ("market", "control"): 1.27,
    ("discussion", "weak-buy"): 0.67, ("market", "weak-buy"): 0.80,
    ("discussion", "weak-sell"): 1.07, ("market", "weak-sell"): 1.00,
    ("discussion", "strong-buy"): 0.53, ("market", "strong-buy"): 1.13,
    ("discussion", "strong-sell"): 1.80, ("market", "strong-sell"): 1.87,
}
HUMAN_UNANIMOUS = {("discussion", "control"): "8/15", ("market", "control"): "1/15"}
# Data B, control markets: mean spread per period.
HUMAN_SPREADS = {
    "B": [17.1, -15.8, -75.4, 19.5, 43.1, -117.0, -155.3, -204.1, -121.9, -88.3],
    "A and C": [103.2, 122.6, 108.0, 88.7, 79.0, 124.0, 90.4, 120.2, 116.1, 58.7],
}
# Data B: mean spread over all periods and markets, per condition and applicant.
HUMAN_SPREAD_CELLS = {
    "control": {"A": 89.3, "B": -69.5, "C": 112.9}, "weak-buy": {"A": 115.4, "B": 95.8, "C": 135.2},
    "weak-sell": {"A": 280.4, "B": 106.0, "C": 192.2}, "strong-buy": {"A": -3.3, "B": -13.2, "C": 123.8},
    "strong-sell": {"A": 315.2, "B": -144.1, "C": 145.2},
}
DISCLOSURE = re.compile(r"£\s?\d|side payment|private payment|paid (?:extra|more|if)|bonus|incentive", re.I)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def fisher_greater(k1, n1, k2, n2):
    """One-sided Fisher exact p for P(success | group 1) > P(success | group 2)."""
    K, N = k1 + k2, n1 + n2
    return sum(comb(K, x) * comb(N - K, n1 - x) for x in range(k1, min(K, n1) + 1)) / comb(N, n1)


def permutation_greater(a, b, reps=20000, seed=1):
    obs = st.mean(a) - st.mean(b)
    pool, rng, hits = a + b, random.Random(seed), 0
    for _ in range(reps):
        rng.shuffle(pool)
        hits += st.mean(pool[: len(a)]) - st.mean(pool[len(a):]) >= obs - 1e-12
    return obs, (hits + 1) / (reps + 1)


def bootstrap(groups, stat, reps=20000, seed=2):
    """95% percentile CI of stat(*resampled groups), resampling triads within each group."""
    rng = random.Random(seed)
    d = sorted(stat(*[rng.choices(g, k=len(g)) for g in groups]) for _ in range(reps))
    return d[int(0.025 * reps)], d[int(0.975 * reps) - 1]


def load(runs):
    cells = {}
    for run in runs:
        found = {}
        for p in sorted(run.glob("*-[0-9][0-9][0-9].json")):
            r = json.loads(p.read_text())
            r.setdefault("manipulation", "control")
            r.setdefault("pay_keys", {})
            r["file"] = p.name
            found.setdefault((r["condition"], r["manipulation"]), []).append(r)
        cells.update(found)  # a later directory replaces earlier records for the same cell
    return cells, [r for rs in cells.values() for r in rs]


def votes(rankings):
    return sum(1 for x in rankings.values() if x and task.correct(x))


def bv(rs):
    return [r["outcome"]["b_votes"] for r in rs]


def ci_str(lo, hi):
    return f"{lo:.2f} to {hi:.2f}"


def main(runs, out_path):
    cells, recs = load(runs)
    ok = {k: [r for r in rs if r["status"] == "complete"] for k, rs in cells.items()}
    order = [(c, m) for m in MANIPS for c in ("discussion", "market") if (c, m) in cells]
    out = [f"# Results: {', '.join(r.name for r in runs)}", ""]

    out += ["## Outcomes", "",
            "| Institution | Manipulation | Triads complete | Mean B votes (0–3) | Before interaction | Unanimous | Majority | Human mean | Human unanimous |",
            "|---|---|---|---|---|---|---|---|---|"]
    for k in order:
        rs, n = ok[k], len(ok[k])
        human = (HUMAN_VOTES.get(k, ""), HUMAN_UNANIMOUS.get(k, ""))
        if not n:
            out.append(f"| {k[0]} | {k[1]} | 0 of {len(cells[k])} | | | | | {human[0]} | {human[1]} |")
            continue
        u = sum(r["outcome"]["unanimous"] for r in rs)
        m = sum(r["outcome"]["majority"] for r in rs)
        out.append(
            f"| {k[0]} | {k[1]} | {n} of {len(cells[k])} | {st.mean(bv(rs)):.2f} | {st.mean(votes(r['ranking_before']) for r in rs):.2f} | "
            f"{u}/{n} ({ci_str(*wilson(u, n))}) | {m}/{n} ({ci_str(*wilson(m, n))}) | {human[0]} | {human[1]} |"
        )
    out += ["", "Vote distribution (triads with 0/1/2/3 B votes):", ""]
    for k in order:
        out.append(f"- {k[0]} {k[1]}: {[sum(v == x for v in bv(ok[k])) for x in range(4)]}")

    dc, mc = ok.get(("discussion", "control"), []), ok.get(("market", "control"), [])
    if len(dc) >= 2 and len(mc) >= 2:
        a, b = bv(dc), bv(mc)
        diff, p = permutation_greater(a, b)
        lo, hi = bootstrap([a, b], lambda x, y: st.mean(x) - st.mean(y))
        ud, um = sum(r["outcome"]["unanimous"] for r in dc), sum(r["outcome"]["unanimous"] for r in mc)
        jd, jm = sum(r["outcome"]["majority"] for r in dc), sum(r["outcome"]["majority"] for r in mc)
        out += ["", "## Experiment 1: discussion > market in the control condition (unit = triad)", "",
                f"- Mean B votes difference: {diff:.2f}, bootstrap 95% CI {ci_str(lo, hi)}, one-sided permutation p = {p:.4f}",
                f"- Unanimous: Fisher one-sided p = {fisher_greater(ud, len(dc), um, len(mc)):.4f}",
                f"- Majority: Fisher one-sided p = {fisher_greater(jd, len(dc), jm, len(mc)):.4f}"]

    manip = [m for m in MANIPS[1:] if ok.get(("discussion", m)) and ok.get(("market", m))]
    if manip and len(dc) >= 2 and len(mc) >= 2:
        dm = [v for m in manip for v in bv(ok[("discussion", m)])]
        mm = [v for m in manip for v in bv(ok[("market", m)])]
        stat = lambda w, x, y, z: (st.mean(w) - st.mean(x)) - (st.mean(y) - st.mean(z))
        lo, hi = bootstrap([bv(dc), bv(mc), dm, mm], stat)
        out += ["", "## Experiment 2: institution × manipulation (unit = triad)", "",
                f"- Interaction contrast (discussion − market in control, minus the same pooled over {', '.join(manip)}): "
                f"{stat(bv(dc), bv(mc), dm, mm):.2f}, bootstrap 95% CI {ci_str(lo, hi)}",
                "", "| Manipulation | Discussion − market | 95% CI | Humans |", "|---|---|---|---|"]
        for m in ("control",) + tuple(manip):
            a, b = bv(ok[("discussion", m)]), bv(ok[("market", m)])
            lo, hi = bootstrap([a, b], lambda x, y: st.mean(x) - st.mean(y))
            out.append(f"| {m} | {st.mean(a) - st.mean(b):.2f} | {ci_str(lo, hi)} | {HUMAN_VOTES[('discussion', m)] - HUMAN_VOTES[('market', m)]:.2f} |")
        pooled = lambda ms: [v for m in ms if m in manip for c in ("discussion", "market") for v in bv(ok[(c, m)])]
        for label, x, y in (("strong − weak", ("strong-buy", "strong-sell"), ("weak-buy", "weak-sell")),
                            ("sell − buy", ("weak-sell", "strong-sell"), ("weak-buy", "strong-buy"))):
            a, b = pooled(x), pooled(y)
            if a and b:
                lo, hi = bootstrap([a, b], lambda p, q: st.mean(p) - st.mean(q))
                out.append(f"\n- Planned contrast {label} (both institutions): {st.mean(a) - st.mean(b):.2f}, 95% CI {ci_str(lo, hi)}")

    # Manipulation checks.
    rows_d, rows_m = [], []
    for m in MANIPS[1:]:
        for r in ok.get(("discussion", m), []):
            firsts = {int(k): (v[0] if v else None) for k, v in r["ranking_after"].items()}
            for role, key in r["pay_keys"].items():
                if key:
                    t = mp.target(m, int(role))
                    public = [x["message"] for x in r["discussion"]["transcript"] if str(x["speaker"]) == role]
                    rows_d.append((m, firsts[int(role)] == t, any(DISCLOSURE.search(x) for x in public), r["outcome"]["side_gbp"][role] > 0))
        for r in ok.get(("market", m), []):
            for role, key in r["pay_keys"].items():
                if key:
                    t, side = mp.target(m, int(role)), (2 if m.endswith("buy") else 3)
                    n_paid = sum(1 for p in r["market"]["periods"] for tr in p["trades"] if tr[0] == t and str(tr[side]) == role)
                    n_ctrl = [sum(1 for p in c["market"]["periods"] for tr in p["trades"] if tr[0] == t and str(tr[side]) == role) for c in mc]
                    rows_m.append((m, n_paid, st.mean(n_ctrl) if n_ctrl else float("nan"), r["outcome"]["side_gbp"][role]))
    if rows_d:
        out += ["", "## Manipulation checks: discussion (paid agents)", "",
                "| Manipulation | Paid agents | Rank own target first | Mention payment in public (keyword proxy) | Earned side payment |", "|---|---|---|---|---|"]
        for m in MANIPS[1:]:
            rs = [x for x in rows_d if x[0] == m]
            if rs:
                n = len(rs)
                out.append(f"| {m} | {n} | {sum(x[1] for x in rs)}/{n} | {sum(x[2] for x in rs)}/{n} | {sum(x[3] for x in rs)}/{n} |")
        out += ["", "The keyword column is only a screen; the coded checks below use code_transcripts.py."]
    coding, used = {}, {r["file"] for r in recs if r["condition"] == "discussion"}
    for run in runs:
        f = run / "coding.json"
        if f.exists():
            for name, roles in json.loads(f.read_text()).items():
                if name in used:
                    coding[name] = roles
    if coding:
        out += ["", "## Manipulation checks: coded discussion transcripts", "",
                "Same roles in control triads are coded against the strong-condition target (A for roles 1 and 2, C for role 3).", "",
                "| Manipulation | Agents coded | Advocacy | Distortion | Disclosure | Strategic intent (notes) |", "|---|---|---|---|---|---|"]
        for m in MANIPS:
            rs = [res for name, roles in coding.items() if name.startswith(f"discussion-{m}-")
                  for res in roles.values() if res["paid"] or m == "control"]
            if rs:
                n = len(rs)
                out.append(f"| {m} | {n} | " + " | ".join(f"{sum(r[f]['value'] for r in rs)}/{n}" for f in ("advocacy", "distortion", "disclosure", "strategic_intent")) + " |")
    if rows_m:
        out += ["", "## Manipulation checks: market (paid agents)", "",
                "| Manipulation | Paid agents | Target shares bought/sold per market (incentivised side) | Same role in control | Mean side payment (£) |",
                "|---|---|---|---|---|"]
        for m in MANIPS[1:]:
            rs = [x for x in rows_m if x[0] == m]
            if rs:
                out.append(f"| {m} | {len(rs)} | {st.mean(x[1] for x in rs):.1f} | {st.mean(x[2] for x in rs):.1f} | {st.mean(x[3] for x in rs):.2f} |")

    mk = [k for k in order if k[0] == "market" and ok[k]]
    if mk:
        out += ["", "## Market spreads (ECU; negative = more buying)", "",
                "Mean over periods and markets, agents vs humans (Data B):", "",
                "| Manipulation | A | B | C | Human A | Human B | Human C |", "|---|---|---|---|---|---|---|"]
        for k in mk:
            s = {a: st.mean(p["spreads"][a] for r in ok[k] for p in r["market"]["periods"]) for a in "ABC"}
            h = HUMAN_SPREAD_CELLS[k[1]]
            out.append(f"| {k[1]} | {s['A']:.1f} | {s['B']:.1f} | {s['C']:.1f} | {h['A']} | {h['B']} | {h['C']} |")
        if ok.get(("market", "control")):
            rs = ok[("market", "control")]
            out += ["", "Control markets by period:", "",
                    "| Period | B (agents) | A and C (agents) | B (humans) | A and C (humans) |", "|---|---|---|---|---|"]
            for i in range(10):
                sb = st.mean(r["market"]["periods"][i]["spreads"]["B"] for r in rs)
                so = st.mean((r["market"]["periods"][i]["spreads"]["A"] + r["market"]["periods"][i]["spreads"]["C"]) / 2 for r in rs)
                out.append(f"| {i + 1} | {sb:.1f} | {so:.1f} | {HUMAN_SPREADS['B'][i]} | {HUMAN_SPREADS['A and C'][i]} |")
        out += ["", "Trades per market (10 periods):", ""]
        for k in mk:
            trades = [sum(len(p["trades"]) for p in r["market"]["periods"]) for r in ok[k]]
            out.append(f"- {k[1]}: mean {st.mean(trades):.1f}, range {min(trades)}–{max(trades)}")

    out += ["", "## Failures and usage", "",
            "| Institution | Manipulation | Failed triads | Quiz failed | Invalid rankings | Invalid market actions | Calls | Cache hit | Cost (USD) |",
            "|---|---|---|---|---|---|---|---|---|"]
    for k in order:
        kinds, u = {}, {"calls": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0}
        for r in cells[k]:
            for a in r["agents"].values():
                for f in a["failures"]:
                    kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
                for x in u:
                    u[x] += a["usage"][x]
        cost = ((u["input_tokens"] - u["cached_tokens"]) * PRICE_PER_M["input"] + u["cached_tokens"] * PRICE_PER_M["cached"]
                + u["output_tokens"] * PRICE_PER_M["output"]) / 1e6
        hit = u["cached_tokens"] / u["input_tokens"] if u["input_tokens"] else 0
        failed = sum(r["status"] != "complete" for r in cells[k])
        out.append(f"| {k[0]} | {k[1]} | {failed} | {kinds.get('quiz_failed', 0)} | {kinds.get('invalid_ranking', 0)} | "
                   f"{kinds.get('invalid_action', 0)} | {u['calls']} | {hit:.0%} | {cost:.2f} |")
    out += ["", "Cost uses list prices for uncached input, cached input, and output; cache-write charges are not included."]
    errors = [f"- {r['condition']}-{r['manipulation']}-{r['triad']:03d}: {r.get('error')}" for r in recs if r["status"] != "complete"]
    if errors:
        out += ["", "Errors:", ""] + errors

    text = "\n".join(out) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)


if __name__ == "__main__":
    args = sys.argv[1:]
    out_arg = None
    if "--out" in args:
        i = args.index("--out")
        out_arg = Path(args[i + 1])
        del args[i:i + 2]
    runs = [Path(p) for p in args]
    main(runs, out_arg or runs[-1] / "report.md")
