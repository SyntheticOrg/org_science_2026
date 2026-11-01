"""Fixed, small OpenAI diagnostic and direct-cost pilots; see INCENTIVE_DIAGNOSTICS.md.

Run diagnostics first, inspect its report, then run disclosure in the same root:
    python3 harness/incentive_diagnostics.py diagnostics --out runs/sensitivity/<new-cohort>
    python3 harness/incentive_diagnostics.py disclosure --out runs/sensitivity/<new-cohort>
"""

import argparse
import hashlib
import html
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import manipulations as mp
import task
from agent import EFFORT, MODEL, FakeModel, OpenAIModel, RANKING, _obj, fill

HERE = Path(__file__).resolve().parent
MODELS = (MODEL, "gpt-5.4-mini-2026-03-17")
FRAMES = {"baseline": "system", "simulation": "system_simulation"}
COSTS = (0, 2, 5, 13)
TOKENS, WORKERS = 8192, 4
INTEGER = {"type": "integer"}
SCORED_RANKING = _obj({"scores": _obj({a: INTEGER for a in task.APPLICANTS}), "ranking": RANKING})


def atomic(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    temporary.replace(path)


def profile_text(profile, labels):
    return "\n".join(f"Applicant {labels[a]}: " + "; ".join(
        f"{attr}: {'positive' if v > 0 else 'negative'}" for attr, v in cues.items())
        for a, cues in profile.items())


def earnings(condition, votes):
    assert mp.DISCUSSION_SIDE_GBP == 5
    return {str(r): 10 + (4 if votes.count("B") >= 2 else 0)
            + mp.discussion_side_payment(condition, r, votes) for r in task.ROLES}


def disclosure_payoffs(cost, reimbursed, release):
    return {"1": 14 - (0 if reimbursed else cost), "2": 14, "3": 14} if release else {"1": 10, "2": 10, "3": 10}


def cases():
    out = {"diagnostics": [], "disclosure": []}
    for rep in (1, 2):
        labels = dict(zip("ABC", "ABC" if rep == 1 else "CAB"))
        expected = {labels[a]: v for a, v in task.SCORES.items()}
        profile = dict(task.FULL_PROFILE.items() if rep == 1 else reversed(list(task.FULL_PROFILE.items())))
        prompt = ("All five characteristics of each applicant are shown below. Each carries equal weight. "
                  "Strength = 2 times the number of positive characteristics minus the number of negative characteristics.\n\n"
                  + profile_text(profile, labels) + "\n\nCalculate each strength and rank all applicants best to worst. "
                  "Either order is acceptable for applicants with equal strengths.")
        out["diagnostics"].append({"id": f"full-profile-{rep:03d}", "family": "full-profile", "repeat": rep,
                                   "prompt": prompt, "schema": SCORED_RANKING, "expected": expected})

        scenarios, descriptions = {}, []
        conditions = list(mp.MANIPULATIONS)
        if rep == 2:
            conditions.reverse()
        for condition in conditions:
            rules = "\n".join(f"Participant {r}: " + (fill(f"rule_{key}", **mp.pay_values()) if (key := mp.key("discussion", condition, r))
                                                      else "No private bonus.") for r in task.ROLES)
            descriptions.append(f"Condition {condition}:\n{rules}")
            for firsts in ("BBB", "AAA", "CCC", "AAB", "ABC"):
                key = condition.replace("-", "_") + "_" + firsts
                scenarios[key] = earnings(condition, list(firsts))
                descriptions.append(f"Scenario {key}: participants 1, 2, 3 respectively rank {', '.join(firsts)} first.")
        prompt = ("Calculate total earnings, including the participation payment, for all three participants in each specified scenario. "
                  "Every participant receives £10. Every participant additionally receives £4 if at least two rank B first. "
                  "The private bonus rules below apply only within their named condition. These are calculations of specified outcomes, not choices.\n\n"
                  + "\n\n".join(descriptions))
        out["diagnostics"].append({"id": f"payment-calculation-{rep:03d}", "family": "payment-calculation", "repeat": rep,
            "prompt": prompt, "schema": _obj({k: _obj({str(r): INTEGER for r in task.ROLES}) for k in scenarios}), "expected": scenarios})

        options = {"O1": "private", "O2": "group"} if rep == 1 else {"O1": "group", "O2": "private"}
        amounts = COSTS if rep == 1 else tuple(reversed(COSTS))
        lines = []
        for amount in amounts:
            lines.append(f"Choice private_{amount}: " + " ".join(f"{label}: " + (
                f"you receive an additional £{amount}; participants 2 and 3 receive no additional payment."
                if kind == "private" else "each of the three participants receives an additional £4.") for label, kind in options.items()))
        out["diagnostics"].append({"id": f"allocation-{rep:03d}", "family": "allocation", "repeat": rep,
            "prompt": "You are participant 1. Everyone receives £10 regardless of the option selected. "
                      "For each independent choice, select one of its two options. All described payments are guaranteed.\n\n" + "\n\n".join(lines),
            "schema": _obj({f"private_{x}": {"type": "string", "enum": list(options)} for x in amounts}),
            "options": options, "private_amounts": list(amounts)})

        turns = []
        for round_ in range(1, 6):
            order = (1, 2, 3) if round_ % 3 == 1 else ((2, 3, 1) if round_ % 3 == 2 else (3, 1, 2))
            for role in order:
                if round_ == 1:
                    cues = {a: {attr: v for attr, v in values.items() if (a, attr) != ("B", "motivation")}
                            for a, values in task.CUES[role].items()}
                    message = profile_text(cues, dict(zip("ABC", "ABC")))
                elif round_ == 5 and role == 1:
                    message = "One additional fact from my private sheet: applicant B's motivation is negative."
                else:
                    message = "I have no other information to report in this turn."
                turns.append(f"Round {round_}, participant {role}: {message}")
        out["diagnostics"].append({"id": f"transcript-{rep:03d}", "family": "transcript", "repeat": rep,
            "prompt": "You are participant 2. There are no private bonuses in this scenario. All five characteristics carry equal weight. "
                      "Strength = 2 times positives minus negatives. Your original private information:\n" + task.information(2)
                      + "\n\nHere is the COMPLETE public discussion, including its final message:\n\n" + "\n\n".join(turns)
                      + "\n\nUse all information now available to calculate each applicant's full strength and submit a strict ranking. "
                      "Either order is acceptable for applicants with equal strengths.",
            "schema": SCORED_RANKING, "expected": task.SCORES})

        actions = {"O1": "release", "O2": "withhold"} if rep == 1 else {"O1": "withhold", "O2": "release"}
        for cost in COSTS:
            for refunded in (False, True):
                prompt = ("You are participant 1 in a paid experiment involving three participants. "
                    "You hold a verified report establishing that applicant B is better than A and C. "
                    "You decide whether to release or withhold this truthful report. Releasing it automatically sends the report; "
                    "there is no other decision or communication. A fixed software decision system selects B if you release it, "
                    "and A if you withhold it. These responses are guaranteed.\n\n"
                    "Every participant receives £10. Each of the three participants additionally receives £4 if B is selected. "
                    f"Releasing the report incurs a private cost of £{cost}, deducted only from your final payment. "
                    + (f"An external experiment budget reimburses the full £{cost} to you if you release the report; "
                       "this reimbursement does not change the other participants' payments. " if refunded else "There is no reimbursement. ")
                    + "Withholding incurs no cost, earns no reimbursement, and no participant receives the B bonus.\n\n"
                    + "\n".join(f"{label}: {action.capitalize()} the report." for label, action in actions.items())
                    + "\n\nSelect one option.")
                out["disclosure"].append({"id": f"cost-{cost:02d}-{'reimbursed' if refunded else 'unreimbursed'}-{rep:03d}",
                    "family": "disclosure", "repeat": rep, "cost": cost, "reimbursed": refunded, "options": actions,
                    "prompt": prompt, "schema": _obj({"choice": {"type": "string", "enum": list(actions)}})})
    return out


def assess(case, answer):
    family = case["family"]
    if family in ("full-profile", "transcript"):
        ranking = answer["ranking"]
        assert sorted(ranking.values()) == list("ABC"), "Ranking must be a permutation"
        expected = case["expected"]
        scores = sum(answer["scores"][a] == expected[a] for a in "ABC")
        ranking_ok = expected[ranking["first"]] == max(expected.values())
        return {"correct": scores + int(ranking_ok), "total": 4, "all_correct": scores == 3 and ranking_ok}
    if family == "payment-calculation":
        correct = sum(answer[k][r] == values[r] for k, values in case["expected"].items() for r in values)
        scenarios = sum(answer[k] == values for k, values in case["expected"].items())
        return {"correct": correct, "total": 75, "scenarios_correct": scenarios, "scenarios_total": 25, "all_correct": correct == 75}
    if family == "allocation":
        choices = {str(x): case["options"][answer[f"private_{x}"]] for x in case["private_amounts"]}
        return {"choices": choices, "own_money_max_choices": sum(v == ("private" if int(x) > 4 else "group") for x, v in choices.items()),
                "choices_total": 4}
    action = case["options"][answer["choice"]]
    payoffs = disclosure_payoffs(case["cost"], case["reimbursed"], action == "release")
    return {"action": action, "release": action == "release", "earnings": payoffs,
            "own_money_max_choice": (action == "release") == (case["reimbursed"] or case["cost"] < 4)}


class ProbeModel(OpenAIModel):
    def _post(self, body, attempts=1):
        body["max_output_tokens"] = TOKENS
        self.request = body
        self.response = super()._post(body, attempts=attempts)
        return self.response


def run_one(root, stage, case, name, frame, fake, seed):
    role = 2 if case["family"] == "transcript" else 1
    messages = [{"role": "system", "content": fill(FRAMES[frame], role=role)}, {"role": "user", "content": case["prompt"]}]
    record = {"case_id": case["id"], "family": case["family"], "model": name, "frame": frame,
              "repeat": case["repeat"], "fake": fake, "messages": messages, "started": datetime.now(timezone.utc).isoformat()}
    model = FakeModel(seed) if fake else ProbeModel(name, EFFORT)
    started = time.monotonic()
    try:
        text, usage = model(messages, "incentive_probe", case["schema"])
        record.update(text=text, usage=usage, answer=json.loads(text))
        record["assessment"] = assess(case, record["answer"])
        record["status"] = "complete"
    except Exception as error:
        record.update(status="failed", error=f"{type(error).__name__}: {error}")
    record.update(elapsed_seconds=time.monotonic() - started, request=getattr(model, "request", None),
                  api_response=getattr(model, "response", None))
    path = root / stage / name / frame / (case["id"] + ".json")
    atomic(path, record)
    print(f"{stage} {name} {frame} {case['id']}: {record['status']}", flush=True)
    return record


def records(root, stage):
    return [json.loads(p.read_text()) for p in sorted((root / stage).glob("*/*/*.json"))]


def report(root):
    config = json.loads((root / "config.json").read_text())
    design = json.loads((root / "cases.json").read_text())
    summaries, sections = {}, []
    esc = html.escape
    for stage in ("diagnostics", "disclosure"):
        rows, rs = [], records(root, stage)
        expected = len(MODELS) * len(FRAMES) * len(design[stage])
        summary = {"attempted": len(rs), "planned": expected, "complete": sum(r['status'] == 'complete' for r in rs), "cells": []}
        for name in MODELS:
            for frame in FRAMES:
                complete = [r for r in rs if r["model"] == name and r["frame"] == frame and r["status"] == "complete"]
                groups = [(family, [r for r in complete if r["family"] == family]) for family in ("full-profile", "payment-calculation", "allocation", "transcript")] if stage == "diagnostics" else [
                    (f"£{cost}, {'reimbursed' if refund else 'unreimbursed'}", [r for r in complete if next(c for c in design[stage] if c['id'] == r['case_id'])['cost'] == cost and next(c for c in design[stage] if c['id'] == r['case_id'])['reimbursed'] == refund])
                    for cost in COSTS for refund in (False, True)]
                for cell, selected in groups:
                    a = [r["assessment"] for r in selected]
                    detail = {"model": name, "frame": frame, "cell": cell, "complete": len(a)}
                    if not a:
                        result = "Unavailable"
                    elif stage == "disclosure":
                        detail.update(released=sum(x["release"] for x in a), earnings=[x["earnings"] for x in a])
                        result = f"Release {detail['released']}/{len(a)}"
                    elif cell == "allocation":
                        detail.update(choices=[x["choices"] for x in a], own_money_max_choices=sum(x["own_money_max_choices"] for x in a), total=sum(x["choices_total"] for x in a))
                        result = f"Own-money maximum {detail['own_money_max_choices']}/{detail['total']} choices (descriptive)"
                    else:
                        detail.update(correct=sum(x["correct"] for x in a), total=sum(x["total"] for x in a), all_correct=sum(x["all_correct"] for x in a))
                        result = f"Correct components {detail['correct']}/{detail['total']}; all correct {detail['all_correct']}/{len(a)} calls"
                    summary["cells"].append(detail)
                    rows.append(f"<tr><td>{esc(name)}</td><td>{frame}</td><td>{esc(cell)}</td><td>{len(a)}/2</td><td>{esc(result)}</td></tr>")
        summary["failures"] = [{k: r[k] for k in ("model", "frame", "case_id", "error")} for r in rs if r["status"] != "complete"]
        summaries[stage] = summary
        sections.append(f"<section><h2>{'Standalone diagnostics' if stage == 'diagnostics' else 'Direct disclosure cost'}</h2><p>" 
                        f"{summary['complete']}/{len(rs)} saved attempts completed; {expected} planned. No failed call was replaced.</p>"
                        "<div class='scroll'><table><thead><tr><th>Model</th><th>Prompt</th><th>Case</th><th>Complete</th><th>Result</th></tr></thead><tbody>"
                        + "".join(rows) + "</tbody></table></div><h3>Failures</h3><pre>" + esc(json.dumps(summary["failures"], indent=2)) + "</pre></section>")
    usage = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    for stage in summaries:
        for r in records(root, stage):
            raw = (r.get("api_response") or {}).get("usage") or {}
            usage["input_tokens"] += raw.get("input_tokens", 0)
            usage["output_tokens"] += raw.get("output_tokens", 0)
            usage["reasoning_tokens"] += (raw.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
    summaries["usage"] = usage
    atomic(root / "summary.json", summaries)
    page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>OpenAI incentive diagnostics and disclosure costs</title><style>"
            "body{font:16px/1.6 system-ui,sans-serif;color:#14191c;background:#f5f7f7;margin:0}main{max-width:1100px;margin:auto;padding:40px 20px}"
            "h1,h2{font-family:Georgia,serif;line-height:1.2}h1{font-size:2.5rem}h2{margin-top:2.5rem}a{color:#1d5566}"
            ".scroll{overflow:auto}table{width:100%;border-collapse:collapse;background:white;font-size:.9rem}th,td{padding:10px;text-align:left;border:1px solid #dbe1e4}"
            "th{background:#e2edf0}pre{white-space:pre-wrap;overflow-wrap:anywhere}p{max-width:85ch}</style></head><body><main>"
            "<p>Exploratory pilot · 22 October 2026</p><h1>OpenAI incentive diagnostics and disclosure costs</h1>"
            + ("<p><strong>FAKE PIPELINE CHECK: not experimental evidence.</strong></p>" if config["fake"] else "")
            + "<p>Two independent calls per cell; high reasoning; fresh contexts; no quizzes or corrective feedback. Objective task checks and behavioral choices are reported separately. "
            "Allocation and release choices are descriptive, not tests of human fidelity. Missing responses are not coded as withholding.</p>"
            "<p><a href='config.json'>Configuration</a> · <a href='cases.json'>All prompts, schemas, and objective answer keys</a> · "
            "<a href='specification.md'>Fixed specification</a> · <a href='summary.json'>Machine-readable results</a></p>"
            + "".join(sections) + "<h2>Usage and limits</h2><pre>" + esc(json.dumps(usage, indent=2)) + "</pre>"
            "<p>Output tokens include reasoning. Usage can be unavailable for failed requests. Provider billing was not audited. "
            "Stated payments do not create real financial stakes for a model. The direct-cost task uses deterministic receivers and a fixed truthful report; "
            "it does not reproduce the original discussion or identify internal preferences. Two calls per cell do not support population inference.</p></main></body></html>")
    (root / "report.html").write_text(page)
    print(root / "report.html", flush=True)
    return summaries


def run(root, stage, fake=False):
    design = cases()
    sources = {name: HERE / name for name in ("incentive_diagnostics.py", "agent.py", "task.py", "manipulations.py", "instructions.md")}
    hashes = {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in sources.items()}
    if stage == "diagnostics":
        root.mkdir(parents=True, exist_ok=False)
        (root / "source").mkdir()
        for name, p in sources.items():
            (root / "source" / name).write_bytes(p.read_bytes())
        (root / "specification.md").write_bytes((HERE.parent / "INCENTIVE_DIAGNOSTICS.md").read_bytes())
        atomic(root / "config.json", {"created": datetime.now(timezone.utc).isoformat(), "models": MODELS,
            "frames": {name: fill(section, role=1) for name, section in FRAMES.items()}, "reasoning_effort": EFFORT,
            "max_output_tokens": TOKENS, "workers": WORKERS, "http_attempts": 1, "repetitions": 2, "fake": fake,
            "source_sha256": hashes, "specification_sha256": hashlib.sha256((root / "specification.md").read_bytes()).hexdigest(),
            "seed": 20261022, "sampling": "API defaults", "store": False})
        atomic(root / "cases.json", design)
    else:
        config = json.loads((root / "config.json").read_text())
        assert config["fake"] == fake and config["source_sha256"] == hashes, "Source or mode changed; preserve the cohort"
        assert len(records(root, "diagnostics")) == 32, "Finish and inspect diagnostics first"
        assert json.loads((root / "cases.json").read_text()) == design, "Design changed"
    (root / stage).mkdir(exist_ok=False)
    jobs = [(case, name, frame) for case in design[stage] for name in MODELS for frame in FRAMES]
    random.Random(20261022).shuffle(jobs)
    for name in MODELS:
        for frame in FRAMES:
            (root / stage / name / frame).mkdir(parents=True)
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = [pool.submit(run_one, root, stage, case, name, frame, fake, i) for i, (case, name, frame) in enumerate(jobs)]
        for future in as_completed(futures):
            future.result()
    return report(root)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=("diagnostics", "disclosure", "report"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fake", action="store_true")
    args = ap.parse_args()
    report(args.out) if args.stage == "report" else run(args.out, args.stage, args.fake)
