"""Experiment runner: nine fresh agents per trial, a solo practice mystery each, then the 15-minute networked
mystery in 30 synchronous turns. One JSON record per trial.

Usage (from second-test/):
    python3 harness/runner.py --trials 1 --fake                                  # pipeline check, no API calls
    python3 harness/runner.py --networks Empty --trials 5 --workers 5            # calibration: nine independent players
    python3 harness/runner.py ... --reasoning-summary auto                       # also save reasoning summaries
    python3 harness/runner.py --trials 30 --workers 20                           # main run, all six treatments
"""

import argparse
import json
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import engine
import networks
import personas as persona_cards
import task
from agent import SUMMARY_MODES, Agent, FakeModel, ModelError, OpenAIModel, fill, turn_schema

HERE = Path(__file__).resolve().parent
PRACTICE_TICKS = 6  # stage 1 lasted 3 minutes

# Frozen on 2026-10-21 after calibration on isolates only (runs/20261021-calib10-empty-repeat-s1-mixed, APPROACH.md),
# before any networked trial was run. Change only with a new calibration run.
SEARCHES = 1  # per 30-second turn
REPEAT_SEARCH = True  # the platform's unique_factoids off: a search can return a clue the player already found
EFFORT_MIX = ("low", "medium", "high")  # each agent's reasoning effort, drawn independently
# Added after the network pilots (runs/20261021-netpilot-msgtime), set from message volume only. Isolates cannot
# send messages, so the isolate calibration is unaffected. The inbox and time-budget options stay off.
MESSAGE_COSTS_TIME = True  # a message with free text uses the whole turn


def interface(game, node):
    send_targets = (" (not available in the practice task)" if not game.sends else
                    " to the people listed in your messaging window" if game.targets[node] else
                    ", but nobody follows you, so you cannot send messages")
    rules = ""
    if game.sends and game.targets[node]:
        if game.message_costs_time:
            rules += (" Writing a message takes time: in a turn in which you send a message with your own text (including a"
                      " reply), you cannot search. Passing on clues or forwarding a message without adding text is quick and"
                      " does not stop you from searching.")
        if game.message_cap is not None:
            rules += f" You can send at most {game.message_cap} messages during the whole game."
    if game.time_budget:
        return fill("interface_budget", send_targets=send_targets, message_rules=rules)
    return fill("interface", searches=game.searches, sends=game.sends, send_targets=send_targets, message_rules=rules)


def run_practice(agent, rng, searches=SEARCHES, repeat_search=REPEAT_SEARCH, time_budget=False, plain_pay=False):
    """Stage 1 (Appendix B.1): one player, six clues, until the correct answer is entered or time runs out."""
    m = task.make_practice(rng)
    g = engine.Game(m, "Empty", {1: agent.player}, rng, duration=PRACTICE_TICKS * engine.TICK, ask_victim=False,
                    searches=searches, sends=0, repeat_search=repeat_search, time_budget=time_budget, plain_pay=plain_pay)
    schema = turn_schema(m.suspects, [], [], ask_victim=False)
    g.broadcast(0)
    g.pending[1]["hq"].clear()  # the intro clue is part of the instructions
    passed = False
    for t in range(PRACTICE_TICKS):
        prompt = g.turn_text(1, t)
        if t == 0:
            prompt = fill("practice_instructions", interface=interface(g, 1), intro=m.broadcasts[0][0], turns=PRACTICE_TICKS,
                          answer_advice=fill("answer_advice_plain" if plain_pay else "answer_advice")) + "\n\n" + prompt
        passed = g.apply(1, t, agent.ask(prompt, "turn", schema))
        if passed:
            break
    outcome = "You entered the correct answer." if passed else f"You did not enter the correct answer ({m.culprit})."
    agent.messages.append({"role": "user", "content": fill("practice_result", outcome=outcome)})
    return {"passed": passed, "turns": t + 1, "searches": [e for e in g.events if e["kind"] == "search"], "answers": g.answer_log}


