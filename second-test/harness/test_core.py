"""Checks for networks, the mystery, search, messaging, and scoring. Run: python3 test_core.py"""

import json
import random
from pathlib import Path

import engine
import networks
import task
from agent import FakeModel, fill, turn_schema

DATA = Path(__file__).resolve().parent.parent / "source" / "dataverse"

# Visible alters (totalAlters) per node in the authors' solutions2.tab.
VISIBLE = {
    "HubAndSpoke": [8] + [1] * 8,
    "CorePeriphery": [8] * 3 + [3] * 6,
    "OutCorePeriphery": [3] * 9,
    "InCorePeriphery": [8, 8, 8, 1, 0, 1, 0, 1, 0],
    "LocallyClustered": [3] * 9,
    "CompleteClique": [8] * 9,
}


def test_networks():
    for net, counts in VISIBLE.items():
        assert [len(networks.sources(net, n)) for n in networks.NODES] == counts, net
        assert all((i, i) not in networks.EDGES[net] for i in networks.NODES)
    # Appendix E: every node has three incoming ties in out core-periphery, three outgoing in in core-periphery,
    # and the locally clustered network has in- and out-degree three everywhere.
    assert all(len(networks.targets("InCorePeriphery", n)) == 3 for n in networks.NODES)
    assert all(len(networks.targets("LocallyClustered", n)) == 3 for n in networks.NODES)
    assert networks.sources("InCorePeriphery", 5) == [] and networks.targets("InCorePeriphery", 5) == [1, 2, 3]
    assert set(networks.POSITIONS) == set(networks.EDGES)


def test_counterfactual_networks():
    assert networks.core_periphery(3, 6) == networks.EDGES["OutCorePeriphery"]
    assert networks.core_periphery(3, 6, direction="in") == networks.EDGES["InCorePeriphery"]
    sees = lambda net: [len(networks.sources(net, n)) for n in networks.nodes(net)]
    assert sees("OutCP_up0") == [2] * 3 + [3] * 6 and sees("OutCP_up6") == [4] * 3 + [3] * 6
    assert sees("InCP_down0") == [8] * 3 + [0] * 6 and sees("InCP_down6") == [8] * 3 + [1] * 6
    for c in (1, 2, 4):  # out version: everyone sees exactly c others, as in the paper's design with c = 3
        assert sees(f"OutCP_core{c}") == [c] * (c + 6)
    for p in (3, 9):
        assert sees(f"OutCP_per{p}") == [3] * (3 + p)
    assert sees("OutStar") == [3] * 3 + [1] * 6
    assert networks.EDGES["InStar"] == {(j, i) for i, j in networks.EDGES["OutStar"]}
    for net in networks.COUNTERFACTUALS:
        assert all((i, i) not in networks.EDGES[net] for i in networks.nodes(net))
        assert {n for e in networks.EDGES[net] for n in e} <= set(networks.nodes(net))
        assert len(networks.nodes(net)) <= len(task.PLAYER_NAMES)


def test_networks_match_data():
    """Same check against the raw file, when it is present."""
    path = DATA / "solutions2.tab"
    if not path.exists():
        return
    import csv
    seen = {}
    with path.open() as f:
        for r in csv.DictReader(f):
            if r["network"] in VISIBLE:
                seen[(r["network"], int(r["node"]))] = int(r["totalAlters"])
    for net, counts in VISIBLE.items():
        assert [seen[(net, n)] for n in networks.NODES] == counts, net


def test_mystery():
    for seed in range(50):
        m = task.make_main(random.Random(seed))
        assert len(m.clues) == 41 and sum(c.wave == 2 for c in m.clues) == 15  # Appendix B.3: 26 + 15
        assert len(set(m.suspects) | {m.victim}) == 8
        assert m.culprit in m.suspects and m.red_herring in m.suspects and m.culprit != m.red_herring
        assert all(c.keywords for c in m.clues)
        assert sorted(int(c.id[1:]) for c in m.clues) == list(range(1, 42))
        surnames = {p.split(" ", 1)[1].lower() for p in m.suspects + [m.victim]}
        assert not surnames & {n.lower() for n in task.PLAYER_NAMES}
        # The weapon from the phase-3 broadcast is owned by exactly the red herring, the culprit and one other suspect.
        gun = m.names["weapon_gun"]
        owners = {p for c in m.clues for p in m.suspects if c.text.startswith(f"Search of {p}'s") and c.text.endswith(f"owned a {gun}.")}
        assert owners == {m.culprit, m.red_herring, m.names["davis"]}, owners
        assert all("{" not in c.text for c in m.clues) and all("{" not in x for v in m.broadcasts.values() for x in v)
        assert set(m.broadcasts) == {0, 300, 600}


