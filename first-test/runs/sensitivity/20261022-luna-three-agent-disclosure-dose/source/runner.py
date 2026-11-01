"""Experiment runner: fresh triads, quiz, rankings, discussion or market, one JSON record per triad.

Usage (from first-test/):
    python3 harness/runner.py --triads 3 --workers 6                           # experiment 1 controls, real API
    python3 harness/runner.py --triads 3 --manipulations weak-buy weak-sell strong-buy strong-sell   # experiment 2
    python3 harness/runner.py --triads 1 --fake                                # pipeline check, no API calls
"""

import argparse
import json
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import manipulations as mp
import task
from agent import EFFORT, MODEL, MARKET_ACTION, MESSAGE, RANKING, Agent, FakeModel, ModelError, OpenAIModel, fill, parse_quiz, quiz_schema
from market import InvalidAction, Market

HERE = Path(__file__).resolve().parent
CONDITIONS = ("discussion", "market")
PROMPT_VARIANTS = ("baseline", "privacy", "simulation", "neutral-final", "combined")
DISCUSSION_ROUNDS = 5
PERIODS, MARKET_ROUNDS = 10, 10


# --- shared stages -----------------------------------------------------------------

def briefing(condition, pay_key, protocol="paper", prompt_variant="baseline"):
    """Condition instructions, plus the private payment rule for a paid agent."""
    text = fill(f"{condition}_instructions" + ("_open" if protocol == "open" else ""), task=fill("task"))
    if protocol == "no-quiz":
        text = text.replace("After these instructions you will answer a short quiz. You will then receive your information",
                            "After these instructions you will receive your information")
    if prompt_variant in ("privacy", "combined"):
        text += "\n\n" + fill("disclosure_discretion")
    if pay_key:
        text += "\n\n" + fill("payment_private", rule=fill(f"rule_{pay_key}", **mp.pay_values()))
    return text


def run_quiz(agent, condition, pay_key=None, prompt_variant="baseline"):
    items = parse_quiz(f"quiz_{condition}") + (parse_quiz(f"quiz_pay_{pay_key}", **mp.pay_values()) if pay_key else [])
    schema = quiz_schema(items)
    questions = "\n".join(f"{i + 1}. {it['question']}" for i, it in enumerate(items))
    prompt = briefing(condition, pay_key, prompt_variant=prompt_variant) + "\n\n" + fill("quiz_intro") + "\n\n" + questions
    attempts = []
    for attempt in range(2):
        answers = agent.ask(prompt, "quiz", schema)
        wrong = [i for i, it in enumerate(items) if answers[f"q{i + 1}"] != it["answer"]]
        attempts.append({"answers": answers, "incorrect": [i + 1 for i in wrong]})
        if not wrong:
            break
        if attempt == 0:
            listing = "\n".join(f"{i + 1}. {items[i]['question']}\n   {items[i]['explanation']}" for i in wrong)
            prompt = fill("quiz_retry", incorrect_items=listing) + "\n\n" + questions
        else:
            agent.failures.append({"kind": "quiz_failed", "incorrect": [i + 1 for i in wrong]})
    return attempts


def rank(agent, prompt, transcript=None):
    if transcript is not None:
        lines = "\n".join(
            f"Participant {m['speaker']}{' (you)' if m['speaker'] == agent.role else ''}: {m['message']}" for m in transcript
        )
        prompt = f"Complete public discussion transcript:\n\n{lines}\n\n{prompt}"
    for attempt in range(2):
        r = agent.ask(prompt, "ranking", RANKING)
        ranking = [r["first"], r["second"], r["third"]]
        if task.is_ranking(ranking):
            return ranking
        agent.failures.append({"kind": "invalid_ranking", "ranking": ranking})
        prompt = fill("ranking_retry")
    return None


# --- institutions ------------------------------------------------------------------

def reminder(pay_key):
    """Prefix for a paid agent's turn prompts; empty for unpaid agents, whose prompts stay identical to the control."""
    return fill("payment_reminder", rule=fill(f"rule_{pay_key}", **mp.pay_values())) + "\n\n" if pay_key else ""


def run_discussion(agents, pay_keys, intro=None):
    """intro: per-role text placed before the agent's first turn (open protocol)."""
    transcript, intro = [], dict(intro or {})
    for rnd in range(1, DISCUSSION_ROUNDS + 1):
        start = (rnd - 1) % 3
        for role in [task.ROLES[(start + i) % 3] for i in range(3)]:
            lines = "\n".join(
                f"Participant {m['speaker']}{' (you)' if m['speaker'] == role else ''}: {m['message']}" for m in transcript
            ) or "(none yet)"
            prompt = intro.pop(role, "") + reminder(pay_keys[role]) + fill("discussion_turn", round=rnd, transcript=lines)
            reply = agents[role].ask(prompt, "message", MESSAGE)
            transcript.append({"round": rnd, "speaker": role, "message": reply["message"].strip(), "note": reply["note"]})
    return {"transcript": transcript}


