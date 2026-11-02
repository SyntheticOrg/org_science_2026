"""Runner: one group of F, C and A plays 18 periods of one treatment; one JSON record per group.

Usage (from third-test/):
    python3 harness/runner.py --fake --treatments all             # pipeline check, no API calls
    python3 harness/runner.py --notes --groups 3 --treatments NC-D SC-MC CH-MC     # pilot with private notes
    python3 harness/runner.py --groups 27 --workers 27                              # experiment 1 (frozen settings)

Group g plays game sequence ((g - 1) mod 9) + 1, so group g + 27 replaces an incomplete group g with the same draws
(e.g. --first-group 32 --groups 1 for group 5); the incomplete record stays in place.
Rerunning into an existing --out directory resumes it: groups that have a record are skipped, and the
settings must match the directory's config.json.
"""

import argparse
import json
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import game
from agent import Agent, FakeModel, GroupFailed, ModelError, OpenAIModel, enum, fill, nullable, obj

HERE = Path(__file__).resolve().parent
TREATMENTS = ("NC-D", "SC/S-D", "SC/A-D", "SC-MC", "CH/S-D", "CH/A-D", "CH-MC", "EC-MC")
MAIN = TREATMENTS[:7]
TURNS = 8  # chat budget for all chat treatments (APPROACH.md, Decisions 3)
A_DECIDES = {"SC-MC", "CH-MC", "EC-MC"}
A_ACTS = A_DECIDES | {"SC/A-D", "CH/A-D"}  # A is a model only here; elsewhere A is passive and makes no calls
WRITERS = {"CH/S-D": ("F", "C"), "CH/A-D": ("A", "F", "C"), "CH-MC": ("A", "F", "C"), "EC-MC": ("A", "F", "C")}
READERS = {"CH/S-D": ("A", "F", "C")} | {t: w for t, w in WRITERS.items() if t != "CH/S-D"}  # A reads in CH/S-D (p. 1954)
PRESET = {  # EC-MC buttons, from the English instructions and the z-Tree program
    "A": ("What game is it?", "Please, tell me the truth"),
    "F": tuple(f"It is game {g}" for g in game.GAMES) + ("I am telling the truth", "C is telling the truth", "C is lying"),
    "C": tuple(f"It is game {g}" for g in game.GAMES) + ("I am telling the truth", "F is telling the truth", "F is lying"),
}
ROWS, COLS = [f"f{i}" for i in game.ACTIONS], [f"c{i}" for i in game.ACTIONS]
CELL = {"row": enum(ROWS), "column": enum(COLS)}


def transcript(log, viewer):
    lines = [f"  {m['speaker']}{' (you)' if m['speaker'] == viewer else ''}: {m['message']}" for m in log if m["message"]]
    return "\n".join(lines) or "  (no messages yet)"


def record_path(out_dir, treatment, group):
    return out_dir / f"{treatment.replace('/', '-')}-{group:02d}.json"