def test_search():
    m = task.make_main(random.Random(1))
    rng = random.Random(0)
    brown = m.red_herring.split(" ", 1)[1]
    found = set()
    while (c := task.search(m, brown, 0, found, rng)):
        assert c.wave == 1 and brown in c.text
        found.add(c.id)
    early = len(found)
    while (c := task.search(m, f"Mr. {brown}'s", 300, found, rng)):  # multi-word query: first matching word counts
        assert brown in c.text
        found.add(c.id)
    assert len(found) > early and any(c.wave == 2 for c in m.clues if c.id in found)
    assert task.search(m, "the", 600, set(), rng) is None


def test_repeat_search():
    """With repeats allowed, a keyword with few clues keeps returning them; without, it runs dry."""
    m = task.make_main(random.Random(1))
    city = m.names["city_conf"]
    n = sum(city.lower() in c.keywords and c.wave == 1 for c in m.clues)
    rng = random.Random(0)
    g = engine.Game(m, "Empty", {1: "Avery"}, rng, repeat_search=True, searches=1)
    for t in range(4 * n):
        g.apply(1, t, {"searches": [city]})
    hits = [e["clue"] for e in g.events if e["kind"] == "search"]
    assert all(hits) and len(set(hits)) == n and len(hits) == 4 * n
    g = engine.Game(m, "Empty", {1: "Avery"}, rng, repeat_search=False, searches=1)
    for t in range(4 * n):
        g.apply(1, t, {"searches": [city]})
    hits = [e["clue"] for e in g.events if e["kind"] == "search"]
    assert len([h for h in hits if h]) == n


def test_effort_mix():
    import tempfile
    import runner
    with tempfile.TemporaryDirectory() as d:
        path, status, _ = runner.run_trial("Empty", 1, 3, FakeModel(3), Path(d), practice=False,
                                           effort_mix=["low", "medium", "high"], repeat_search=True)
        rec = json.loads(path.read_text())
        assert status == "complete" and rec["repeat_search"] is True
        assert set(rec["efforts"].values()) <= {"low", "medium", "high"} and len(rec["efforts"]) == 9


def test_personas():
    import personas
    rng = random.Random(0)
    cards = [personas.draw(rng) for _ in range(5000)]
    assert all(18 <= c["age"] <= 70 for c in cards)
    assert abs(sum(c["gender"] == "man" for c in cards) / 5000 - personas.MALE) < 0.03
    degree = sum(c["education"].startswith(("have a bachelor", "have a graduate")) for c in cards) / 5000
    assert abs(degree - 0.449) < 0.03  # 45% with at least a bachelor's degree (Levay et al. 2016)
    assert all(abs(sum(c[t] == "high" for c in cards) / 5000 - 1 / 3) < 0.03 for t in personas.TRAITS)
    text = personas.describe({"age": 25, "gender": "woman", "education": "have a bachelor's degree", "student": True,
                              **{t: "average" for t in personas.TRAITS}, "conscientiousness": "low"})
    assert text == ("You are a 25-year-old woman. You have a bachelor's degree, and you are currently a student. "
                    "You are easily distracted and not very careful or organised.")


def test_answers_first_tally():
    m = task.make_main(random.Random(2))
    players = dict(zip(networks.NODES, task.PLAYER_NAMES[:9]))
    g = engine.Game(m, "HubAndSpoke", players, random.Random(3), answers_first=True)
    for n, conf in ((2, 60), (3, 80), (4, 70)):
        g.murderer[n] = (m.culprit, conf)
    g.murderer[5] = (m.red_herring, 40)
    text = g.turn_text(1, 0)
    assert text.index("Answers of people you follow") < text.index("Your answers")
    assert (f"3 of the 8 people you follow have entered {m.culprit} as the murderer (average confidence 70%); "
            f"1 of the 8 people you follow has entered {m.red_herring} as the murderer (average confidence 40%); "
            "4 of the 8 have not entered a murderer.") in text
    assert "have entered" not in engine.Game(m, "Empty", players, random.Random(3), answers_first=True).turn_text(1, 0)


