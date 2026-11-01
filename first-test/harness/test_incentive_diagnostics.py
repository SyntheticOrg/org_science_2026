"""Local checks for the fixed diagnostic stimuli, payoff rules, and saved pipeline."""

import contextlib
import io
import itertools
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import incentive_diagnostics as d


class DiagnosticsTests(unittest.TestCase):
    def test_fixed_design_and_labels(self):
        self.assertEqual(d.MODELS, ("gpt-6-luna",))
        cases = d.cases()
        self.assertEqual(len(cases["diagnostics"]), 8)
        self.assertEqual(len(cases["disclosure"]), 16)
        self.assertEqual(len({c["id"] for group in cases.values() for c in group}), 24)
        full = [c for c in cases["diagnostics"] if c["family"] == "full-profile"]
        self.assertEqual(full[0]["expected"], {"A": 1, "B": 4, "C": 1})
        self.assertEqual(full[1]["expected"], {"C": 1, "A": 4, "B": 1})
        for c in cases["disclosure"]:
            self.assertNotIn("expected", c)
            self.assertEqual(c["options"]["O1"], "release" if c["repeat"] == 1 else "withhold")

    def test_original_payments_exhaustively(self):
        for votes in itertools.product("ABC", repeat=3):
            for condition in d.mp.MANIPULATIONS:
                actual = d.earnings(condition, list(votes))
                for role in (1, 2, 3):
                    count = votes.count("C" if role == 3 else "A")
                    bonus = False
                    if condition == "weak-buy" and role == 1:
                        bonus = count >= 2
                    elif condition == "weak-sell" and role == 1:
                        bonus = count <= 1
                    elif condition == "strong-buy":
                        bonus = count >= 2 if role == 3 else count == 3
                    elif condition == "strong-sell":
                        bonus = count <= 1 if role == 3 else count == 0
                    self.assertEqual(actual[str(role)], 10 + 4 * (votes.count("B") >= 2) + 5 * bonus)

    def test_all_diagnostic_answer_keys(self):
        for case in d.cases()["diagnostics"]:
            if case["family"] == "allocation":
                continue
            if case["family"] == "payment-calculation":
                answer = case["expected"]
            else:
                order = sorted("ABC", key=lambda a: -case["expected"][a])
                answer = {"scores": case["expected"], "ranking": dict(zip(("first", "second", "third"), order))}
            self.assertTrue(d.assess(case, answer)["all_correct"])
        case = d.cases()["diagnostics"][0]
        self.assertFalse(d.assess(case, {"scores": {"A": 1, "B": 5, "C": 1},
                                       "ranking": {"first": "B", "second": "C", "third": "A"}})["all_correct"])
        with self.assertRaises(AssertionError):
            d.assess(case, {"scores": case["expected"], "ranking": {"first": "B", "second": "B", "third": "A"}})

    def test_transcript_contains_last_turn_fact(self):
        case = next(c for c in d.cases()["diagnostics"] if c["family"] == "transcript")
        self.assertEqual(case["prompt"].count("Round "), 15)
        self.assertEqual(case["prompt"].count("applicant B's motivation is negative"), 1)
        self.assertIn("Round 5, participant 1: One additional fact", case["prompt"])

    def test_behavioral_choices_are_not_comprehension_scores(self):
        for case in d.cases()["diagnostics"]:
            if case["family"] != "allocation":
                continue
            group = next(k for k, v in case["options"].items() if v == "group")
            result = d.assess(case, {f"private_{x}": group for x in d.COSTS})
            self.assertNotIn("all_correct", result)
            self.assertEqual(result["own_money_max_choices"], 2)

    def test_costs_and_reimbursements(self):
        for case in d.cases()["disclosure"]:
            for label, action in case["options"].items():
                result = d.assess(case, {"choice": label})
                self.assertEqual(result["earnings"], d.disclosure_payoffs(case["cost"], case["reimbursed"], action == "release"))
                self.assertTrue(all(x >= 0 for x in result["earnings"].values()))
                expected = "release" if case["reimbursed"] or case["cost"] < 4 else "withhold"
                self.assertEqual(result["own_money_max_choice"], action == expected)
        self.assertLess(sum(d.disclosure_payoffs(13, False, True).values()), 30)
        self.assertGreater(sum(d.disclosure_payoffs(5, False, True).values()), 30)

    def test_request_cap_and_no_http_retry(self):
        model = object.__new__(d.ProbeModel)
        with patch.object(d.OpenAIModel, "_post", return_value={"model": "returned-id"}) as post:
            response = model._post({"store": False})
        self.assertEqual(post.call_args.kwargs["attempts"], 1)
        self.assertEqual(model.request["max_output_tokens"], 8192)
        self.assertFalse(model.request["store"])
        self.assertIs(model.response, response)

    def test_fake_pipeline_preserves_counts_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory) / "pilot"
            first = d.run(root, "diagnostics", fake=True)
            self.assertEqual(first["diagnostics"]["attempted"], 16)
            with self.assertRaises(FileExistsError):
                d.run(root, "diagnostics", fake=True)
            second = d.run(root, "disclosure", fake=True)
            self.assertEqual(second["disclosure"]["complete"], 32)
            self.assertEqual({r["model"] for r in d.records(root, "disclosure")}, {"gpt-6-luna"})
            self.assertEqual(second["usage"]["input_tokens"], 0)
            self.assertIn("FAKE PIPELINE CHECK", (root / "report.html").read_text())
            with self.assertRaises(FileExistsError):
                d.run(root, "disclosure", fake=True)

    def test_historical_reporting_uses_saved_model_scope(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            d.atomic(root / "config.json", {"models": ["gpt-6-luna", "gpt-5.4-mini-2026-03-17"],
                                           "frames": d.FRAMES, "fake": True})
            d.atomic(root / "cases.json", d.cases())
            result = d.report(root)
            self.assertEqual(result["diagnostics"]["planned"], 32)
            self.assertEqual(result["disclosure"]["planned"], 64)
            self.assertIn("gpt-5.4-mini-2026-03-17", (root / "report.html").read_text())


if __name__ == "__main__":
    unittest.main()
