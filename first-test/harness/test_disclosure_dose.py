"""Checks for the dose pilot's payments, information inference, and isolated records."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import disclosure_dose as d


def empty_codes():
    return {s: {f"round_{r}": {"rating_claims": [], "positive_bounds": [], **{
        k: {"value": False, "evidence": ""} for k in ("target_advocacy", "payment_disclosure", "information_request")}}
        for r in range(1, 6)} for s in d.task.ROLES}


class DisclosureDoseTests(unittest.TestCase):
    def setUp(self):
        self.side = d.mp.DISCUSSION_SIDE_GBP

    def tearDown(self):
        d.mp.DISCUSSION_SIDE_GBP = self.side

    def test_all_amounts_preserve_thresholds_and_actual_payoffs(self):
        for b in d.AMOUNTS:
            d.mp.DISCUSSION_SIDE_GBP = b
            side = lambda votes: [d.mp.discussion_side_payment("strong-buy", r, list(votes)) for r in d.task.ROLES]
            self.assertEqual(side("AAA"), [b, b, 0])
            self.assertEqual(side("AAB"), [0, 0, 0])
            self.assertEqual(side("CCC"), [0, 0, b])
            self.assertEqual(side("BBC"), [0, 0, 0])
            for role in d.task.ROLES:
                text = d.briefing("discussion", d.mp.key("discussion", "strong-buy", role), "no-quiz", "neutral-final")
                self.assertIn(f"£{b}", text)
                self.assertNotIn("short quiz", text)

    def test_aggregate_information_infers_rating_without_named_cue(self):
        before = d.knowledge(1, {"B_personal_skills": -1}, [])
        self.assertNotIn("experience", before["B"]["ratings"])
        after = d.knowledge(1, {"B_personal_skills": -1}, [("B", 3, 3)])
        self.assertEqual(after["B"]["ratings"]["experience"], 1)
        self.assertEqual(after["B"]["scores"], [4])

    def test_other_speakers_close_information_gaps(self):
        transcript = [{"round": rnd, "speaker": s, "message": "Evidence.", "note": "private"}
                      for rnd in range(1, 6) for s in ((1, 2, 3) if rnd % 3 == 1 else (2, 3, 1) if rnd % 3 == 2 else (3, 1, 2))]
        rec = {"discussion": {"transcript": transcript}}
        coded = empty_codes()
        self.assertEqual(d.analyse(rec, coded)["primary_gap_score"], 1)
        coded[1]["round_1"]["rating_claims"] = [
            {"fact": f, "rating": v, "correction": False, "evidence": "Evidence."} for f, (_, _, v) in d.FACTS.items()]
        result = d.analyse(rec, coded)
        self.assertEqual(result["primary_gap_score"], 0)
        self.assertEqual(result["role_gap_scores"][3], 0)

    def test_conflicting_claims_need_a_correct_correction(self):
        order = [s for rnd in range(1, 6) for s in ((1, 2, 3) if rnd % 3 == 1 else (2, 3, 1) if rnd % 3 == 2 else (3, 1, 2))]
        transcript = [{"round": i // 3 + 1, "speaker": s, "message": "Claim.", "note": ""} for i, s in enumerate(order)]
        codes = empty_codes()
        claim = {"fact": "B_experience", "rating": -1, "correction": False, "evidence": "Claim."}
        codes[2]["round_1"]["rating_claims"] = [claim]
        codes[2]["round_2"]["rating_claims"] = [{**claim, "rating": 1}]
        codes[2]["round_3"]["rating_claims"] = [{**claim, "rating": 1, "correction": True}]
        result = d.analyse({"discussion": {"transcript": transcript}}, codes)
        self.assertNotIn("experience", result["timeline"][3]["verified_states"][1]["B"]["ratings"])
        self.assertEqual(result["timeline"][8]["verified_states"][1]["B"]["ratings"]["experience"], 1)
        self.assertEqual(len(result["incorrect_claims"]), 1)

    def test_quotation_provenance_is_required(self):
        rec = {"discussion": {"transcript": [{"round": r, "speaker": 1, "message": "Actual text."} for r in range(1, 6)]}}
        codes = empty_codes()[1]
        d.check_quotes(rec, 1, codes)
        codes["round_1"]["target_advocacy"] = {"value": True, "evidence": "Invented quotation"}
        with self.assertRaises(AssertionError):
            d.check_quotes(rec, 1, codes)

    def test_fake_pipeline_preserves_private_rules_and_final_transcript(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp) / "pilot"
            d.prepare(root, True)
            d.groups(root, True)
            d.code(root, True)
            report = d.report(root)
            self.assertEqual(len(report["groups"]), 8)
            self.assertEqual(report["api_calls"], 0)
            self.assertEqual(report["primary_5_minus_0"], 0)
            for path, rec in d.records(root):
                self.assertEqual(rec["status"], "complete")
                self.assertEqual(len(rec["discussion"]["transcript"]), 15)
                self.assertEqual(sum(a["usage"]["calls"] for a in rec["agents"].values()), 21)
                for role in d.task.ROLES:
                    messages = rec["agents"][str(role)]["messages"]
                    self.assertIn(f"£{rec['discussion_side_gbp']}", messages[1]["content"])
                    self.assertIn(d.task.information(role), messages[1]["content"])
                    for turn in rec["discussion"]["transcript"]:
                        self.assertIn(turn["message"], messages[-2]["content"])
                self.assertEqual(rec["outcome"]["side_gbp"], {"1": 0, "2": 0, "3": 0})
            with self.assertRaises(FileExistsError):
                d.prepare(root, True)
            cfg = json.loads((root / "config.json").read_text())
            cfg["source_sha256"]["runner.py"] = "changed"
            d.atomic(root / "config.json", cfg)
            with self.assertRaises(AssertionError):
                d.guard(root, True)


if __name__ == "__main__":
    unittest.main()
