"""Run or report the fixed discussion prompt sensitivity screen (standard library only).

    python3 harness/sensitivity.py --out runs/sensitivity/prompt-screen
    python3 harness/sensitivity.py --report runs/sensitivity/prompt-screen
    python3 harness/sensitivity.py --code runs/sensitivity/prompt-screen

The protocol is in first-test/SENSITIVITY.md. Existing output directories are never reused.
"""

import argparse
import hashlib
import json
import statistics as st
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import manipulations as mp
import task
from agent import EFFORT, MODEL, FakeModel, OpenAIModel
from analysis import HUMAN_VOTES, PRICE_PER_M, bootstrap, ci_str
from code_transcripts import CUE_RUBRIC, RUBRIC, code_one
from runner import DISCUSSION_ROUNDS, HERE, PROMPT_VARIANTS, run_triad


def records(root):
    return [(p, json.loads(p.read_text())) for p in sorted(root.glob("*/discussion-*-[0-9][0-9][0-9].json"))]


def disclosure(r, coded, role, field="cues"):
    values = list(coded[str(role)][field].values())
    return values.count("shared") / len(values)


def report(root):
    config = json.loads((root / "config.json").read_text())
    recs = records(root)
    coding = json.loads((root / "coding.json").read_text()) if (root / "coding.json").exists() else {}
    cells = {(v, m): [(p, r) for p, r in recs if r["prompt_variant"] == v and r["manipulation"] == m and r["status"] == "complete"]
             for v in config["prompt_variants"] for m in config["manipulations"]}
    out = ["# Prompt sensitivity screen", "", f"Model: {config['model']}; reasoning: {config['reasoning_effort']}; side payment: £{config['discussion_side_gbp']}.",
           "", "Exploratory, independent triads. Intervals describe model-sampling variation, not human-population uncertainty. Human means are digitised from Figure 2.",
           "", "| Variant | Incentive | Complete | B votes [95% CI] | Human B votes | Paid agents voting target | Side payment earned |",
           "|---|---|---|---|---|---|---|"]
    if config["triads_per_cell"] < 10:
        out[4:4] = ["", f"Only {config['triads_per_cell']} triads per cell: intervals are highly discrete descriptive resampling summaries and do not support inferential conclusions."]
    out[4:4] = ["", f"Protocol: {config['protocol']}; initial private ranking retained; quiz {'included' if config['protocol'] == 'paper' else 'omitted'}."]
    out[4:4] = ["", "Final discussion delivery: " + ("complete public transcript supplied to every voter."
                if config.get("final_transcript_included", False) else "historical delivery; some final turns were not supplied to every voter.")]
    for (v, m), pairs in cells.items():
        rs = [r for _, r in pairs]
        if not rs:
            out.append(f"| {v} | {m} | 0 | — | {HUMAN_VOTES['discussion', m]:.2f} | — | — |")
            continue
        votes = [r["outcome"]["b_votes"] for r in rs]
        paid = [(r, role) for r in rs for role in task.ROLES if mp.target(m, role)]
        own = sum(r["ranking_after"][str(role)][0] == mp.target(m, role) for r, role in paid if r["ranking_after"][str(role)])
        earned = sum(r["outcome"]["side_gbp"][str(role)] > 0 for r, role in paid)
        out.append(f"| {v} | {m} | {len(rs)}/{config['triads_per_cell']} | {st.mean(votes):.2f} [{ci_str(*bootstrap([votes], st.mean))}] | "
                   f"{HUMAN_VOTES['discussion', m]:.2f} | {f'{own}/{len(paid)}' if paid else '—'} | {f'{earned}/{len(paid)}' if paid else '—'} |")
    if coding:
        out += ["", "## Cue disclosure (model-coded; audit required)", "", "Fractions of each participant's nine own cues explicitly and correctly stated. Rows show paid roles, or all roles in control; the contrasts below match roles. Aggregated scores count as undisclosed cues, so this measures explicit reporting rather than all information a listener could infer. A 'misstated' code also includes describing a held cue as unknown; it does not establish a lie.",
                "", "| Variant | Incentive | Roles | First-round shared | End shared | End misstated | End withheld |",
                "|---|---|---|---|---|---|---|"]
        for (v, m), pairs in cells.items():
            selected = [(r, coding[str(p.relative_to(root))], role) for p, r in pairs if str(p.relative_to(root)) in coding
                        for role in task.ROLES if str(role) in coding[str(p.relative_to(root))] and (m == "control" or mp.target(m, role))]
            if not selected:
                continue
            values = [x for _, c, role in selected for x in c[str(role)]["cues"].values()]
            first = st.mean(disclosure(r, c, role, "cues_first_round") for r, c, role in selected)
            out.append(f"| {v} | {m} | {len(selected)} | {first:.1%} | " + " | ".join(f"{values.count(x) / len(values):.1%}" for x in ("shared", "misstated", "withheld")) + " |")
        out += ["", "## Disclosure response to conflicting incentives", "", "Treatment minus control, averaging participant disclosure within each triad before bootstrapping. Weak-buy uses role 1 in both cells; strong-buy uses all roles. Negative values indicate less disclosure under conflict.",
                "", "| Variant | Contrast | First-round difference [95% CI] | End difference [95% CI] |", "|---|---|---|---|"]
        effect_groups = {}
        for v in config["prompt_variants"]:
            for m in ("weak-buy", "strong-buy"):
                roles = [role for role in task.ROLES if mp.target(m, role)]
                estimates = []
                for field in ("cues_first_round", "cues"):
                    groups = [[st.mean(disclosure(r, coding[str(p.relative_to(root))], role, field) for role in roles)
                               for p, r in cells[v, cell] if all(str(role) in coding.get(str(p.relative_to(root)), {}) for role in roles)] for cell in (m, "control")]
                    effect_groups[v, m, field] = groups
                    if all(groups):
                        diff = lambda a, b: st.mean(a) - st.mean(b)
                        lo, hi = bootstrap(groups, diff)
                        estimates.append(f"{diff(*groups):+.1%} [{lo:+.1%} to {hi:+.1%}]")
                    else:
                        estimates.append("—")
                out.append(f"| {v} | {m} − control | " + " | ".join(estimates) + " |")
        if "baseline" in config["prompt_variants"]:
            out += ["", "## Change in end-disclosure response relative to baseline wording", "",
                    "Difference in treatment-minus-control effects. Negative values indicate a larger disclosure reduction under the alternative wording. Exploratory intervals are not adjusted for multiple comparisons.",
                    "", "| Variant | Incentive | Change [95% CI] |", "|---|---|---|"]
            for v in config["prompt_variants"]:
                if v == "baseline":
                    continue
                for m in ("weak-buy", "strong-buy"):
                    groups = effect_groups[v, m, "cues"] + effect_groups["baseline", m, "cues"]
                    if all(groups):
                        diff = lambda a, b, c, d: st.mean(a) - st.mean(b) - st.mean(c) + st.mean(d)
                        lo, hi = bootstrap(groups, diff)
                        out.append(f"| {v} | {m} | {diff(*groups):+.1%} [{lo:+.1%} to {hi:+.1%}] |")
    else:
        out += ["", "Cue coding has not been run. Vote outcomes alone do not establish disclosure sensitivity."]
    out += ["", "## Failures and usage", ""]
    failures = sum(r["status"] != "complete" for _, r in recs)
    usage = {k: sum(a["usage"][k] for _, r in recs for a in r["agents"].values()) for k in ("calls", "input_tokens", "cached_tokens", "output_tokens")}
    out.append(f"Failed triads: {failures}/{len(recs)}. Participant calls: {usage['calls']}; usage: {json.dumps(usage)}.")
    if config["model"] == MODEL:
        cost = ((usage["input_tokens"] - usage["cached_tokens"]) * PRICE_PER_M["input"] + usage["cached_tokens"] * PRICE_PER_M["cached"] + usage["output_tokens"] * PRICE_PER_M["output"]) / 1e6
        out.append(f"Estimated participant cost at the harness's recorded rates: ${cost:.2f}; excludes coding.")
    if coding:
        uses = [u for roles in coding.values() for result in roles.values() for u in result["usage"]]
        out.append(f"Coding: {len(uses)} calls, {sum(u['input_tokens'] for u in uses)} input tokens, {sum(u['output_tokens'] for u in uses)} output tokens.")
        coding_config = root / "coding-config.json"
        if coding_config.exists() and json.loads(coding_config.read_text())["model"] == MODEL:
            coding_cost = sum((u["input_tokens"] - u["cached_tokens"]) * PRICE_PER_M["input"] + u["cached_tokens"] * PRICE_PER_M["cached"]
                              + u["output_tokens"] * PRICE_PER_M["output"] for u in uses) / 1e6
            out.append(f"Estimated coding cost at the same rates: ${coding_cost:.2f}.")
    out += ["", "Interpretation: prompt sensitivity tests the measurement setup. A larger incentive effect is not by itself evidence of closer human fidelity. The simulation arm changes both role framing and the explicit payoff-maximisation instruction. Neutral-final changes arrive after discussion and therefore cannot cause earlier disclosure differences.", ""]
    path = root / "report.md"
    path.write_text("\n".join(out))
    print(path, flush=True)


