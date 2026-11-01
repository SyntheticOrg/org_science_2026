"""Checks for scoring, information isolation, and market accounting. Run: python3 test_core.py"""

import json
import random

import task
from market import InvalidAction, Market


def test_task():
    assert task.SCORES == {"A": 1, "B": 4, "C": 1}
    assert task.BEST == "B"
    for role in task.ROLES:
        assert all(len(task.CUES[role][a]) == 3 for a in task.APPLICANTS)
    # Each role sees B tied for first; pooling yields B uniquely (weak hidden profile, see APPROACH.md).
    assert {r: {a: task.strength(task.CUES[r][a]) for a in "ABC"} for r in task.ROLES} == {
        1: {"A": 3, "B": 3, "C": 0}, 2: {"A": 3, "B": 3, "C": 0}, 3: {"A": 0, "B": 3, "C": 3}}
    assert task.correct(["B", "C", "A"]) and not task.correct(["A", "B", "C"])
    assert not task.is_ranking(["B", "B", "A"])


def test_information_isolation():
    for role in task.ROLES:
        text = task.information(role)
        shown = sum(text.count(w) for w in ("positive", "negative"))
        assert shown == 9, (role, shown)
        for a in task.APPLICANTS:
            line = next(l for l in text.splitlines() if l.startswith(f"Applicant {a}:"))
            shown_attrs = {p.split(":")[0].strip() for p in line.split(": ", 1)[1].split(";")}
            assert shown_attrs == set(task.CUES[role][a]), (role, a, shown_attrs)
        assert "strength" not in text.lower() and "best" not in text.lower()


def test_market_rules():
    m = Market([1, 2, 3])
    bid = m.bid(1, "B", 60)
    assert m.available_cash(1) == 140
    try:
        m.bid(1, "B", 141)
        assert False
    except InvalidAction:
        pass
    # Own orders cannot be accepted or crossed.
    try:
        m.sell(1, "B")
        assert False
    except InvalidAction:
        pass
    assert m.ask(1, "B", 50).side == "ask"  # rests: the only bid at 60 is trader 1's own
    # Crossing ask from another trader trades at the standing bid's price.
    assert m.ask(2, "B", 40) == ("B", 60, 1, 2)
    assert bid not in m.orders and m.cash[1] == 140 and m.cash[2] == 260
    # Buy accepts the lowest ask from someone else, price-time priority.
    m.ask(3, "A", 30)
    m.ask(2, "A", 30)
    assert m.buy(1, "A") == ("A", 30, 1, 3)
    # No short selling beyond available shares.
    m.ask(3, "C", 10)
    m.ask(3, "C", 11)
    try:
        m.ask(3, "C", 12)
        assert False
    except InvalidAction:
        pass
    # Cancel only own orders.
    other = next(o for o in m.orders if o.trader == 3)
    try:
        m.cancel(1, other.id)
        assert False
    except InvalidAction:
        pass
    m.cancel(3, other.id)
    for bad in (-1, 201, 10.5, True):
        try:
            m.bid(1, "A", bad)
            assert False, bad
        except InvalidAction:
            pass
    assert "#" not in m.state(2).split("Your open orders")[0]  # book shows no order ids or traders
    assert m.spreads()["B"] == 50 + 40 - 60


def test_market_conservation():
    rng = random.Random(0)
    for _ in range(200):
        m = Market([1, 2, 3])
        for _ in range(300):
            t, a = rng.choice([1, 2, 3]), rng.choice("ABC")
            act = rng.choice(["bid", "ask", "buy", "sell", "cancel"])
            try:
                if act in ("bid", "ask"):
                    getattr(m, act)(t, a, rng.randint(0, 200))
                elif act == "cancel":
                    m.cancel(t, rng.randint(1, 50))
                else:
                    getattr(m, act)(t, a)
            except InvalidAction:
                pass
            assert sum(m.cash.values()) == 600
            for x in "ABC":
                assert sum(m.shares[s][x] for s in m.cash) == 6
            for s in m.cash:
                assert m.available_cash(s) >= 0 and m.cash[s] >= 0
                assert all(m.available_shares(s, x) >= 0 for x in "ABC")


