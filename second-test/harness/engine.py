"""One game on the platform: clock, search, messaging along network ties, answer registry, and the text each
player sees. Players act in synchronous turns of TICK seconds; everything a player does in turn t takes effect
at the end of the turn (second TICK * (t + 1)) and is seen by others at the start of turn t + 1."""

import networks
import task
from agent import fill

TICK = 30
SEARCHES_PER_TICK = 2
SENDS_PER_TICK = 1
BASE_PAY, PAY_PER_MINUTE = 0.40, 0.14

# Time budget (flexible time): seconds a typical adult needs at a computer. Fixed from the literature, not tuned.
READ_WORDS_PER_SECOND = 238 / 60  # silent reading of English non-fiction (Brysbaert 2019, meta-analysis)
TYPE_SECONDS_PER_WORD = 60 / 40  # composing text at about 40 words per minute (copy typing averages 52; Dhakal et al. 2018)
SEARCH_SECONDS = 5  # type one keyword, submit, see the result appear
MESSAGE_SECONDS = 3  # pick recipients and send, or share a clue with a click
ANSWER_SECONDS = 5  # choose a name from the list and set the confidence


def clock(seconds):
    return f"{seconds // 60}:{seconds % 60:02d}"


class Game:
    def __init__(self, mystery, network, players, rng, duration=900, ask_victim=True,
                 searches=SEARCHES_PER_TICK, sends=SENDS_PER_TICK, repeat_search=False,
                 message_costs_time=False, message_cap=None, read_costs_time=False, time_budget=False,
                 answers_first=False, notepad_words=None, plain_pay=False):
        """players: node -> fake name.
        message_costs_time: writing a message (one with free text, including replies) takes the whole turn, so no
        search runs that turn; passing on clues or forwarding without text does not. message_cap: most messages a
        player can send in the whole game (None: no limit).
        read_costs_time: incoming messages wait unread in an inbox; opening them takes the whole turn (no search or
        message that turn) and their content, including shared clues, is shown at the start of the next turn.
        time_budget: each turn has TICK seconds. Reading the new items on screen is charged first (overflow carries
        into the next turn), then answers, messages and searches run in that order while time is left. Per-turn
        limits on searches and messages, and message_costs_time, do not apply.
        answers_first: each turn opens with the answers of the people the player follows, with a tally, before the
        new search results and messages (the human interface showed the answer panel at all times).
        notepad_words: each turn the player can add a scribble of at most this many words to a notepad that stays
        on screen for the whole game (longer scribbles are cut off); None: no notepad."""
        self.m, self.network, self.players, self.rng = mystery, network, dict(players), rng
        self.duration, self.ticks, self.ask_victim = duration, duration // TICK, ask_victim
        self.searches, self.sends, self.repeat_search = searches, sends, repeat_search
        self.message_costs_time, self.message_cap = message_costs_time and not time_budget, message_cap
        self.read_costs_time, self.time_budget, self.answers_first = read_costs_time, time_budget, answers_first
        self.notepad_words, self.plain_pay = notepad_words, plain_pay
        if time_budget:
            self.searches = self.sends = 99
        self.nodes = sorted(players)
        self.node_of = {name: n for n, name in players.items()}
        self.sources = {n: [s for s in networks.sources(network, n) if s in players] for n in self.nodes}
        self.targets = {n: [s for s in networks.targets(network, n) if s in players] for n in self.nodes}
        self.known = {n: {} for n in self.nodes}  # clue id -> text, found by search or received
        self.searched = {n: set() for n in self.nodes}
        self.seen_msgs = {n: set() for n in self.nodes}
        self.sent = {n: 0 for n in self.nodes}
        self.notepad = {n: [] for n in self.nodes}  # (seconds, scribble)
        self.inbox = {n: [] for n in self.nodes}  # unread (message record, clue ids) when read_costs_time
        self.debt = {n: 0.0 for n in self.nodes}  # reading left over from earlier turns, in seconds
        self.available = {n: float(TICK) for n in self.nodes}  # seconds left for actions in the current turn
        self.pending = {n: {"hq": [], "search": [], "msgs": [], "problems": []} for n in self.nodes}
        self.murderer = {n: None for n in self.nodes}  # (name, confidence)
        self.victim = {n: None for n in self.nodes}
        self.messages, self.events, self.answer_log, self.snapshots = [], [], [], []

    # --- what a player sees ---------------------------------------------------------

    def recipients(self, node):
        return [self.players[t] for t in self.targets[node]]

    def messaging_text(self, node):
        follow = ", ".join(self.players[s] for s in self.sources[node]) or "nobody"
        send = ", ".join(self.recipients(node)) or "nobody"
        return (f"You follow (see the answers and receive the messages of): {follow}. "
                f"You can send messages to (the people who follow you): {send}.")

    def _answer_text(self, node, own=False):
        empty = "not entered (earning nothing)" if own and not self.plain_pay else "not entered"
        parts = []
        if self.ask_victim:
            parts.append(f"victim: {self.victim[node] or empty}")
        m = self.murderer[node]
        parts.append(f"murderer: {m[0]} ({m[1]}% confident)" if m else f"murderer: {empty}")
        return "; ".join(parts) if own else f"{self.players[node]}: " + "; ".join(parts)

    def turn_text(self, node, t):
        p = self.pending[node]
        blocks = []
        if p["hq"]:
            blocks.append("**Messages from headquarters:**\n" + "\n".join(f"- {x}" for x in p["hq"]))
        if p["search"]:
            blocks.append("**Your search results:**\n" + "\n".join(f"- {x}" for x in p["search"]))
        if p["msgs"]:
            blocks.append("**New messages:**\n" + "\n".join(f"- {x}" for x in p["msgs"]))
        if p["problems"]:
            blocks.append("**Problems with your last turn:**\n" + "\n".join(f"- {x}" for x in p["problems"]))
        if self.message_cap is not None and self.targets[node]:
            blocks.append(f"**Messages left:** {self.message_cap - self.sent[node]} of {self.message_cap}")
        if self.notepad_words:
            pad = "\n".join(f"- {clock(s)} {x}" for s, x in self.notepad[node]) or "(empty)"
            blocks.append(f"**Your notepad:**\n{pad}")
        if self.inbox[node]:
            senders = ", ".join(dict.fromkeys(self.players[r["sender"]] for r, _ in self.inbox[node]))
            blocks.append(f"**Unread messages:** {len(self.inbox[node])}, from {senders}. "
                          "Opening them takes this turn; you will see them at the start of your next turn.")
        if self.time_budget:
            words = sum(len(x.split()) for k in ("hq", "search", "msgs") for x in p[k])
            reading = words / READ_WORDS_PER_SECOND
            left = TICK - self.debt[node] - reading
            self.debt[node], self.available[node] = max(0.0, -left), max(0.0, left)
            self.events.append({"seconds": t * TICK, "kind": "time", "node": node, "words": words,
                                "reading": round(reading, 1), "available": round(self.available[node], 1)})
            blocks.append(f"**Your time:** reading the new items above takes about {round(reading)} seconds; "
                          + (f"you have about {round(self.available[node])} seconds left in this turn for actions."
                             if self.available[node] > 0 else
                             "you have no time left for actions in this turn, and reading continues into the next turn."))
        self.pending[node] = {k: [] for k in p}
        neighbours = "\n".join(f"- {self._answer_text(s)}" for s in self.sources[node]) or "(you follow nobody)"
        if self.answers_first and self.sources[node]:
            neighbours = self._tally(node) + "\n" + neighbours
        return fill("turn_answers_first" if self.answers_first else "turn", elapsed=clock(t * TICK), remaining=clock(self.duration - t * TICK),
                    updates="\n\n".join(blocks) or "Nothing new since your last turn.",
                    own=self._answer_text(node, own=True), neighbours="\n" + neighbours if self.sources[node] else neighbours)

    def _tally(self, node):
        """'3 of the 8 people you follow have entered Mr. X as the murderer (average confidence 65%); ...'"""
        answers = [self.murderer[s] for s in self.sources[node]]
        k = len(answers)
        groups = {}
        for a in answers:
            if a:
                groups.setdefault(a[0], []).append(a[1])
        parts = [f"{len(c)} of the {k} people you follow {'has' if len(c) == 1 else 'have'} entered {name} as the murderer"
                 f" (average confidence {round(sum(c) / len(c))}%)"
                 for name, c in sorted(groups.items(), key=lambda x: -len(x[1]))]
        empty = k - sum(len(c) for c in groups.values())
        if empty:
            parts.append(f"{empty} of the {k} {'has' if empty == 1 else 'have'} not entered a murderer")
        return "; ".join(parts) + "."

    def broadcast(self, t):
        """Headquarters messages due during turn t, to everyone."""
        for s, texts in self.m.broadcasts.items():
            if t * TICK <= s < (t + 1) * TICK:
                for n in self.nodes:
                    self.pending[n]["hq"].extend(texts)
                self.events.append({"seconds": s, "kind": "broadcast", "texts": texts})

    # --- actions ----------------------------------------------------------------------

    def apply(self, node, t, action):
        """Apply one player's turn. Returns True if the player's murderer answer is now the culprit."""
        start, end = t * TICK, (t + 1) * TICK
        problems = self.pending[node]["problems"]
        queries = [q for q in action.get("searches", []) if q.strip()]
        sends = action.get("messages", [])[: self.sends]
        if self.read_costs_time and action.get("open_messages"):
            if self.inbox[node]:
                for rec, clues in self.inbox[node]:
                    self.seen_msgs[node].add(rec["id"])
                    for c in clues:
                        self.known[node][c] = self.known[node].get(c) or self._clue_text(c)
                    self.pending[node]["msgs"].append(self._render(rec))
                self.events.append({"seconds": start, "kind": "open", "node": node, "messages": [r["id"] for r, _ in self.inbox[node]]})
                self.inbox[node] = []
                if queries or sends:
                    problems.append("You spent the turn reading your messages, so your searches and messages were not run.")
                queries, sends = [], []
            else:
                problems.append("You had no unread messages to open.")
        if self.notepad_words and action.get("scribble", "").strip():
            words = action["scribble"].split()
            if len(words) > self.notepad_words:
                problems.append(f"You can only scribble {self.notepad_words} words per turn; the rest was not written down.")
            self.notepad[node].append((start, " ".join(words[: self.notepad_words])))
        answers_fit = True
        if self.time_budget:
            queries, sends, answers_fit = self._fit_budget(node, start, action, queries, sends, problems)
        if self.message_costs_time and queries and any(m["text"].strip() for m in sends):
            problems.append("Writing a message takes the whole turn, so your searches were not run: " + ", ".join(queries) + ".")
            queries = []
        if len(queries) > self.searches and not self.time_budget:
            problems.append(f"Only {self.searches} searches per turn; ignored: {', '.join(queries[self.searches:])}.")
        for q in queries[: self.searches]:
            clue = task.search(self.m, q, start, set() if self.repeat_search else self.searched[node], self.rng)
            self.events.append({"seconds": start, "kind": "search", "node": node, "query": q,
                                "clue": clue.id if clue else None, "wave": clue.wave if clue else None})
            if clue:
                self.searched[node].add(clue.id)
                self.known[node][clue.id] = clue.text
                self.pending[node]["search"].append(f'"{q}": {clue.id}: {clue.text}')
            else:
                self.pending[node]["search"].append(f"\"{q}\": No results were found for your search '{q}'.")
        if len(action.get("messages", [])) > self.sends and not self.time_budget:
            problems.append(f"Only {self.sends} message(s) per turn; the extra messages were not sent.")
        for msg in sends:
            if self.message_cap is not None and self.sent[node] >= self.message_cap:
                problems.append(f"You have used all {self.message_cap} of your messages; it was not sent.")
                break
            self.sent[node] += self._send(node, end, msg, problems)
        if not answers_fit:
            return bool(self.murderer[node]) and self.murderer[node][0] == self.m.culprit
        if self.ask_victim and action.get("victim") and action["victim"] != self.victim[node]:
            self.victim[node] = action["victim"]
            self.answer_log.append({"seconds": end, "node": node, "question": "victim", "answer": action["victim"]})
        m = action.get("murderer")
        if m:
            new = (m["name"], max(0, min(100, int(m["confidence"]))))
            if new != self.murderer[node]:
                self.murderer[node] = new
                self.answer_log.append({"seconds": end, "node": node, "question": "murderer", "answer": new[0],
                                        "confidence": new[1], "category": self.m.category(new[0])})
        return bool(self.murderer[node]) and self.murderer[node][0] == self.m.culprit

    def _fit_budget(self, node, start, action, queries, sends, problems):
        """Spend the turn's remaining seconds on answers, then messages, then searches; drop what does not fit."""
        left, used, dropped = self.available[node], 0.0, []
        changes = int(bool(self.ask_victim and action.get("victim") and action["victim"] != self.victim[node]))
        m = action.get("murderer")
        changes += int(bool(m) and (m["name"], max(0, min(100, int(m["confidence"])))) != self.murderer[node])
        answers_fit = changes * ANSWER_SECONDS <= left
        if answers_fit:
            used += changes * ANSWER_SECONDS
        else:
            dropped.append("your answer change")
        kept_sends = []
        for msg in sends:
            cost = MESSAGE_SECONDS + len(msg["text"].split()) * TYPE_SECONDS_PER_WORD
            if used + cost <= left:
                kept_sends.append(msg)
                used += cost
            else:
                dropped.append(f"a message ({round(cost)} seconds)")
        kept_queries = []
        for q in queries:
            if used + SEARCH_SECONDS <= left:
                kept_queries.append(q)
                used += SEARCH_SECONDS
            else:
                dropped.append(f'the search "{q}"')
        if dropped:
            problems.append(f"Not enough time in your last turn (about {round(left)} seconds); not done: " + ", ".join(dropped) + ".")
        self.events.append({"seconds": start, "kind": "spent", "node": node, "used": round(used, 1), "available": round(left, 1)})
        return kept_queries, kept_sends, answers_fit

    def _send(self, node, seconds, msg, problems):
        to = [self.node_of[x] for x in dict.fromkeys(msg["to"]) if x in self.node_of and self.node_of[x] in self.targets[node]]
        clues = [c for c in dict.fromkeys(msg["share_clues"]) if c in self.known[node]]
        bad = [c for c in msg["share_clues"] if c not in self.known[node]]
        if bad:
            problems.append(f"You cannot share clues you do not have: {', '.join(bad)}.")
        refs = {}
        for key in ("reply_to", "forward"):
            ref = msg.get(key)
            if ref and ref not in self.seen_msgs[node]:
                problems.append(f"Unknown message {ref} in {key}; ignored.")
                ref = None
            refs[key] = next(x for x in self.messages if x["id"] == ref) if ref else None
        text = msg["text"].strip()
        if not to or not (text or clues or refs["forward"]):
            problems.append("A message needs at least one recipient and some content; it was not sent.")
            return False
        kind = ("reply" if refs["reply_to"] else "forward" if refs["forward"] else
                "share_text" if clues and text else "share" if clues else "text")
        rec = {"id": f"M{len(self.messages) + 1}", "seconds": seconds, "sender": node, "to": to, "kind": kind,
               "text": text, "clues": clues, "reply_to": refs["reply_to"]["id"] if refs["reply_to"] else None,
               "forward": refs["forward"]["id"] if refs["forward"] else None}
        self.messages.append(rec)
        self.seen_msgs[node].add(rec["id"])
        shown = self._render(rec)
        carried = clues + (refs["forward"]["clues"] if refs["forward"] else [])
        for r in to:
            if self.read_costs_time:
                self.inbox[r].append((rec, carried))
                continue
            self.seen_msgs[r].add(rec["id"])
            for c in carried:
                self.known[r][c] = self.known[r].get(c) or self._clue_text(c)
            self.pending[r]["msgs"].append(shown)
        return True

    def _clue_text(self, cid):
        return next(c.text for c in self.m.clues if c.id == cid)

    def _render(self, rec):
        head = f"{rec['id']} from {self.players[rec['sender']]}"
        if rec["reply_to"]:
            orig = next(x for x in self.messages if x["id"] == rec["reply_to"])
            head += f", in reply to {orig['id']} from {self.players[orig['sender']]}" + (f' ("{orig["text"]}")' if orig["text"] else "")
        parts = [head + ":"]
        if rec["text"]:
            parts.append(f'"{rec["text"]}"')
        if rec["clues"]:
            parts.append("Shared clues: " + " ".join(f"{c}: {self._clue_text(c)}" for c in rec["clues"]))
        if rec["forward"]:
            fwd = next(x for x in self.messages if x["id"] == rec["forward"])
            parts.append(f"Forwarded {self._render(fwd)}")
        return " ".join(parts)

    # --- records ----------------------------------------------------------------------

    def snapshot(self, t):
        self.snapshots.append({"seconds": (t + 1) * TICK, "murderer": {n: self.murderer[n] for n in self.nodes},
                               "victim": {n: self.victim[n] for n in self.nodes}})

    def earnings(self):
        """Base pay plus pay per minute with each correct answer entered, from the 30-second snapshots."""
        pay = {}
        for n in self.nodes:
            minutes = sum(TICK / 60 for s in self.snapshots[:-1] for q, right in (("murderer", self.m.culprit), ("victim", self.m.victim))
                          if (s[q][n][0] if q == "murderer" and s[q][n] else s[q][n]) == right)
            pay[n] = round(BASE_PAY + PAY_PER_MINUTE * minutes, 2)
        return pay

    def outcome(self):
        final = {n: self.m.category(self.murderer[n][0] if self.murderer[n] else None) for n in self.nodes}
        return {"num_correct": sum(v == "correct" for v in final.values()), "final": final,
                "attention_passed": {n: self.victim[n] == self.m.victim for n in self.nodes} if self.ask_victim else None,
                "messages": len(self.messages), "text_messages": sum(x["kind"] in ("text", "share_text") for x in self.messages),
                "shares": sum(x["kind"] == "share" for x in self.messages), "replies": sum(x["kind"] == "reply" for x in self.messages),
                "forwards": sum(x["kind"] == "forward" for x in self.messages),
                "searches": sum(e["kind"] == "search" for e in self.events)}
