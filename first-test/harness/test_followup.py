"""Checks for the follow-up studies: every condition runs end to end with fake agents and delivers the intended prompts."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import followup as f


class FollowupTests(unittest.TestCase):
    def test_marking_tags_only_sole_held_ratings(self):
        tags = {r: f.task.information(r, cues=f.MONOPOLY_CUES, marked=True).count("(only you)") for r in f.task.ROLES}
        self.assertEqual(tags, {1: 4, 2: 0, 3: 1})
        self.assertEqual(f.task.information(1), f.task.information(1, cues=f.task.CUES, marked=False))

    def test_jobs_balance_opening_speakers(self):
        full = f.jobs("full")
        self.assertEqual(len(full), 12 * 3 + 6 * 6)
        for c in f.conditions():
            starts = sorted(j["first"] for j in full if j["condition"] == c["condition"])
            self.assertEqual(starts, [1, 2, 3] * (2 if c["monopoly"] else 1) if not c["monopoly"] else [1, 1, 2, 2, 3, 3])
        self.assertEqual(sum(6 + 3 * j["rounds"] for j in full), 648 + 756)

    def test_fake_run_of_every_condition_passes_checks(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp) / "cohort"
            f.prepare(root, "full", fake=True)
            results = f.groups(root, fake=True)
        self.assertEqual(len(results), 72)
        self.assertEqual([r["problems"] for r in results if r["problems"]], [])

    def test_check_catches_a_wrong_round_count(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp) / "cohort"
            f.prepare(root, "smoke", fake=True)
            path = sorted(Path(r["record"]) for r in f.groups(root, fake=True))[0]
            rec = json.loads((root / path).read_text())
        self.assertIn("speaking order", f.check(rec, {**rec["job"], "rounds": rec["job"]["rounds"] + 2}))


if __name__ == "__main__":
    unittest.main()