def test_fake_triads():
    """Full pipeline without API calls: records complete, each agent sees only its own cues."""
    import tempfile
    from pathlib import Path

    from agent import FakeModel
    from runner import run_triad

    with tempfile.TemporaryDirectory() as d:
        for condition in ("discussion", "market"):
            path, status, outcome = run_triad(condition, 1, 7, FakeModel(7), Path(d))
            assert status == "complete", status
            rec = json.loads(path.read_text())
            for role, a in rec["agents"].items():
                seen = "\n".join(m["content"] for m in a["messages"])
                assert task.information(int(role)) in seen
                for other in task.ROLES:
                    if other != int(role):
                        assert task.information(other) not in seen
            if condition == "market":
                p = rec["market"]["periods"][rec["market"]["paid_period"] - 1]
                assert rec["market"]["payoff_gbp"] == {t: 2 * p["shares_end"][t]["B"] + p["cash_end"][t] / 50 for t in p["shares_end"]}


def test_manipulation_payoffs():
    import itertools

    import manipulations as mp

    def payoff(m, r, firsts, best="B"):
        return mp.discussion_side_payment(m, r, firsts) + (4 if firsts.count(best) >= 2 else 0)

    # Which roles can earn more than when all rank B first (APPROACH.md, Incentive structure).
    conflict = {}
    for m in mp.MANIPULATIONS[1:]:
        allb = {r: payoff(m, r, ["B"] * 3) for r in task.ROLES}
        best = {r: max(payoff(m, r, list(f)) for f in itertools.product("ABC", repeat=3)) for r in task.ROLES}
        conflict[m] = ([r for r in task.ROLES if best[r] > allb[r]], allb)
    assert conflict == {
        "weak-buy": ([1], {1: 4, 2: 4, 3: 4}), "weak-sell": ([], {1: 9, 2: 4, 3: 4}),
        "strong-buy": ([1, 2, 3], {1: 4, 2: 4, 3: 4}), "strong-sell": ([], {1: 9, 2: 9, 3: 9})}

    # Every payment quiz answer agrees with the payoff code: (manipulation, role, firsts, best) per item.
    from agent import parse_quiz
    cases = {
        "discussion_weak_buy_role1": [("weak-buy", 1, "AAC", "C"), ("weak-buy", 1, "CCC", "C")],
        "discussion_weak_sell_role1": [("weak-sell", 1, "CCA", "C"), ("weak-sell", 1, "AAA", "C")],
        "discussion_strong_buy_role12": [("strong-buy", 1, "AAC", "C"), ("strong-buy", 2, "AAA", "C")],
        "discussion_strong_buy_role3": [("strong-buy", 3, "CCA", "A"), ("strong-buy", 3, "AAA", "A")],
        "discussion_strong_sell_role12": [("strong-sell", 1, "CCC", "C"), ("strong-sell", 2, "CCA", "C")],
        "discussion_strong_sell_role3": [("strong-sell", 3, "AAC", "A"), ("strong-sell", 3, "CCC", "A")],
    }
    for side in (5, 20, 100):  # the paper's £5 and the experiment 3 amounts
        mp.DISCUSSION_SIDE_GBP = side
        gbp = {"a": 0, "b": 4, "c": side, "d": side + 4}
        for k, items in cases.items():
            for it, (m, r, firsts, best) in zip(parse_quiz(f"quiz_pay_{k}", **mp.pay_values()), items):
                assert mp.key("discussion", m, r) == k
                assert gbp[it["answer"]] == payoff(m, r, list(firsts), best), (side, k, it["question"])
                assert f"£{side}" in it["question"]
    mp.DISCUSSION_SIDE_GBP = 5

    # Market: count only the target, only the paid role's side of the trade.
    trades = [("A", 50, 1, 2), ("A", 60, 1, 3), ("C", 40, 3, 1), ("A", 70, 2, 1), ("B", 90, 1, 2)]
    assert mp.market_side_payment("weak-buy", 1, trades) == 5.0
    assert mp.market_side_payment("weak-sell", 1, trades) == 2.5
    assert mp.market_side_payment("strong-buy", 3, trades) == 2.5
    assert mp.market_side_payment("strong-sell", 3, trades) == 0
    assert mp.market_side_payment("control", 1, trades) == 0
    assert mp.key("market", "strong-sell", 3) == "market_sell_C" and mp.key("market", "weak-buy", 2) is None


def test_fake_manipulated_triads():
    """Paid agents see their own rule and reminders; unpaid agents never see payment text."""
    import tempfile
    from pathlib import Path

    from agent import FakeModel
    from runner import run_triad

    with tempfile.TemporaryDirectory() as d:
        for condition, manipulation in (("discussion", "strong-buy"), ("market", "weak-sell"), ("market", "control")):
            path, status, _ = run_triad(condition, 1, 3, FakeModel(3), Path(d), manipulation)
            assert status == "complete"
            rec = json.loads(path.read_text())
            assert set(rec["outcome"]["side_gbp"]) == {"1", "2", "3"}
            for role, a in rec["agents"].items():
                key = rec["pay_keys"][role]
                users = [m["content"] for m in a["messages"] if m["role"] == "user"]
                seen = "\n".join(users)
                if key:
                    assert "Your private payment" in users[0]
                    turns = [u for u in users if u.startswith("Reminder of your private payment")]
                    assert len(turns) == (5 if condition == "discussion" else 100)
                else:
                    assert "private payment" not in seen and "£2.50" not in seen and "additional £5" not in seen