def apply_action(m, t, a):
    """Run one market action; return (event result, feedback text for the agent's next turn)."""
    act, app, price, oid = a["action"], a["applicant"], a["price"], a["order_id"]
    try:
        if act == "pass":
            return {"ok": True}, "Your last action: pass."
        if act == "cancel":
            o = m.cancel(t, oid)
            return {"ok": True, "cancelled": o.id}, f"Your last action: order #{o.id} cancelled."
        if app is None:
            raise InvalidAction("Name the applicant for this action.")
        if act in ("bid", "ask"):
            if price is None:
                raise InvalidAction("Name a price for your bid or ask.")
            out = getattr(m, act)(t, app, price)
        else:
            out = getattr(m, act)(t, app)
        if isinstance(out, tuple):
            _, p, buyer, _ = out
            verb = "bought" if buyer == t else "sold"
            return {"ok": True, "trade": list(out)}, f"Your last action: you {verb} one share of {app} at {p} ECU."
        return {"ok": True, "order": out.id}, f"Your last action: your {act} for {app} at {price} ECU is open as order #{out.id}."
    except InvalidAction as e:
        return {"ok": False, "error": str(e)}, f"Your last action was rejected: {e}"


def run_market(agents, rng, pay_keys):
    periods = []
    for period in range(1, PERIODS + 1):
        m = Market(task.ROLES)
        feedback = {t: "" for t in task.ROLES}
        events = []
        for rnd in range(1, MARKET_ROUNDS + 1):
            order = list(task.ROLES)
            rng.shuffle(order)
            for t in order:
                prompt = reminder(pay_keys[t]) + fill(
                    "market_turn", period=period, round=rnd, market_state=m.state(t), cash=m.cash[t],
                    available_cash=m.available_cash(t), holdings=m.holdings(t), action_feedback=feedback[t],
                )
                action = agents[t].ask(prompt, "market_action", MARKET_ACTION)
                result, feedback[t] = apply_action(m, t, action)
                if not result["ok"]:
                    agents[t].failures.append({"kind": "invalid_action", "period": period, "round": rnd, "error": result["error"]})
                events.append({"round": rnd, "trader": t, "action": action, "result": result})
        periods.append({
            "period": period, "events": events, "trades": [list(x) for x in m.trades], "spreads": m.spreads(),
            "cash_end": m.cash, "shares_end": m.shares,
            "payoff_gbp": {t: m.payoff_gbp(t, task.BEST) for t in task.ROLES},
        })
    paid = rng.randint(1, PERIODS)
    return {"periods": periods, "paid_period": paid, "payoff_gbp": periods[paid - 1]["payoff_gbp"]}


# --- triad -------------------------------------------------------------------------

