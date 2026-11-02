"""Chat coder: game claims and challenges in every chat round of a run, written to <run>/coding.json.

Free chat (CH/S-D, CH/A-D, CH-MC) is coded by a separate model call per round with the fixed rubric below; the
coder sees the transcript but not the drawn game, and truth and lies are computed later in code against the draw.
EC-MC's preset messages are coded by rule. Coding never feeds back into participant contexts.

Usage (from third-test/):
    python3 harness/code_chat.py runs/<run>            # code every round not yet coded (resumes)
    python3 harness/code_chat.py runs/<run> --review   # print every coded lie and a seeded 10% of rounds for hand checks
"""

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agent import InvalidReply, ModelError, OpenAIModel, obj

RUBRIC = """You code chat transcripts from an economics experiment. Three players, A, F and C, are in a group. In each period the computer draws one of five games, Game 1 to Game 5. F and C are told which game was drawn; A is not. F chooses a row (f1 to f5) and C a column (c1 to c5), or A chooses both, depending on the treatment. The players may chat before the choices.

List every game claim and every challenge in the transcript. Messages are numbered in square brackets.

A game claim is a message by F or C that states or implies which game was drawn in the current period. It can be direct ("It is game 4", "we are in Game 2", "Game 3 was selected; choose f3, c3") or implied by evaluating the current choices in one named game, which tells the reader that this game was drawn ("f3/c3 gives us 36 each in Game 2", "in Game 5 it gives A 64", "f1 and c1 are best responses in Game 1"). Record the game number. Code at most one claim per message; a message that names a game and also proposes actions is a claim.
Not a game claim: proposals of actions alone ("let's play f2 and c2", "choose 3"); comparisons across games or averages over games ("f3/c3 gives A at least 64 in every game"); explicitly conditional or hypothetical statements ("if it were Game 4, ..."); statements about earlier periods; questions; anything written by A, who does not know the game.

A challenge is a message that explicitly disputes or corrects another player's claim about which game was drawn: "That's not true, it is Game 2", "C is lying", "No, it's not game 5". Agreement, doubts about intentions, or disputes about actions are not challenges.

Return the message numbers. Return empty lists if there are none."""

TREATMENTS = ("CH/S-D", "CH/A-D", "CH-MC", "EC-MC")


def messages(rnd):
    """The round's written messages, numbered from 1."""
    return [m for m in rnd["chat"] if m["message"]]


def transcript(msgs):
    return "\n".join(f"[{i}] (turn {m['turn']}) {m['speaker']}: {m['message']}" for i, m in enumerate(msgs, 1))


def code_presets(msgs):
    """EC-MC: the preset buttons code themselves."""
    claims = [{"index": i, "game": int(m["message"][-1])} for i, m in enumerate(msgs, 1) if m["message"].startswith("It is game")]
    return {"claims": claims, "challenges": [i for i, m in enumerate(msgs, 1) if m["message"].endswith("is lying")]}


def code_free(model, msgs):
    if not msgs:
        return {"claims": [], "challenges": []}, {}
    idx = list(range(1, len(msgs) + 1))
    schema = obj({"claims": {"type": "array", "items": obj({"index": {"type": "integer", "enum": idx}, "game": {"type": "integer", "enum": [1, 2, 3, 4, 5]}})},
                  "challenges": {"type": "array", "items": {"type": "integer", "enum": idx}}})
    prompt = [{"role": "system", "content": RUBRIC}, {"role": "user", "content": transcript(msgs)}]
    for attempt in range(2):
        try:
            text, usage = model(prompt, "chat_coding", schema)
            out = json.loads(text)
            break
        except (InvalidReply, json.JSONDecodeError) as e:
            if attempt:
                raise ModelError(f"coder failed twice: {e}") from e
    by_index = {c["index"]: c["game"] for c in out["claims"]}  # one claim per message
    return {"claims": [{"index": i, "game": g} for i, g in sorted(by_index.items())], "challenges": sorted(set(out["challenges"]))}, usage


def located(coded, msgs):
    """Attach speaker and turn to each coded message, so the analysis needs no transcript."""
    at = lambda i: {"index": i, "speaker": msgs[i - 1]["speaker"], "turn": msgs[i - 1]["turn"]}
    return {"claims": [at(c["index"]) | {"game": c["game"]} for c in coded["claims"]],
            "challenges": [at(i) for i in coded["challenges"]], "messages": len(msgs)}


def records(run):
    for p in sorted(run.glob("*-[0-9][0-9].json")):
        rec = json.loads(p.read_text())
        if rec["treatment"] in TREATMENTS and rec["status"] == "complete":
            yield rec


def code_run(run, workers):
    out_path = run / "coding.json"
    coding = json.loads(out_path.read_text()) if out_path.exists() else {"rubric": RUBRIC, "rounds": {}}
    assert coding["rubric"] == RUBRIC, f"{out_path} was coded with another rubric"
    model = None
    jobs = []
    for rec in records(run):
        for rnd in rec["rounds"]:
            key = f"{rec['treatment']}|{rec['group']}|{rnd['round']}"
            if key in coding["rounds"]:
                continue
            msgs = messages(rnd)
            if rec["treatment"] == "EC-MC":
                coding["rounds"][key] = located(code_presets(msgs), msgs) | {"coder": "rule"}
            else:
                jobs.append((key, msgs))
    if jobs:
        model = OpenAIModel()
        coding |= {"model": model.model, "reasoning_effort": model.effort}
        with ThreadPoolExecutor(workers) as pool:
            futures = {pool.submit(code_free, model, msgs): (key, msgs) for key, msgs in jobs}
            for n, f in enumerate(as_completed(futures), 1):
                key, msgs = futures[f]
                coded, usage = f.result()
                coding["rounds"][key] = located(coded, msgs) | {"coder": "model", "usage": usage}
                if n % 100 == 0:
                    out_path.write_text(json.dumps(coding, indent=1))
                    print(f"  coded {n}/{len(jobs)}", flush=True)
    out_path.write_text(json.dumps(coding, indent=1))
    print(f"{run}: {len(coding['rounds'])} rounds coded ({len(jobs)} by model in this call)")


def review(run, share=0.10, seed=20261026):
    """Every coded lie, then a seeded random share of all coded rounds, each with transcript and codes."""
    coding = json.loads((run / "coding.json").read_text())["rounds"]
    rounds = {f"{r['treatment']}|{r['group']}|{x['round']}": x for r in records(run) for x in r["rounds"]}
    lies = [k for k, c in coding.items() if any(cl["game"] != rounds[k]["game"] for cl in c["claims"])]
    sample = sorted(random.Random(seed).sample(sorted(coding), round(share * len(coding))))
    for title, keys in (("CODED LIES", lies), (f"RANDOM {share:.0%} OF ROUNDS", sample)):
        print(f"\n######## {title}: {len(keys)} rounds")
        for k in keys:
            x, c = rounds[k], coding[k]
            print(f"\n=== {k} (drawn game {x['game']}) claims {[(cl['index'], cl['speaker'], cl['game']) for cl in c['claims']]} "
                  f"challenges {[ch['index'] for ch in c['challenges']]}")
            print(transcript(messages(x)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--workers", type=int, default=25)
    args = ap.parse_args()
    for run in args.runs:
        review(run) if args.review else code_run(run, args.workers)