def test_fake_open_protocol():
    """Open protocol: no quiz, no ranking before the discussion; instructions, payment rule, and information open turn 1."""
    import tempfile
    from pathlib import Path

    from agent import FakeModel
    from runner import run_triad

    with tempfile.TemporaryDirectory() as d:
        path, status, _ = run_triad("discussion", 1, 3, FakeModel(3), Path(d), "strong-buy", protocol="open")
        rec = json.loads(path.read_text())
        assert status == "complete" and rec["protocol"] == "open" and "quiz" not in rec and "ranking_before" not in rec
        for role, a in rec["agents"].items():
            users = [m["content"] for m in a["messages"] if m["role"] == "user"]
            assert "quiz" not in "\n".join(users).lower() and "best to worst" not in "\n".join(users)
            assert all(x in users[0] for x in ("Strength =", "Your private payment", "Your information:", "is up to you", "Discussion round 1 of 5"))
            assert any("The discussion has ended. Submit your final private ranking" in u for u in users)


def test_prompt_sensitivity():
    """Wording variants retain the paper procedure, isolated information, and payoffs."""
    import tempfile
    from pathlib import Path

    from agent import FakeModel, fill
    from runner import PROMPT_VARIANTS, run_triad

    with tempfile.TemporaryDirectory() as d:
        histories = {}
        for variant in PROMPT_VARIANTS:
            path, status, _ = run_triad("discussion", 1, 3, FakeModel(3), Path(d), "strong-buy", prompt_variant=variant)
            r = json.loads(path.read_text())
            assert status == "complete" and r["prompt_variant"] == variant and r["discussion_side_gbp"] == 5
            assert len(r["discussion"]["transcript"]) == 15 and "quiz" in r and "ranking_before" in r
            for role, a in r["agents"].items():
                expected = "system_simulation" if variant in ("simulation", "combined") else "system"
                assert a["messages"][0]["content"] == fill(expected, role=role)
                users = [m["content"] for m in a["messages"] if m["role"] == "user"]
                assert (fill("disclosure_discretion") in users[0]) == (variant in ("privacy", "combined"))
                assert "Before you continue" in users[0] and "Your private payment" in users[0]
                assert any("best to worst, individually and privately" in u for u in users)
                assert any(u.endswith(fill("ranking_after_discussion_open" if variant in ("neutral-final", "combined") else "ranking_after_discussion")) for u in users)
            histories[variant] = r["agents"]["1"]["messages"]
        final_index = next(i for i, m in enumerate(histories["baseline"]) if m["content"].endswith(fill("ranking_after_discussion")))
        assert histories["baseline"][:final_index] == histories["neutral-final"][:final_index]
        try:
            run_triad("market", 1, 3, FakeModel(3), Path(d), prompt_variant="privacy")
            assert False
        except ValueError:
            pass


def test_no_quiz_sensitivity():
    """Every sensitivity arm gets instructions and cues, but no quiz or quiz priming."""
    import tempfile
    from pathlib import Path

    from agent import FakeModel
    from runner import PROMPT_VARIANTS, run_triad

    with tempfile.TemporaryDirectory() as d:
        for variant in PROMPT_VARIANTS:
            path, status, _ = run_triad("discussion", 1, 7, FakeModel(7), Path(d), "strong-buy", "no-quiz", variant)
            r = json.loads(path.read_text())
            assert status == "complete" and r["protocol"] == "no-quiz" and "quiz" not in r and "ranking_before" in r
            assert len(r["discussion"]["transcript"]) == 15
            for a in r["agents"].values():
                users = [m["content"] for m in a["messages"] if m["role"] == "user"]
                assert "quiz" not in "\n".join(users).lower()
                assert all(text in users[0] for text in ("Strength =", "Your private payment", "Your information:", "best to worst"))