def test_memory_window():
    from agent import Agent
    seen = []
    class Echo(FakeModel):
        def __call__(self, messages, schema_name, schema):
            seen.append([x["content"] for x in messages])
            return super().__call__(messages, schema_name, schema)
    a = Agent("Avery", Echo(0), memory=2)
    schema = {"type": "object", "properties": {"notes": {"type": "string"}}, "required": ["notes"], "additionalProperties": False}
    a.ask("practice", "turn", schema)
    a.ask("MAIN", "turn", schema, pin=True)
    for i in range(5):
        a.ask(f"turn{i}", "turn", schema)
    last = seen[-1]
    assert last[1] == "MAIN" and "practice" not in last
    assert [x for x in last if x.startswith("turn")] == ["turn2", "turn3", "turn4"] and len(last) == 7
    assert len(a.messages) == 1 + 2 * 7  # the full conversation is still recorded


def test_hint_and_memory_note():
    import tempfile
    import runner
    with tempfile.TemporaryDirectory() as d:
        path, status, _ = runner.run_trial("HubAndSpoke", 1, 5, FakeModel(5), Path(d), practice=False,
                                           others_may_know=True, memory=3)
        rec = json.loads(path.read_text())
        first = next(x["content"] for x in rec["agents"]["2"]["messages"] if x["role"] == "user")
        assert fill("others_may_know") in first and "**Memory.**" in first and rec["memory"] == 3


def test_notepad():
    m = task.make_main(random.Random(2))
    g = engine.Game(m, "Empty", {1: "Avery"}, random.Random(3), notepad_words=8)
    g.apply(1, 0, {**_act(), "scribble": "Brown owns gun, was in Honolulu at the launch party"})
    g.apply(1, 1, {**_act(), "scribble": "  "})
    assert g.notepad[1] == [(0, "Brown owns gun, was in Honolulu at the")] and "only scribble 8 words" in g.pending[1]["problems"][0]
    for t in range(2, 6):
        g.turn_text(1, t)
    assert "Brown owns gun, was in Honolulu at the" in g.turn_text(1, 6)  # stays on screen
    assert "notepad" not in engine.Game(m, "Empty", {1: "Avery"}, random.Random(3)).turn_text(1, 0)


def test_plain_pay():
    import tempfile
    import runner
    with tempfile.TemporaryDirectory() as d:
        texts = {}
        for plain in (False, True):
            path, status, _ = runner.run_trial("Empty", 1, 4, FakeModel(4), Path(d), plain_pay=plain)
            msgs = json.loads(path.read_text())["agents"]["1"]["messages"]
            texts[plain] = " ".join(x["content"] for x in msgs if x["role"] == "user")
        assert "earning nothing" in texts[False] and "as soon as you have one" in texts[False]
        assert "earning nothing" not in texts[True] and "as soon as you have one" not in texts[True]
        assert "You can change your answers at any time." in texts[True]


def test_susceptibility_trait():
    import personas
    a, b, s = random.Random(9), random.Random(9), random.Random(10)
    without, with_ = [personas.draw(a) for _ in range(300)], [personas.draw(b, s) for _ in range(300)]
    assert all({k: v for k, v in w.items() if k != "susceptibility"} == o for o, w in zip(without, with_))
    assert abs(sum(w["susceptibility"] == "high" for w in with_) / 300 - 1 / 3) < 0.08
    p = {**without[0], **{t: "average" for t in personas.TRAITS}, "susceptibility": "low"}
    assert personas.describe(p).endswith("You are confident in your own judgment, and you rarely change your mind "
                                         "because of what other people think.")


def _game(net="HubAndSpoke"):
    m = task.make_main(random.Random(2))
    players = dict(zip(networks.NODES, task.PLAYER_NAMES[:9]))
    return m, engine.Game(m, net, players, random.Random(3))