def run_triad(condition, triad, seed, model, out_dir, manipulation="control", protocol="paper", prompt_variant="baseline", information_regime="distributed"):
    if prompt_variant not in PROMPT_VARIANTS:
        raise ValueError(f"Unknown prompt variant: {prompt_variant}")
    if protocol not in ("paper", "no-quiz", "open"):
        raise ValueError(f"Unknown protocol: {protocol}")
    if protocol == "no-quiz" and condition != "discussion":
        raise ValueError("The no-quiz protocol is discussion only.")
    if prompt_variant != "baseline" and (condition != "discussion" or protocol == "open"):
        raise ValueError("Prompt sensitivity variants require discussion with the initial ranking retained.")
    if information_regime not in ("distributed", "complete"):
        raise ValueError(f"Unknown information regime: {information_regime}")
    if information_regime == "complete" and condition != "discussion":
        raise ValueError("Complete-information sensitivity is discussion only.")
    rng = random.Random(seed)
    pay_keys = {r: mp.key(condition, manipulation, r) for r in task.ROLES}
    rec = {
        "condition": condition, "manipulation": manipulation, "triad": triad, "seed": seed, "model": model.model,
        "reasoning_effort": model.effort, "pay_keys": pay_keys, "discussion_side_gbp": mp.DISCUSSION_SIDE_GBP, "protocol": protocol,
        "prompt_variant": prompt_variant, "final_transcript_included": condition == "discussion",
        "information_regime": information_regime,
        "started": datetime.now(timezone.utc).isoformat(), "status": "running",
    }
    system_section = "system_simulation" if prompt_variant in ("simulation", "combined") else "system"
    agents = {r: Agent(r, model, system_section) for r in task.ROLES}
    information = {r: fill("complete_information" if information_regime == "complete" else "private_information",
                           information=task.information(r, complete=information_regime == "complete")) for r in task.ROLES}
    try:
        if protocol == "open":  # experiment 3: no quiz, no ranking before the discussion
            assert condition == "discussion", "the open protocol is discussion only"
            intro = {r: briefing(condition, pay_keys[r], protocol) + "\n\n" + information[r] + "\n\n"
                     for r in task.ROLES}
            rec[condition] = run_discussion(agents, pay_keys, intro)
            rec["ranking_after"] = {r: rank(agents[r], fill("ranking_after_discussion_open"), rec["discussion"]["transcript"]) for r in task.ROLES}
        else:
            if protocol == "paper":
                rec["quiz"] = {r: run_quiz(agents[r], condition, pay_keys[r], prompt_variant) for r in task.ROLES}
            rec["ranking_before"] = {
                r: rank(agents[r], (briefing(condition, pay_keys[r], protocol, prompt_variant) + "\n\n" if protocol == "no-quiz" else "")
                        + information[r] + "\n\n" + fill("ranking_before"))
                for r in task.ROLES
            }
            rec[condition] = run_discussion(agents, pay_keys) if condition == "discussion" else run_market(agents, rng, pay_keys)
            final_section = "ranking_after_discussion_open" if prompt_variant in ("neutral-final", "combined") else f"ranking_after_{condition}"
            transcript = rec["discussion"]["transcript"] if condition == "discussion" else None
            rec["ranking_after"] = {r: rank(agents[r], fill(final_section), transcript) for r in task.ROLES}
        votes = sum(1 for x in rec["ranking_after"].values() if x and task.correct(x))
        rec["outcome"] = {"b_votes": votes, "unanimous": votes == 3, "majority": votes >= 2}
        if condition == "discussion":
            rec["outcome"]["bonus_gbp"] = 4 if votes >= 2 else 0
            firsts = [x[0] if x else None for x in rec["ranking_after"].values()]
            rec["outcome"]["side_gbp"] = {r: mp.discussion_side_payment(manipulation, r, firsts) for r in task.ROLES}
        else:
            paid = rec["market"]["periods"][rec["market"]["paid_period"] - 1]["trades"]
            rec["outcome"]["side_gbp"] = {r: mp.market_side_payment(manipulation, r, paid) for r in task.ROLES}
        rec["status"] = "complete"
    except ModelError as e:
        rec.update(status="failed", error=str(e), traceback=traceback.format_exc())
    rec["finished"] = datetime.now(timezone.utc).isoformat()
    rec["agents"] = {r: {"messages": a.messages, "usage": a.usage, "failures": a.failures} for r, a in agents.items()}
    path = out_dir / f"{condition}-{manipulation}-{triad:03d}.json"
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return path, rec["status"], rec.get("outcome")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triads", type=int, default=3, help="triads per condition")
    ap.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=list(CONDITIONS))
    ap.add_argument("--manipulations", nargs="+", choices=mp.MANIPULATIONS, default=["control"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20261020)
    ap.add_argument("--fake", action="store_true", help="random schema-valid answers, no API calls")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--effort", default=EFFORT)
    ap.add_argument("--prompt-variant", choices=PROMPT_VARIANTS, default="baseline")
    ap.add_argument("--information-regime", choices=("distributed", "complete"), default="distributed")
    ap.add_argument("--side-gbp", type=int, default=mp.DISCUSSION_SIDE_GBP, help="discussion side payment in £ (experiment 3)")
    ap.add_argument("--protocol", choices=("paper", "no-quiz", "open"), default="paper",
                    help="no-quiz: retain initial ranking; open: also omit it (both discussion only)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if args.triads < 1 or args.workers < 1 or args.side_gbp < 0:
        ap.error("triads and workers must be positive; side payment must be nonnegative")
    if args.protocol == "no-quiz" and args.conditions != ["discussion"]:
        ap.error("--protocol no-quiz requires --conditions discussion")
    if args.prompt_variant != "baseline" and (args.conditions != ["discussion"] or args.protocol == "open"):
        ap.error("prompt sensitivity variants require discussion with the initial ranking retained")
    if args.information_regime == "complete" and args.conditions != ["discussion"]:
        ap.error("complete-information sensitivity requires --conditions discussion")
    mp.DISCUSSION_SIDE_GBP = args.side_gbp

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + ("-fake" if args.fake else "")
    out_dir = args.out or HERE.parent / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    model = FakeModel(args.seed) if args.fake else OpenAIModel(args.model, args.effort)
    cells = [(c, m) for c in args.conditions for m in args.manipulations]
    jobs = [(c, m, i, args.seed * 1000 + j) for j, (c, m, i) in enumerate((c, m, i) for c, m in cells for i in range(1, args.triads + 1))]
    (out_dir / "config.json").write_text(json.dumps({
        "run_id": run_id, "model": model.model, "reasoning_effort": model.effort, "triads_per_condition": args.triads,
        "conditions": args.conditions, "manipulations": args.manipulations, "seed": args.seed, "discussion_side_gbp": args.side_gbp, "protocol": args.protocol, "discussion_rounds": DISCUSSION_ROUNDS,
        "market_periods": PERIODS, "market_rounds": MARKET_ROUNDS, "instructions": (HERE / "instructions.md").read_text(),
        "prompt_variant": args.prompt_variant, "final_transcript_included": "discussion" in args.conditions,
        "information_regime": args.information_regime,
    }, indent=1))

    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(run_triad, c, i, s, model, out_dir, m, args.protocol, args.prompt_variant, args.information_regime) for c, m, i, s in jobs]
        for f in as_completed(futures):
            path, status, outcome = f.result()
            print(f"{path.name}: {status} {outcome or ''}", flush=True)
    print(f"done in {time.time() - t0:.0f}s -> {out_dir}")


if __name__ == "__main__":
    main()