def test_final_discussion_delivery():
    """Every voter sees every public turn, including the last correction, without others' notes."""
    import tempfile
    from pathlib import Path

    from agent import FakeModel
    from runner import PROMPT_VARIANTS, run_triad

    class DistinctMessages(FakeModel):
        turn = 0

        def __call__(self, messages, name, schema):
            text, usage = super().__call__(messages, name, schema)
            if name == "message":
                self.turn += 1
                text = json.dumps({"message": f"PUBLIC_TURN_{self.turn:02d}_END",
                                   "note": f"PRIVATE_NOTE_{self.turn:02d}_END"})
            elif name == "ranking":
                text = json.dumps({"first": "B", "second": "A", "third": "C"})
            return text, usage

    with tempfile.TemporaryDirectory() as d:
        for protocol in ("paper", "no-quiz", "open"):
            for variant in (("baseline",) if protocol == "open" else PROMPT_VARIANTS):
                path, status, _ = run_triad("discussion", 1, 7, DistinctMessages(7), Path(d),
                                            "strong-buy", protocol, variant)
                assert status == "complete"
                rec = json.loads(path.read_text())
                assert rec["final_transcript_included"] is True
                turns = rec["discussion"]["transcript"]
                assert len(turns) == 15 and turns[-1]["speaker"] == 1
                for role, agent in rec["agents"].items():
                    final_prompt = agent["messages"][-2]["content"]
                    for turn in turns:
                        assert turn["message"] in final_prompt, (protocol, variant, role, turn["message"])
                        assert turn["note"] not in final_prompt
                    assert final_prompt.count("Participant ") == 15


def test_vllm_adapter():
    import io
    from unittest.mock import patch

    from agent import ModelError, RANKING
    from vllm_model import VLLMModel

    answer = {"first": "A", "second": "B", "third": "C"}
    payload = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer), "reasoning": "PRIVATE_REASONING"}}],
               "usage": {"prompt_tokens": 10, "completion_tokens": 12, "completion_tokens_details": {"reasoning_tokens": 7}}}
    model = VLLMModel("test-model", {})
    with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as post:
        text, usage = model([{"role": "user", "content": "rank"}], "ranking", RANKING)
        assert json.loads(text) == answer and usage["output_tokens"] == 12 and usage["reasoning_tokens"] == 7
        assert "PRIVATE_REASONING" not in text and model.effort == "thinking"
        request = post.call_args.args[0]
        body = json.loads(request.data)
        assert body["response_format"]["json_schema"]["schema"] == RANKING
        assert body["chat_template_kwargs"] == {"enable_thinking": True}
        assert body["max_tokens"] == 8192 and body["temperature"] == 0.6 and body["top_p"] == 0.95
        assert request.full_url.startswith("http://127.0.0.1:")
    old_mode = VLLMModel("test-model", {"enable_thinking": False, "max_tokens": 1024, "temperature": 0.7, "top_p": 0.8})
    with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as post:
        old_mode([], "ranking", RANKING)
        body = json.loads(post.call_args.args[0].data)
        assert body["chat_template_kwargs"] == {"enable_thinking": False} and body["max_tokens"] == 1024
        assert body["temperature"] == 0.7 and body["top_p"] == 0.8 and old_mode.effort is None
    try:
        VLLMModel("cmu-lti/osim-8b", {})
        assert False
    except ValueError as error:
        assert "thinking has not passed preflight" in str(error)
    assert VLLMModel("cmu-lti/osim-8b", {"enable_thinking": False}).effort is None
    payload["choices"][0]["finish_reason"] = "length"
    with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
        try:
            model([], "ranking", RANKING)
            assert False
        except ModelError:
            pass
    payload["choices"][0]["finish_reason"] = "stop"
    payload["choices"][0]["message"]["content"] = ""
    with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
        try:
            model([], "ranking", RANKING)
            assert False
        except ModelError as error:
            assert "no final text content" in str(error)
    try:
        VLLMModel("test", {}, "http://example.com/v1/chat/completions", "Bearer test")
        assert False
    except ValueError:
        pass


def test_cue_coder_round_selection():
    from agent import FakeModel
    from code_transcripts import code_cues

    class RecordingModel(FakeModel):
        def __call__(self, messages, name, schema):
            self.prompt = messages[0]["content"]
            return super().__call__(messages, name, schema)

    model = RecordingModel()
    rec = {"discussion": {"transcript": [{"speaker": 1, "round": 1, "message": "EARLY"},
                                         {"speaker": 1, "round": 2, "message": "LATE"},
                                         {"speaker": 2, "round": 1, "message": "OTHER"}]}}
    cues, _ = code_cues(model, rec, 1, first_round=True)
    assert len(cues) == 9 and "EARLY" in model.prompt and "LATE" not in model.prompt and "OTHER" not in model.prompt
    code_cues(model, rec, 1)
    assert "LATE" in model.prompt and "OTHER" not in model.prompt


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
