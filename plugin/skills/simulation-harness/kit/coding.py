"""Coder: codes units of text with a fixed rubric in separate model calls (standard library only).

Kit file of the synthetic-organisations plugin, generalised from the transcript coder of the Brandts & Cooper replication. The coder sees a
unit's text, never the state it is checked against: truth and errors are computed in code afterwards. coding.json
can be resumed and refuses a changed rubric or schema. Hand checks (GUIDE-LLM item E.1): review() prints every
positive unit and a seeded share of all units; the researcher writes a verdict per checked unit into
hand_checks.json as {"<key>": true | false}; agreement() reports the share confirmed.
"""

import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import agent


def code_units(model, units, rubric, schema, out_path, workers=10):
    """units: {key: text}; schema: the reply properties for one unit. Codes every unit not yet in out_path."""
    out_path = Path(out_path)
    coding = json.loads(out_path.read_text()) if out_path.exists() else \
        {"rubric": rubric, "schema": schema, "model": model.describe(), "units": {}}
    if (coding["rubric"], coding["schema"]) != (rubric, schema):
        raise SystemExit(f"{out_path} was coded with another rubric or schema; write to a new file.")

    def one(key):
        a = agent.Agent("coder", model, rubric)
        try:
            return key, {"coded": a.ask(units[key], "coding", agent.obj(schema)), "calls": a.calls}
        except (agent.GroupFailed, agent.ModelError) as e:
            return key, {"error": str(e), "calls": a.calls}

    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(one, k) for k in units if k not in coding["units"]]
        for n, f in enumerate(as_completed(futures), 1):
            key, result = f.result()
            coding["units"][key] = result
            if n % 100 == 0:
                out_path.write_text(json.dumps(coding, indent=1, ensure_ascii=False))
    out_path.write_text(json.dumps(coding, indent=1, ensure_ascii=False))
    return coding


def review(out_path, units, positive, share=0.10, seed=1):
    """Print every unit whose coding is positive (positive(coded) -> bool) and a seeded share of all units, each with
    its text, for hand checks. Returns (positive keys, sampled keys)."""
    coding = json.loads(Path(out_path).read_text())["units"]
    pos = sorted(k for k, c in coding.items() if "coded" in c and positive(c["coded"]))
    sample = sorted(random.Random(seed).sample(sorted(coding), round(share * len(coding))))
    for title, keys in ((f"POSITIVE ({len(pos)})", pos), (f"RANDOM {share:.0%} ({len(sample)})", sample)):
        print(f"\n######## {title}")
        for k in keys:
            print(f"\n=== {k}: {coding[k].get('coded', coding[k].get('error'))}\n{units[k]}")
    return pos, sample


def agreement(hand_path):
    """(share of hand-checked units whose coding was confirmed, number checked)."""
    checks = json.loads(Path(hand_path).read_text())
    return (sum(bool(v) for v in checks.values()) / len(checks) if checks else float("nan")), len(checks)
