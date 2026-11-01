"""Toy reporting game: an informed adviser A and an uninformed decider D, in three treatments.

Kit template of the synthetic-organisations plugin: replace the game with the source study's task, keep the shape.
A study module defines TREATMENTS, FOCAL (the treatments whose contrast is the target; calibration never touches
them), MODEL, EFFORT and run_group(group) -> record dict with a status, and calls runner.main(study) as a script.

Run from the study folder: python3 harness/study.py --fake (see runner.py for the other modes).
"""

import sys
from pathlib import Path

import runner
from agent import Agent, GroupFailed, ModelError, enum, fill, load_sections, obj
from chat import chat_schema, run_chat, transcript

S = load_sections(Path(__file__).resolve().parent / "instructions.md")
TREATMENTS = ("aligned-report", "conflict-report", "conflict-chat")
FOCAL = ("conflict-report", "conflict-chat")  # reserve both sides of the focal contrast for evaluation
MODEL, EFFORT = "gpt-6-luna", "medium"  # frozen with --freeze; record any change as a variant
ROUNDS, TURNS, STATES = 3, 3, (1, 2, 3, 4, 5)
NUMBER = {"number": enum(STATES)}


def target(state, conflict):
    return min(state + 1, 5) if conflict else state


def payoffs(state, choice, conflict):
    return {"A": 10 * (choice == target(state, conflict)), "D": 10 * (choice == state)}


def run_group(group):
    t = group.treatment
    conflict, chat = t.startswith("conflict"), t.endswith("chat")
    opening = fill(S["opening"], rounds=ROUNDS, communication=fill(S["comm_chat"], turns=TURNS) if chat else S["comm_report"],
                   incentive=S["incentive_conflict" if conflict else "incentive_aligned"])
    agents = {r: Agent(r, group.model_for(r), fill(S["system"], role=r)) for r in ("A", "D")}
    rec = {"rounds": []}

    def ask(role, prompt, name, props):
        text = "\n\n".join(x for x in (prompt, S["note"] if group.notes else None) if x)
        return agents[role].ask(text, name, obj(props, note=group.notes))

    try:
        for r in range(1, ROUNDS + 1):
            state = group.rng.choice(STATES)
            head = {"A": fill(S["round_a"], round=r, state=state), "D": fill(S["round_d"], round=r)}
            if r == 1:
                head = {k: f"{opening}\n\n{v}" for k, v in head.items()}
            rnd = {"round": r, "state": state}
            if chat:
                first = dict(head)  # the round's header opens each player's first prompt

                def say(role, turn, log):
                    prompt = fill(S["ask_chat"], turn=turn, turns=TURNS, transcript=transcript(log, role))
                    return ask(role, "\n\n".join(x for x in (first.pop(role, None), prompt) if x), "chat", chat_schema())["message"]

                rnd["chat"], rnd["chat_ended"] = run_chat(say, ("A", "D"), TURNS, group.rng)
                context = f"Conversation:\n{transcript(rnd['chat'], 'D')}"
                d_head = first.pop("D", None)
            else:
                rnd["report"] = ask("A", f"{head['A']}\n\n{S['ask_report']}", "report", NUMBER)["number"]
                context, d_head = f"Player A reports the number {rnd['report']}.", head["D"]
            prompt = fill(S["ask_choice"], context=context)
            rnd["choice"] = ask("D", "\n\n".join(x for x in (d_head, prompt) if x), "choice", NUMBER)["number"]
            rnd["payoffs"] = payoffs(state, rnd["choice"], conflict)
            for role, a in agents.items():
                a.tell(fill(S["result"], round=r, state=state, choice=rnd["choice"], pay_a=rnd["payoffs"]["A"], pay_d=rnd["payoffs"]["D"]))
            rec["rounds"].append(rnd)
        rec["status"] = "complete"
    except (GroupFailed, ModelError) as e:
        rec.update(status="incomplete", error=str(e))
    rec["agents"] = {role: a.record() for role, a in agents.items()}
    return rec


if __name__ == "__main__":
    runner.main(sys.modules[__name__])