def run(root, model, triads=2, workers=20, variants=PROMPT_VARIANTS, seed=20261021, protocol="no-quiz"):
    root.mkdir(parents=True, exist_ok=False)
    mp.DISCUSSION_SIDE_GBP = 5
    config = {"created": datetime.now(timezone.utc).isoformat(), "model": model.model, "reasoning_effort": model.effort,
              "prompt_variants": list(variants), "manipulations": list(mp.MANIPULATIONS), "triads_per_cell": triads,
              "discussion_side_gbp": 5, "discussion_rounds": DISCUSSION_ROUNDS, "protocol": protocol, "seed": seed,
              "final_transcript_included": True,
              "workers": workers, "instructions": (HERE / "instructions.md").read_text(),
              "model_settings": getattr(model, "settings", {}),
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob("*.py")}}
    (root / "config.json").write_text(json.dumps(config, indent=2))
    (root / "source").mkdir()
    for p in HERE.glob("*.py"):
        (root / "source" / p.name).write_bytes(p.read_bytes())
    for v in variants:
        (root / v).mkdir()
    jobs = [(v, m, i) for v in variants for m in mp.MANIPULATIONS for i in range(1, triads + 1)]
    started = time.time()
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(run_triad, "discussion", i, seed * 10000 + j, model, root / v, m, protocol, v): (v, m, i)
                   for j, (v, m, i) in enumerate(jobs)}
        for future in as_completed(futures):
            _, status, outcome = future.result()
            print(f"{futures[future]}: {status} {outcome}", flush=True)
    print(f"Finished in {time.time() - started:.0f}s", flush=True)
    report(root)


