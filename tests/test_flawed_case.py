"""Tests for the deliberately flawed case in ``samples/flawed-case/``.

The case plants three defects in otherwise correct results for guideline 1:
a paraphrased excerpt, a misattributed excerpt and a compliance/gap
disagreement. Each test shows that the defect is detectable from the sample
policies alone, and that the correct results in ``samples/expected/`` are clean.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import evidence  # noqa: E402

POLICIES = evidence.load_policies()
LABELS = evidence.load_json(evidence.EXPECTED_DIR / "policy-labels.json")["1"]
DEFECTS = evidence.load_json(evidence.FLAWED_DIR / "planted-defects.json")
FLAWED_COMPLIANCE = evidence.load_json(evidence.FLAWED_DIR / "guideline-1.compliance-checker.json")
FLAWED_GAP = evidence.load_json(evidence.FLAWED_DIR / "guideline-1.gap-identifier.json")
CLEAN_COMPLIANCE = evidence.load_json(evidence.EXPECTED_DIR / "guideline-1.compliance-checker.json")
CLEAN_GAP = evidence.load_json(evidence.EXPECTED_DIR / "guideline-1.gap-identifier.json")


def row_for(output: dict, key: str, clause: str) -> dict:
    """Return the clause row whose requirement starts with ``clause``."""
    for row in output[key]:
        if evidence.clause_number(row["SoG Requirement"]) == clause:
            return row
    raise KeyError(clause)


def defect(kind: str) -> dict:
    return next(item for item in DEFECTS["defects"] if item["type"] == kind)


def disagreements(compliance: dict, gap: dict):
    """Clauses rated Fully Compliant by one agent while the other reports a gap."""
    found = []
    for c_row, g_row in zip(compliance["Detailed Compliance Audit"], gap["Detailed Gap Audit"]):
        fully = c_row["Compliance Status"] == "✅Fully Compliant"
        if fully and g_row["Gap Outcome"] in {"PartialGap", "Gap"}:
            found.append(evidence.clause_number(c_row["SoG Requirement"]))
    return found


class PlantedDefectsFileTest(unittest.TestCase):
    def test_three_defects_on_three_clauses(self):
        self.assertEqual(DEFECTS["guideline"], "1")
        self.assertEqual([item["clause"] for item in DEFECTS["defects"]], ["1.2", "1.3", "1.4"])

    def test_every_defect_says_how_it_should_be_detected(self):
        for item in DEFECTS["defects"]:
            with self.subTest(clause=item["clause"]):
                self.assertTrue(item["description"])
                self.assertTrue(item["expected_detection"])

    def test_only_the_planted_rows_differ_from_the_clean_results(self):
        changed = []
        pairs = zip(FLAWED_COMPLIANCE["Detailed Compliance Audit"], CLEAN_COMPLIANCE["Detailed Compliance Audit"])
        for flawed_row, clean_row in pairs:
            if flawed_row != clean_row:
                changed.append(evidence.clause_number(flawed_row["SoG Requirement"]))
        self.assertEqual(changed, ["1.2", "1.3", "1.4"])
        self.assertEqual(FLAWED_GAP, CLEAN_GAP)


class ParaphrasedExcerptTest(unittest.TestCase):
    def setUp(self):
        self.defect = defect("paraphrased excerpt")
        self.row = row_for(FLAWED_COMPLIANCE, "Detailed Compliance Audit", self.defect["clause"])

    def test_paraphrase_is_not_found_in_any_policy(self):
        results = evidence.check_row(self.row, LABELS, POLICIES)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["found"])
        self.assertEqual(results[0]["found_in"], self.defect["found_in"])

    def test_the_verbatim_original_is_found(self):
        clean = row_for(CLEAN_COMPLIANCE, "Detailed Compliance Audit", self.defect["clause"])
        for result in evidence.check_row(clean, LABELS, POLICIES):
            with self.subTest(fragment=result["fragment"][:40]):
                self.assertTrue(result["found"])

    def test_paraphrase_keeps_the_meaning_but_not_the_wording(self):
        clean = row_for(CLEAN_COMPLIANCE, "Detailed Compliance Audit", self.defect["clause"])
        self.assertNotEqual(self.row["Policy Excerpt"], clean["Policy Excerpt"])
        self.assertIn("due diligence", self.row["Policy Excerpt"].lower())


class MisattributedExcerptTest(unittest.TestCase):
    def setUp(self):
        self.defect = defect("misattributed excerpt")
        self.row = row_for(FLAWED_COMPLIANCE, "Detailed Compliance Audit", self.defect["clause"])

    def test_excerpt_is_verbatim_but_cited_to_the_wrong_policy(self):
        results = evidence.check_row(self.row, LABELS, POLICIES)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["found"])
        self.assertFalse(results[0]["attribution_ok"])

    def test_found_in_names_the_real_document(self):
        result = evidence.check_row(self.row, LABELS, POLICIES)[0]
        self.assertEqual(result["cited"], [self.defect["cited"]])
        self.assertEqual(result["found_in"], self.defect["found_in"])

    def test_cited_lines_do_not_hold_the_excerpt(self):
        label, _, start, end = evidence.parse_references(self.row["Policy Reference"])[0]
        cited_lines = POLICIES[LABELS[label]]
        fragment = evidence.split_excerpt(self.row["Policy Excerpt"])[0]
        self.assertFalse(evidence.lines_contain(cited_lines, start, end, fragment))

    def test_clean_result_is_attributed_correctly(self):
        clean = row_for(CLEAN_COMPLIANCE, "Detailed Compliance Audit", self.defect["clause"])
        self.assertTrue(evidence.check_row(clean, LABELS, POLICIES)[0]["attribution_ok"])


class DisagreementTest(unittest.TestCase):
    def setUp(self):
        self.defect = defect("compliance/gap disagreement")

    def test_flawed_results_disagree_on_the_planted_clause_only(self):
        self.assertEqual(disagreements(FLAWED_COMPLIANCE, FLAWED_GAP), [self.defect["clause"]])

    def test_clean_results_do_not_disagree(self):
        self.assertEqual(disagreements(CLEAN_COMPLIANCE, CLEAN_GAP), [])

    def test_expected_reporter_status_is_the_conservative_one(self):
        gap_row = row_for(FLAWED_GAP, "Detailed Gap Audit", self.defect["clause"])
        self.assertEqual(gap_row["Gap Outcome"], "PartialGap")
        self.assertEqual(self.defect["expected_reporter_status"], "Partially Compliant")

    def test_evidence_itself_is_still_verbatim(self):
        row = row_for(FLAWED_COMPLIANCE, "Detailed Compliance Audit", self.defect["clause"])
        result = evidence.check_row(row, LABELS, POLICIES)[0]
        self.assertTrue(result["found"])
        self.assertTrue(result["attribution_ok"])


if __name__ == "__main__":
    unittest.main()