def _act(**kw):
    return {"notes": "", "searches": [], "messages": [], "victim": None, "murderer": None, **kw}


def test_messaging_and_answers():
    m, g = _game()
    hub, spoke, other = g.players[1], g.players[2], g.players[3]
    g.broadcast(0)
    word = m.victim.split(" ", 1)[1]
    g.apply(2, 0, _act(searches=[word, word, word]))  # third search is over the limit
    assert len(g.searched[2]) == 2 and g.pending[2]["problems"]
    cid = sorted(g.searched[2])[0]
    g.apply(2, 0, _act(messages=[{"to": [hub, other], "text": "look", "share_clues": [cid, "C99"], "reply_to": None, "forward": None}]))
    msg = g.messages[-1]
    assert msg["to"] == [1] and msg["clues"] == [cid] and msg["kind"] == "share_text"  # spoke 2 cannot reach spoke 3
    assert cid in g.known[1] and cid not in g.known[3]
    g.apply(1, 1, _act(messages=[{"to": [other], "text": "", "share_clues": [], "reply_to": None, "forward": msg["id"]}]))
    assert g.messages[-1]["kind"] == "forward" and cid in g.known[3]
    g.apply(2, 1, _act(victim=m.victim, murderer={"name": m.culprit, "confidence": 140}))
    assert g.murderer[2] == (m.culprit, 100)
    text = g.turn_text(1, 2)
    assert f"{spoke}: victim: {m.victim}; murderer: {m.culprit} (100% confident)" in text
    assert f"{spoke}: victim" not in g.turn_text(3, 2)  # spoke 3 does not see spoke 2


def test_message_time_and_cap():
    m = task.make_main(random.Random(2))
    players = dict(zip(networks.NODES, task.PLAYER_NAMES[:9]))
    g = engine.Game(m, "CompleteClique", players, random.Random(3), searches=1, message_costs_time=True, message_cap=2)
    word = m.victim.split(" ", 1)[1]
    other = players[2]
    text = {"to": [other], "text": "hi", "share_clues": [], "reply_to": None, "forward": None}
    g.apply(1, 0, _act(searches=[word], messages=[text]))  # text message: search dropped
    assert not g.searched[1] and g.sent[1] == 1 and "whole turn" in g.pending[1]["problems"][0]
    g.apply(1, 1, _act(searches=[word]))
    cid = next(iter(g.searched[1]))
    g.apply(1, 2, _act(searches=[word], messages=[{**text, "text": "", "share_clues": [cid]}]))  # clue only: both run
    assert g.sent[1] == 2 and len([e for e in g.events if e["kind"] == "search" and e["node"] == 1]) == 2
    g.apply(1, 3, _act(messages=[{**text, "text": "", "share_clues": [cid]}]))  # over the cap
    assert g.sent[1] == 2 and len(g.messages) == 2
    assert "Messages left:** 0 of 2" in g.turn_text(1, 4)


def test_inbox():
    m = task.make_main(random.Random(2))
    players = dict(zip(networks.NODES, task.PLAYER_NAMES[:9]))
    g = engine.Game(m, "CompleteClique", players, random.Random(3), searches=1, read_costs_time=True)
    word = m.victim.split(" ", 1)[1]
    g.apply(1, 0, _act(searches=[word]))
    cid = next(iter(g.searched[1]))
    g.apply(1, 1, _act(messages=[{"to": [players[2]], "text": "look", "share_clues": [cid], "reply_to": None, "forward": None}]))
    assert cid not in g.known[2] and len(g.inbox[2]) == 1
    text = g.turn_text(2, 2)
    assert "Unread messages:** 1, from " + players[1] in text and "look" not in text
    g.apply(2, 2, {**_act(searches=[word]), "open_messages": True})  # opening takes the turn
    assert not g.searched[2] and cid in g.known[2] and not g.inbox[2]
    assert '"look"' in g.turn_text(2, 3)


