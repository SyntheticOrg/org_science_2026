"""Chat: a turn-based conversation among the writers of a group (standard library only).

Kit file of the synthetic-organisations plugin, generalised from the chat loop of the Brandts & Cooper replication.
The study builds each prompt and calls the agent inside `say`; who may read the transcript is the study's choice.
"""

from agent import enum, nullable


def run_chat(say, writers, turns, rng, cap=None):
    """say(role, turn, log) -> message text or None. The order of writers is shuffled every turn; the chat ends
    after a turn in which nobody wrote, or after `turns` turns. cap: most messages a writer may send in this chat
    (module B2); a writer at the cap is not asked again. Returns (log, ended), ended being "silence" or "budget"."""
    log, sent = [], {w: 0 for w in writers}
    for turn in range(1, turns + 1):
        order = list(writers)
        rng.shuffle(order)
        wrote = False
        for role in order:
            if cap is not None and sent[role] >= cap:
                continue
            msg = (say(role, turn, log) or "").strip() or None
            log.append({"turn": turn, "speaker": role, "message": msg})
            if msg:
                sent[role] += 1
                wrote = True
        if not wrote:
            return log, "silence"
    return log, "budget"


def transcript(log, viewer=None):
    lines = [f"  {m['speaker']}{' (you)' if m['speaker'] == viewer else ''}: {m['message']}" for m in log if m["message"]]
    return "\n".join(lines) or "  (no messages yet)"


def chat_schema(presets=None):
    """Reply properties for one chat turn: free text, or one of the preset messages; null stays silent."""
    return {"message": nullable(enum(presets) if presets else {"type": "string"})}
