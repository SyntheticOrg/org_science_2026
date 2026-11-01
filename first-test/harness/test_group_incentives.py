"""Local checks for conditional incentives, information isolation, and the group pipeline."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import group_incentives as g
import task
from agent import fill
from runner import run_triad


class GroupIncentivesTests(unittest.TestCase):
    def test_pivotal_and_nonpivotal_payments(self):
        cases = g.conditional_cases()
        self.assertEqual(len(cases), 12)
        expected = {"control-pivotal": ["B"], "weak-buy-pivotal": ["A"],
                    "weak-buy-nonpivotal": list("ABC"), "strong-buy-A-pivotal": ["A"],
                    "strong-buy-C-pivotal": ["C"], "strong-buy-C-blocked": list("ABC")}
        for case in cases:
            self.assertEqual(case["maximising_choices"], expected[case["case"]])
            self.assertNotIn("quiz", case["messages"][1]["content"].lower())
            self.assertNotIn("Round", case["messages"][1]["content"])
        weak = next(c for c in cases if c["case"] == "weak-buy-pivotal")
        self.assertEqual(weak["own_earnings"], {"A": 15, "B": 14, "C": 10})

    def test_information_regimes_and_payment_privacy(self):
        with tempfile.TemporaryDirectory() as directory:
            for regime in g.REGIMES:
                for manipulation in g.MANIPS:
                    path, status, _ = run_triad("discussion", 1, 7, g.FixedFake(7), Path(directory), manipulation,
                                               "no-quiz", g.VARIANT, information_regime=regime)
                    rec = json.loads(path.read_text())
                    self.assertEqual(status, "complete")
                    self.assertEqual(rec["information_regime"], regime)
                    self.assertNotIn("quiz", rec)
                    self.assertEqual(len(rec["discussion"]["transcript"]), 15)
                    for role in task.ROLES:
                        messages = rec["agents"][str(role)]["messages"]
                        first = messages[1]["content"]
                        information = task.information(role, complete=regime == "complete")
                        self.assertIn(information, first)
                        ratings = sum(information.count(x) for x in ("positive", "negative"))
                        self.assertEqual(ratings, 15 if regime == "complete" else 9)
                        self.assertEqual(first.count("Your private payment"), int(bool(rec["pay_keys"][str(role)])))
                        for other in task.ROLES:
                            key = rec["pay_keys"][str(other)]
                            if key and key != rec["pay_keys"][str(role)]:
                                self.assertNotIn(fill(f"rule_{key}", **g.mp.pay_values()), first)
                        self.assertTrue(messages[-2]["content"].endswith(fill("ranking_after_discussion_open")))
                        for turn in rec["discussion"]["transcript"]:
                            self.assertIn(turn["message"], messages[-2]["content"])

    def test_complete_information_not_available_to_market(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_triad("market", 1, 7, g.FixedFake(), Path(directory), information_regime="complete")
            with self.assertRaises(ValueError):
                run_triad("discussion", 1, 7, g.FixedFake(), Path(directory), information_regime="unknown")

    def test_staged_fake_pipeline_and_no_cue_coding_for_complete_profiles(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory) / "pilot"
            self.assertEqual(g.run(root, "conditional", True)["conditional_complete"], 12)
            self.assertEqual(g.run(root, "groups", True)["group_complete"], 12)
            summary = g.run(root, "code", True)
            self.assertEqual(summary["coded_participants"], 36)
            self.assertEqual(summary["api_calls"], 0)
            self.assertEqual(len(summary["cells"]), 6)
            for p in (root / "coding").glob("*/*.json"):
                r = json.loads(p.read_text())
                self.assertEqual("cues" in r, r["regime"] == "distributed")
            for cell in summary["cells"]:
                self.assertEqual(cell["mean_b_votes"], 3)
                self.assertEqual(cell["paid_profitable_unilateral_deviations"], 0)
            with self.assertRaises(FileExistsError):
                g.run(root, "conditional", True)
            with self.assertRaises(FileExistsError):
                g.run(root, "groups", True)
            with self.assertRaises(FileExistsError):
                g.run(root, "code", True)

    def test_source_change_blocks_continuation(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory) / "pilot"
            g.run(root, "conditional", True)
            config = json.loads((root / "config.json").read_text())
            config["source_sha256"]["runner.py"] = "changed"
            g.atomic(root / "config.json", config)
            with self.assertRaises(AssertionError):
                g.run(root, "groups", True)


if __name__ == "__main__":
    unittest.main()