def test_time_budget():
    m = task.make_main(random.Random(2))
    players = dict(zip(networks.NODES, task.PLAYER_NAMES[:9]))
    g = engine.Game(m, "CompleteClique", players, random.Random(3), time_budget=True, repeat_search=True)
    word = m.victim.split(" ", 1)[1]
    g.broadcast(0)
    text = g.turn_text(1, 0)  # the opening broadcast takes a few seconds to read
    left = g.available[1]
    assert 20 < left < 30 and "seconds left in this turn" in text
    g.apply(1, 0, _act(searches=[word] * 10, murderer={"name": m.suspects[0], "confidence": 50}))
    n = sum(e["kind"] == "search" and e["node"] == 1 for e in g.events)
    assert n == int((left - engine.ANSWER_SECONDS) // engine.SEARCH_SECONDS) and g.murderer[1]
    assert "Not enough time" in g.pending[1]["problems"][0]
    long = " ".join(["word"] * 30)  # 3 + 45 seconds of typing: never fits in one turn
    g.turn_text(1, 1)
    g.apply(1, 1, _act(messages=[{"to": [players[2]], "text": long, "share_clues": [], "reply_to": None, "forward": None}]))
    assert not g.messages
    g.pending[1]["search"] = ["x " * 300]  # 300 words: about 76 seconds of reading, carried into later turns
    g.turn_text(1, 2)
    assert g.available[1] == 0 and g.debt[1] > 40
    g.turn_text(1, 3)
    assert g.available[1] == 0 and g.debt[1] > 10


def test_turn_text_and_broadcasts():
    m, g = _game("Empty")
    for t in range(30):
        g.broadcast(t)
    assert sum(e["kind"] == "broadcast" for e in g.events) == 3
    text = g.turn_text(5, 0)
    assert "(you follow nobody)" in text and "Autopsy results" in text and "0:00 elapsed, 15:00 remaining" in text
    assert fill("turn", elapsed="1", remaining="2", updates="{odd} braces", own="", neighbours="") .count("{odd}") == 1


def test_scoring():
    m, g = _game("Empty")
    for t in range(30):
        if t == 10:
            g.apply(1, t, _act(victim=m.victim, murderer={"name": m.culprit, "confidence": 50}))
        if t == 20:
            g.apply(2, t, _act(murderer={"name": m.red_herring, "confidence": 50}))
        g.snapshot(t)
    out, pay = g.outcome(), g.earnings()
    assert out["num_correct"] == 1 and out["final"][1] == "correct" and out["final"][2] == "RH" and out["final"][3] == "none"
    assert pay[1] == round(0.40 + 0.14 * 2 * 9.5, 2) and pay[3] == 0.40


def test_schema_and_fake_turns():
    m, g = _game("InCorePeriphery")
    for n in networks.NODES:
        s = turn_schema(m.suspects, [m.victim] + m.suspects, g.recipients(n))
        assert ("messages" in s["properties"]) == bool(g.targets[n])
    fake = FakeModel(0, ["Hall", "Brown"])
    for t in range(30):
        g.broadcast(t)
        for n in networks.NODES:
            g.turn_text(n, t)
            g.apply(n, t, json.loads(fake([], "turn", turn_schema(m.suspects, [m.victim] + m.suspects, g.recipients(n)))[0]))
        g.snapshot(t)
    for msg in g.messages:  # messages only travel along ties
        assert all((msg["sender"], r) in networks.EDGES["InCorePeriphery"] for r in msg["to"])
    assert len(g.snapshots) == 30 and g.snapshots[-1]["seconds"] == 900


def test_trial_record_and_viewer():
    """A full fake trial with reasoning summaries: every main turn is recovered with its summary, and the page renders."""
    import tempfile
    import runner
    import viewer
    with tempfile.TemporaryDirectory() as d:
        path, status, _ = runner.run_trial("CorePeriphery", 1, 7, FakeModel(7, summary="auto"), Path(d))
        assert status == "complete"
        rec = json.loads(path.read_text())
        view = viewer.build(rec)
        for n, a in view["agents"].items():
            assert len(a["turns"]) == 30 and len(a["cells"]) == 30
            assert all(t["reasoning"] for t in a["turns"] + a["practice"])
            assert len(rec["agents"][n]["reasoning"]) == len(a["turns"]) + len(a["practice"])
        page, _, _ = viewer.write_trial(path, Path(d))
        assert "</script>" in page.read_text() and page.read_text().count("</script>") == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