def run_trial(network, trial, seed, model, out_dir, practice=True, searches=SEARCHES,
              repeat_search=REPEAT_SEARCH, effort_mix=EFFORT_MIX, message_costs_time=MESSAGE_COSTS_TIME, message_cap=None,
              read_costs_time=False, time_budget=False, personas=False, answers_first=False, memory=None,
              others_may_know=False, notepad_words=None, plain_pay=False, susceptibility=False):
    """effort_mix: reasoning efforts to draw from, one independent draw per agent; None gives every agent the model's."""
    rng = random.Random(seed)
    mystery = task.make_main(rng)
    group = list(networks.nodes(network))
    names = rng.sample(task.PLAYER_NAMES, len(group))
    players = dict(zip(group, names))
    game = engine.Game(mystery, network, players, rng, searches=searches, repeat_search=repeat_search,
                       message_costs_time=message_costs_time, message_cap=message_cap,
                       read_costs_time=read_costs_time, time_budget=time_budget, answers_first=answers_first,
                       notepad_words=notepad_words, plain_pay=plain_pay)
    efforts = {n: rng.choice(effort_mix) if effort_mix else model.effort for n in game.nodes}
    prng = random.Random(f"{seed}-personas")  # separate stream, so personas leave the trial's other draws unchanged
    srng = random.Random(f"{seed}-susceptibility") if susceptibility else None
    cards = {n: persona_cards.draw(prng, srng) for n in game.nodes} if personas else {}
    agents = {n: Agent(players[n], model.with_effort(efforts[n]) if effort_mix else model,
                       persona_cards.describe(cards[n]) if personas else None, memory) for n in game.nodes}
    rec = {
        "network": network, "trial": trial, "seed": seed, "model": model.model, "reasoning_effort": model.effort,
        "reasoning_summary": model.summary, "tick_seconds": engine.TICK, "searches_per_tick": game.searches, "sends_per_tick": game.sends,
        "repeat_search": repeat_search, "effort_mix": effort_mix, "efforts": efforts,
        "message_costs_time": message_costs_time, "message_cap": message_cap,
        "read_costs_time": read_costs_time, "time_budget": time_budget, "personas": cards or None,
        "answers_first": answers_first, "memory": memory, "others_may_know": others_may_know, "notepad_words": notepad_words,
        "plain_pay": plain_pay, "susceptibility": susceptibility, "players": players, "positions": networks.POSITIONS[network], "edges": sorted(networks.EDGES[network]),
        "mystery": {"names": mystery.names, "victim": mystery.victim, "culprit": mystery.culprit,
                    "red_herring": mystery.red_herring, "suspects": mystery.suspects,
                    "clues": [{"id": c.id, "wave": c.wave, "text": c.text, "keywords": sorted(c.keywords)} for c in mystery.clues]},
        "started": datetime.now(timezone.utc).isoformat(), "status": "running",
    }
    schemas = {n: turn_schema(mystery.suspects, [mystery.victim] + mystery.suspects, game.recipients(n),
                              inbox=read_costs_time and bool(game.sources[n]), notepad=bool(notepad_words)) for n in game.nodes}
    try:
        with ThreadPoolExecutor(len(game.nodes)) as pool:
            if practice:
                seeds = {n: rng.randrange(2**32) for n in game.nodes}
                rec["practice"] = dict(zip(game.nodes, pool.map(lambda n: run_practice(agents[n], random.Random(seeds[n]), searches, repeat_search, time_budget, plain_pay), game.nodes)))
            for t in range(game.ticks):
                game.broadcast(t)
                prompts = {n: game.turn_text(n, t) for n in game.nodes}
                if t == 0:
                    for n in game.nodes:
                        messaging = game.messaging_text(n) + (" " + fill("others_may_know") if others_may_know and game.sources[n] else "")
                        prompts[n] = (fill("main_instructions", player=players[n], interface=interface(game, n), messaging=messaging,
                                           pay_advice=fill("pay_advice_plain" if plain_pay else "pay_advice"))
                                      + ("\n\n" + (fill("memory_note_notepad", words=notepad_words) if notepad_words else fill("memory_note"))
                                         if memory else "") + "\n\n" + prompts[n])
                actions = dict(zip(game.nodes, pool.map(lambda n: agents[n].ask(prompts[n], "turn", schemas[n], pin=t == 0), game.nodes)))
                order = list(game.nodes)
                rng.shuffle(order)
                for n in order:
                    game.apply(n, t, actions[n])
                game.snapshot(t)
        rec["outcome"] = game.outcome()
        rec["earnings"] = game.earnings()
        rec["status"] = "complete"
    except ModelError as e:
        rec.update(status="failed", error=str(e), traceback=traceback.format_exc())
    rec.update(finished=datetime.now(timezone.utc).isoformat(), events=game.events, messages=game.messages,
               answers=game.answer_log, snapshots=game.snapshots)
    rec["agents"] = {n: {"player": a.player, "messages": a.messages, "usage": a.usage, "failures": a.failures,
                          "reasoning": a.reasoning} for n, a in agents.items()}
    path = out_dir / f"{network}-{trial:03d}.json"
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return path, rec["status"], rec.get("outcome", {}).get("num_correct")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1, help="trials per network")
    ap.add_argument("--first-trial", type=int, default=1, help="number of the first trial (to rerun one trial)")
    ap.add_argument("--networks", nargs="+", choices=list(networks.EDGES), default=list(networks.TREATMENTS))
    ap.add_argument("--workers", type=int, default=4, help="trials run in parallel (each makes 9 calls at a time)")
    ap.add_argument("--seed", type=int, default=20261021)
    ap.add_argument("--slots", type=int, nargs="+", default=None,
                    help="seed position k of each listed network (default 0, 1, ...), to continue an earlier run's seeds")
    ap.add_argument("--model", default=None, help="override the model (default: agent.MODEL)")
    ap.add_argument("--effort", default=None, help="one reasoning effort for every agent (replaces the effort mix)")
    ap.add_argument("--reasoning-summary", choices=SUMMARY_MODES, default=None,
                    help="also request and save a summary of the model's reasoning for every call")
    ap.add_argument("--searches", type=int, default=SEARCHES, help="searches allowed per 30-second turn")
    ap.add_argument("--repeat-search", action=argparse.BooleanOptionalAction, default=REPEAT_SEARCH,
                    help="searches can return clues the player already found (the platform's unique_factoids off)")
    ap.add_argument("--effort-mix", nargs="+", choices=("minimal", "low", "medium", "high"), default=list(EFFORT_MIX),
                    help="draw each agent's reasoning effort from these, independently")
    ap.add_argument("--message-costs-time", action=argparse.BooleanOptionalAction, default=MESSAGE_COSTS_TIME,
                    help="a message with free text uses the whole turn (no search that turn)")
    ap.add_argument("--message-cap", type=int, default=None, help="most messages each player can send in the whole game")
    ap.add_argument("--read-costs-time", action="store_true",
                    help="incoming messages wait in an inbox; opening them takes the whole turn")
    ap.add_argument("--time-budget", action="store_true",
                    help="flexible time: reading, typing, searching and answering cost human-like seconds per 30-second turn")
    ap.add_argument("--personas", action="store_true",
                    help="give each agent a persona card drawn from the MTurk population (personas.py)")
    ap.add_argument("--answers-first", action="store_true",
                    help="open each turn with the answers of the people the agent follows, with a tally")
    ap.add_argument("--memory", type=int, default=None, help="agents keep only this many recent turns in view")
    ap.add_argument("--notepad-words", type=int, default=None,
                    help="a notepad on screen all game; each turn the agent can add a scribble of at most this many words")
    ap.add_argument("--susceptibility", action="store_true",
                    help="add a persona trait for how easily the agent is swayed by others (with --personas)")
    ap.add_argument("--plain-pay", action="store_true",
                    help="neutral answer wording (no 'earning nothing' or 'as soon as you have one'); for the memory setting")
    ap.add_argument("--others-may-know", action="store_true",
                    help="tell agents that the people they follow may have found clues they have not")
    ap.add_argument("--no-practice", action="store_true", help="skip the solo practice mystery")
    ap.add_argument("--fake", action="store_true", help="random schema-valid actions, no API calls")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if args.effort:
        args.effort_mix = None
    slots = args.slots or list(range(len(args.networks)))
    assert len(slots) == len(args.networks), "--slots needs one position per network"

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + ("-fake" if args.fake else "")
    out_dir = args.out or HERE.parent / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.fake:
        model = FakeModel(args.seed, summary=args.reasoning_summary)
    else:
        model = OpenAIModel(**{k: v for k, v in (("model", args.model), ("effort", args.effort)) if v},
                            summary=args.reasoning_summary)
    # Trial i of the k-th listed network gets seed * 1000 + 100 * k + (i - 1), so a single trial can be rerun alone.
    jobs = [(net, i, args.seed * 1000 + 100 * k + i - 1) for k, net in zip(slots, args.networks)
            for i in range(args.first_trial, args.first_trial + args.trials)]
    (out_dir / "config.json").write_text(json.dumps({
        "run_id": run_id, "model": model.model, "reasoning_effort": model.effort,
        "reasoning_summary": model.summary, "trials_per_network": args.trials,
        "networks": args.networks, "slots": slots, "seed": args.seed, "practice": not args.no_practice, "tick_seconds": engine.TICK,
        "searches_per_tick": args.searches, "repeat_search": args.repeat_search, "effort_mix": args.effort_mix,
        "message_costs_time": args.message_costs_time, "message_cap": args.message_cap,
        "read_costs_time": args.read_costs_time, "time_budget": args.time_budget, "personas": args.personas,
        "answers_first": args.answers_first, "memory": args.memory, "others_may_know": args.others_may_know,
        "notepad_words": args.notepad_words, "plain_pay": args.plain_pay,
        "susceptibility": args.susceptibility,
        "time_rates": {"read_words_per_second": engine.READ_WORDS_PER_SECOND, "type_seconds_per_word": engine.TYPE_SECONDS_PER_WORD,
                       "search": engine.SEARCH_SECONDS, "message": engine.MESSAGE_SECONDS, "answer": engine.ANSWER_SECONDS}, "sends_per_tick": engine.SENDS_PER_TICK,
        "instructions": (HERE / "instructions.md").read_text(),
    }, indent=1))

    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(run_trial, net, i, s, model, out_dir, not args.no_practice, args.searches,
                               args.repeat_search, args.effort_mix, args.message_costs_time, args.message_cap,
                               args.read_costs_time, args.time_budget, args.personas, args.answers_first,
                               args.memory, args.others_may_know, args.notepad_words, args.plain_pay, args.susceptibility)
                   for net, i, s in jobs]
        for f in as_completed(futures):
            path, status, correct = f.result()
            print(f"{path.name}: {status} correct={correct}", flush=True)
    print(f"done in {time.time() - t0:.0f}s -> {out_dir}")


if __name__ == "__main__":
    main()