def run_group(treatment, group, seed, model, out_dir, notes=False, turns=TURNS):
    rng = random.Random(f"{seed}-{treatment}-{group}")
    pos = game.position(group)
    agents = {r: Agent(r, model) for r in (("F", "C", "A") if treatment in A_ACTS else ("F", "C"))}
    intro = "\n\n".join((fill("opening", tables=game.tables_text()),
                         fill(treatment, turns=turns, chat_rules=fill("chat_rules", turns=turns)), fill("closing")))
    rec = {"treatment": treatment, "group": group, "position": pos, "games": game.SEQUENCES[pos], "seed": seed,
           "model": model.model, "reasoning_effort": model.effort, "notes": notes, "turns": turns,
           "simulated": list(agents), "chat_readers": list(READERS.get(treatment, ())),
           "started": datetime.now(timezone.utc).isoformat(), "status": "running", "rounds": []}
    try:
        for r in range(1, game.ROUNDS + 1):
            block, period, g = (r - 1) // game.BLOCK + 1, (r - 1) % game.BLOCK + 1, game.SEQUENCES[pos][r - 1]
            prefix = {}  # opened with the period's first prompt to each player
            for role in agents:
                parts = [intro] if r == 1 else [fill("block_screen")] if r == game.BLOCK + 1 else []
                parts.append(fill("header_uninformed", block=block, period=period) if role == "A"
                             else fill("header_informed", block=block, period=period, game=g))
                prefix[role] = "\n\n".join(parts)
            actions = []

            def ask(role, text, kind, props):
                p = prefix.pop(role, None)
                prompt = "\n\n".join(x for x in (p, text, fill("note") if notes else None) if x)
                answer = agents[role].ask(prompt, kind, obj(props, note=notes))
                actions.append({"role": role, "kind": kind, **answer})
                return answer

            rnd = {"round": r, "block": block, "period": period, "game": g, "actions": actions}
            context = ""  # what F and C (or A) see on the decision screen besides the header
            if treatment == "SC/S-D":
                rnd["suggestions"], lines = [], []
                for k in (1, 2, 3):
                    seen = "Suggestions so far:\n" + "\n".join(lines) if lines else ""
                    s = {role: ask(role, "\n\n".join(x for x in (seen, fill("ask_suggestion", k=k)) if x), "suggestion", CELL)
                         for role in ("F", "C")}
                    rnd["suggestions"].append({role: [a["row"], a["column"]] for role, a in s.items()})
                    lines.append(f"{k}. F suggested {s['F']['row']} and {s['F']['column']}; C suggested {s['C']['row']} and {s['C']['column']}.")
                context = "Suggestions this period:\n" + "\n".join(lines)
            elif treatment == "SC/A-D":
                a = ask("A", fill("ask_advice"), "advice", {f"game_{x}": obj(CELL) for x in game.GAMES})
                rnd["advice"] = {x: [a[f"game_{x}"]["row"], a[f"game_{x}"]["column"]] for x in game.GAMES}
                context = "Player A's suggestions:\n" + "\n".join(f"Game {x}: {v[0]} and {v[1]}" for x, v in rnd["advice"].items())
            elif treatment == "SC-MC":
                rep = {role: ask(role, fill("ask_report"), "report", {"game": {"type": "integer", "enum": list(game.GAMES)}})["game"]
                       for role in ("F", "C")}
                rnd["reports"] = rep
                context = f"F says the selected game is Game {rep['F']}. C says the selected game is Game {rep['C']}."
            elif treatment in WRITERS:
                log, rnd["chat_ended"] = [], "budget"
                for t in range(1, turns + 1):
                    order = list(WRITERS[treatment])
                    rng.shuffle(order)
                    wrote = False
                    for role in order:
                        preset = treatment == "EC-MC"
                        text = fill("ask_preset" if preset else "ask_chat", turn=t, turns=turns, transcript=transcript(log, role))
                        msg = ask(role, text, "chat", {"message": nullable(enum(PRESET[role]) if preset else {"type": "string"})})["message"]
                        msg = (msg or "").strip() or None
                        log.append({"turn": t, "speaker": role, "message": msg})
                        wrote |= msg is not None
                    if not wrote:
                        rnd["chat_ended"] = "silence"
                        break
                rnd["chat"] = log
                context = None  # filled per viewer below

            def screen(role, ask_section):
                c = fill("chat_ended", transcript=transcript(rnd["chat"], role)) if "chat" in rnd else context
                return "\n\n".join(x for x in (c, fill(ask_section)) if x)

            if treatment in A_DECIDES:
                a = ask("A", screen("A", "ask_cell"), "choice", CELL)
                row, col = a["row"], a["column"]
                choices = f"A chose row {row} and column {col}."
                if treatment == "SC-MC":
                    choices = f"F reported Game {rnd['reports']['F']} and C reported Game {rnd['reports']['C']}. " + choices
            else:
                row = ask("F", screen("F", "ask_row"), "choice", {"row": enum(ROWS)})["row"]
                col = ask("C", screen("C", "ask_column"), "choice", {"column": enum(COLS)})["column"]
                choices = f"F chose row {row} and C chose column {col}."
            i, j = int(row[1]), int(col[1])
            pf, pc, pa = game.payoffs(g, i, j)
            rnd.update(row=i, column=j, payoffs={"F": pf, "C": pc, "A": pa}, outcome=game.outcome(g, i, j))
            result = fill("result", block=block, period=period, game=g, choices=choices, pay_f=pf, pay_c=pc, pay_a=pa)
            for agent in agents.values():
                agent.tell(result)
            rec["rounds"].append(rnd)
        totals = {role: sum(x["payoffs"][role] for x in rec["rounds"]) for role in ("F", "C", "A")}
        rec["earnings"] = {role: {"ecu": e, "euros": round(5 + 0.02 * e, 2)} for role, e in totals.items()}
        rec["status"] = "complete"
    except (GroupFailed, ModelError) as e:
        rec.update(status="incomplete", error=str(e), traceback=traceback.format_exc())
    rec["finished"] = datetime.now(timezone.utc).isoformat()
    rec["agents"] = {role: {"messages": a.messages, "usage": a.usage, "failures": a.failures} for role, a in agents.items()}
    path = record_path(out_dir, treatment, group)
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return path, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--treatments", nargs="+", default=list(MAIN), help="treatment codes, or 'all' for all eight")
    ap.add_argument("--groups", type=int, default=1, help="groups per treatment")
    ap.add_argument("--first-group", type=int, default=1, help="number of the first group (to rerun or add groups)")
    ap.add_argument("--workers", type=int, default=8, help="groups run in parallel")
    ap.add_argument("--seed", type=int, default=20261023)
    ap.add_argument("--turns", type=int, default=TURNS, help="chat turns per period")
    ap.add_argument("--notes", action="store_true", help="a private note on the reason with every reply (pilots only)")
    ap.add_argument("--model", default=None, help="override the model (default: agent.MODEL)")
    ap.add_argument("--effort", default=None, help="override the reasoning effort (default: agent.EFFORT)")
    ap.add_argument("--fake", action="store_true", help="random schema-valid replies, no API calls")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    treatments = list(TREATMENTS) if args.treatments == ["all"] else args.treatments
    assert set(treatments) <= set(TREATMENTS), f"unknown treatment in {treatments}"

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + ("-fake" if args.fake else "")
    out_dir = args.out or HERE.parent / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    model = None if args.fake else OpenAIModel(**{k: v for k, v in (("model", args.model), ("effort", args.effort)) if v})
    jobs = [(t, g) for t in treatments for g in range(args.first_group, args.first_group + args.groups)]
    config = {
        "run_id": run_id, "model": model.model if model else "fake", "reasoning_effort": model.effort if model else None,
        "treatments": treatments, "groups": [g for _, g in jobs[:args.groups]], "seed": args.seed, "turns": args.turns,
        "notes": args.notes, "instructions": (HERE / "instructions.md").read_text(),
    }
    if (out_dir / "config.json").exists():  # resume: never mix settings, never overwrite a record
        old = json.loads((out_dir / "config.json").read_text())
        changed = [k for k in ("model", "reasoning_effort", "seed", "turns", "notes", "instructions") if old[k] != config[k]]
        assert not changed, f"{out_dir} was run with other settings: {changed}"
        jobs = [(t, g) for t, g in jobs if not record_path(out_dir, t, g).exists()]
        print(f"resuming {out_dir}: {len(jobs)} groups without a record", flush=True)
    else:
        (out_dir / "config.json").write_text(json.dumps(config, indent=1))

    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(run_group, t, g, args.seed, model or FakeModel(f"{args.seed}-{t}-{g}"), out_dir,
                               args.notes, args.turns) for t, g in jobs]
        for f in as_completed(futures):
            path, rec = f.result()
            calls = sum(a["usage"]["calls"] for a in rec["agents"].values())
            print(f"{path.name}: {rec['status']}, {calls} calls"
                  + (f", A earned {rec['earnings']['A']['ecu']} ECU" if rec["status"] == "complete" else f": {rec['error']}"), flush=True)
    print(f"done in {time.time() - t0:.0f}s -> {out_dir}")


if __name__ == "__main__":
    main()