def code(root, workers=40, fake=False):
    target = root / "coding.json"
    coding = json.loads(target.read_text()) if target.exists() else {}
    model = FakeModel(0) if fake else OpenAIModel()
    config_path = root / "coding-config.json"
    if config_path.exists() and json.loads(config_path.read_text())["model"] != model.model:
        raise ValueError("Existing coding uses a different model; preserve it and use a new run directory.")
    config_path.write_text(json.dumps({"model": model.model, "reasoning_effort": model.effort, "first_round": True,
                                      "workers": workers, "cue_rubric": CUE_RUBRIC, "behavior_rubric": RUBRIC}, indent=2))
    recs = [(p, r) for p, r in records(root) if r["status"] == "complete"]
    jobs = [(str(p.relative_to(root)), r, role) for p, r in recs for role in task.ROLES
            if str(role) not in coding.get(str(p.relative_to(root)), {})]
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(code_one, model, r, role, first_round=True): (name, role) for name, r, role in jobs}
        for future in as_completed(futures):
            name, role = futures[future]
            coding.setdefault(name, {})[str(role)] = future.result()
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(coding, indent=1, ensure_ascii=False))
            temporary.replace(target)
            print(f"coded {name} role {role}", flush=True)
    report(root)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--report", type=Path)
    mode.add_argument("--code", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--triads", type=int, default=2)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--variants", nargs="+", choices=PROMPT_VARIANTS, default=list(PROMPT_VARIANTS))
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--protocol", choices=("no-quiz", "paper"), default="no-quiz")
    ap.add_argument("--endpoint-config", type=Path, help="Public Modal endpoint manifest: model name, URL, and checkpoint/settings")
    ap.add_argument("--proxy-token-file", type=Path, help="Private JSON from Modal proxy-token creation; never copied into run records")
    args = ap.parse_args()
    if args.triads < 1 or args.workers < 1:
        ap.error("triads and workers must be positive")
    if args.endpoint_config and (args.fake or not args.proxy_token_file):
        ap.error("endpoint runs require --proxy-token-file and cannot use --fake")
    if args.report:
        report(args.report)
    elif args.code:
        code(args.code, args.workers, args.fake)
    else:
        root = args.out or HERE.parent / "runs" / "sensitivity" / datetime.now().strftime("%Y%m%d-%H%M%S")
        if args.endpoint_config:
            from vllm_model import VLLMModel

            settings = json.loads(args.endpoint_config.read_text())
            credential = json.loads(args.proxy_token_file.read_text())
            model = VLLMModel(settings["model"], settings, settings["url"].rstrip("/") + "/v1/chat/completions", credential["Authorization"])
        else:
            model = FakeModel(20261021) if args.fake else OpenAIModel()
        run(root, model, args.triads, args.workers, args.variants, protocol=args.protocol)
