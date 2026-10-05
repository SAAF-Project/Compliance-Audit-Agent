"""Tests for the prompt builders in ``scripts/build_prompt.py``.

They need no API key and no policy data: every test only inspects the text
that would be sent to the model.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_prompt  # noqa: E402

GUIDELINE = "\n".join([
    "Guideline 1 – Outsourcing of critical or important functions",
    "1.1. The undertaking should establish a written outsourcing policy.",
    "1.2. The undertaking should perform a documented due diligence.",
])
GUIDELINE_TITLE = "Guideline 1 – Outsourcing of critical or important functions"


def json_blocks(prompt: str):
    """Yield every top-level ``{...}`` block of a prompt as a parsed object."""
    depth, start = 0, None
    for position, char in enumerate(prompt):
        if char == "{":
            if depth == 0:
                start = position
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                yield json.loads(prompt[start:position + 1])
                start = None


class WithLineNumbersTest(unittest.TestCase):
    def test_numbers_start_at_zero_by_default(self):
        numbered = build_prompt.with_line_numbers(["first", "second"])
        self.assertEqual(numbered.split("\n"), [" 0 | first", " 1 | second"])

    def test_custom_start(self):
        numbered = build_prompt.with_line_numbers(["a", "b"], start=9)
        self.assertEqual(numbered.split("\n"), [" 9 | a", "10 | b"])

    def test_width_grows_with_the_highest_number(self):
        numbered = build_prompt.with_line_numbers(["x"] * 101).split("\n")
        self.assertTrue(numbered[0].startswith("  0 | "))
        self.assertTrue(numbered[100].startswith("100 | "))
        self.assertEqual(len({line.index("|") for line in numbered}), 1)

    def test_line_text_is_kept_verbatim(self):
        text = "  indented | with a pipe  "
        numbered = build_prompt.with_line_numbers([text])
        self.assertTrue(numbered.endswith(f"| {text}"))

    def test_one_output_line_per_input_line(self):
        lines = ["a", "", "c", ""]
        self.assertEqual(len(build_prompt.with_line_numbers(lines).split("\n")), len(lines))


class AgentDescriptionTest(unittest.TestCase):
    DESCRIPTIONS = (
        "agent_description_selector",
        "agent_description_checker",
        "agent_description_gap",
        "agent_description_reporter",
    )

    def test_every_agent_has_a_description(self):
        for name in self.DESCRIPTIONS:
            with self.subTest(name=name):
                description = getattr(build_prompt, name)
                self.assertIsInstance(description, str)
                self.assertGreater(len(description.strip()), 50)

    def test_descriptions_are_distinct(self):
        texts = {getattr(build_prompt, name).strip() for name in self.DESCRIPTIONS}
        self.assertEqual(len(texts), len(self.DESCRIPTIONS))

    def test_selector_description_forbids_assessment(self):
        self.assertIn("no compliance assessment", normalise_spaces(build_prompt.agent_description_selector))


class SelectorPromptTest(unittest.TestCase):
    def setUp(self):
        self.prompt = build_prompt.selector_prompt(1, GUIDELINE)

    def test_contains_the_guideline_verbatim(self):
        self.assertIn(GUIDELINE, self.prompt)

    def test_states_threshold_and_maximum(self):
        self.assertIn("confidence ≥ 0.80", normalise_spaces(self.prompt))
        self.assertIn("max eight", self.prompt)
        self.assertIn("top three", self.prompt)

    def test_scoring_weights_add_up_to_one_hundred(self):
        section = self.prompt.split("Score Each Document")[1].split("Selection Rules")[0]
        weights = [int(value) for value in re.findall(r"- (\d+)% ", section)]
        self.assertEqual(len(weights), 5)
        self.assertEqual(sum(weights), 100)

    def test_schema_example_is_valid_json(self):
        schema = next(json_blocks(self.prompt))
        self.assertEqual(schema["threshold"], 0.80)
        self.assertEqual(
            set(schema["policies"][0]),
            {"rank", "title", "document_type", "owner", "last_reviewed", "confidence", "rationale"},
        )

    def test_guardrails_forbid_invented_content(self):
        for phrase in ("fabricate any information", "paraphrase policy titles", "assess compliance"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.prompt)

    def test_failure_handling_returns_an_empty_list(self):
        self.assertIn("an empty `policies` array", self.prompt)


class CompliancePromptTest(unittest.TestCase):
    def setUp(self):
        self.prompt = build_prompt.compliance_prompt(1, GUIDELINE)
        self.schema = next(json_blocks(self.prompt))

    def test_contains_the_guideline_verbatim(self):
        self.assertIn(GUIDELINE, self.prompt)

    def test_guideline_number_and_title_are_filled_in(self):
        self.assertEqual(self.schema["Guideline Items"], "1")
        self.assertEqual(self.schema["Guideline Title"], GUIDELINE_TITLE)

    def test_schema_has_the_expected_sections(self):
        self.assertEqual(
            list(self.schema),
            ["Guideline Items", "Guideline Title", "Generalized Compliance Audit",
             "Detailed Compliance Audit", "Compliance Audit Policy Source References",
             "Compliance Audit Summary"],
        )

    def test_clause_row_fields(self):
        row = self.schema["Detailed Compliance Audit"][0]
        self.assertEqual(
            list(row),
            ["SoG Requirement", "Policy Reference", "Policy Excerpt", "Responsible Function",
             "Compliance Status", "Compliance Audit Note"],
        )

    def test_one_row_per_clause_is_required(self):
        self.assertIn("exactly one row per SoG clause", self.prompt)

    def test_verbatim_and_table_rules(self):
        self.assertIn("DO NOT paraphrase", self.prompt)
        self.assertIn("only the table caption or table", normalise_spaces(self.prompt))

    def test_three_status_levels(self):
        for status in ("Fully Compliant", "Partially Compliant", "Gap Identified"):
            with self.subTest(status=status):
                self.assertIn(status, self.schema["Generalized Compliance Audit"]["Compliance Status"])

    def test_no_company_specific_names(self):
        self.assertNotRegex(self.prompt, r"ORSA Standard\.txt")


class GapPromptTest(unittest.TestCase):
    def setUp(self):
        self.prompt = build_prompt.gap_prompt(2, GUIDELINE)
        self.schema = next(json_blocks(self.prompt))

    def test_contains_the_guideline_verbatim(self):
        self.assertIn(GUIDELINE, self.prompt)

    def test_guideline_number_and_title_are_filled_in(self):
        self.assertEqual(self.schema["Guideline Items"], "2")
        self.assertEqual(self.schema["Guideline Title"], GUIDELINE_TITLE)

    def test_clause_row_fields(self):
        row = self.schema["Detailed Gap Audit"][0]
        self.assertEqual(
            list(row),
            ["SoG Requirement", "Policy Reference", "Policy Excerpt", "Responsible Function",
             "Gap Outcome", "Gap Severity", "Gap Audit Note"],
        )

    def test_outcomes_and_severities(self):
        general = self.schema["Generalized Gap Audit"]
        self.assertEqual(general["Gap Outcome"], "NoGap | PartialGap | Gap | UnableToConclude")
        self.assertEqual(general["Gap Severity"], "Low | Medium | High | Critical | None")

    def test_missing_evidence_statement_is_defined(self):
        self.assertIn("No corresponding policy evidence found.", self.prompt)

    def test_no_clause_may_be_skipped(self):
        self.assertIn("You may not skip any clause.", self.prompt)

    def test_rows_align_with_the_compliance_prompt(self):
        compliance = next(json_blocks(build_prompt.compliance_prompt(2, GUIDELINE)))
        shared = ["SoG Requirement", "Policy Reference", "Policy Excerpt", "Responsible Function"]
        self.assertEqual(list(compliance["Detailed Compliance Audit"][0])[:4], shared)
        self.assertEqual(list(self.schema["Detailed Gap Audit"][0])[:4], shared)


class ReporterPromptTest(unittest.TestCase):
    MERGED = '{"clauses": [{"SoG Requirement": "1.1. Example clause"}]}'

    def setUp(self):
        self.prompt = build_prompt.reporter_prompt(1, GUIDELINE, self.MERGED)

    def test_contains_guideline_and_merged_output(self):
        self.assertIn(GUIDELINE, self.prompt)
        self.assertIn(self.MERGED, self.prompt)

    def test_title_and_number_in_the_template(self):
        self.assertIn("Item(s): 1", self.prompt)
        self.assertIn(f"Guideline Title: {GUIDELINE_TITLE}", self.prompt)

    def test_template_sections_in_order(self):
        headings = [
            "## Guideline Information",
            "## Executive Summary — Consolidated Audit View",
            "## Detailed Clause-by-Clause Audit Report",
            "### Clause <N>",
            "## Policy Source References",
            "## Consolidated Audit Conclusion",
            "## Metadata",
        ]
        template = self.prompt.split("# CANONICAL OUTPUT TEMPLATE (MANDATORY)")[1]
        positions = [template.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))

    def test_code_fences_are_balanced(self):
        template = self.prompt.split("# CANONICAL OUTPUT TEMPLATE (MANDATORY)")[1]
        fences = [line for line in template.split("\n") if line.strip() == "```"]
        self.assertEqual(len(fences) % 2, 0)
        self.assertEqual(len(fences), 12)

    def test_clause_block_fields(self):
        for field in ("SoG Requirement:", "Policy Reference(s):", "Policy Excerpt(s):",
                      "Responsible Function:", "Compliance Status (Reporter):",
                      "Gap Outcome (Design):", "Gap Severity:", "Audit Note:",
                      "Consistency Check:", "Reason for Adjustment:", "Recommendation:"):
            with self.subTest(field=field):
                self.assertIn(field, self.prompt)

    def test_reporter_may_not_add_evidence(self):
        self.assertIn("Introduce new policy references or excerpts.", self.prompt)
        self.assertIn("Invent evidence, sections, or line numbers.", self.prompt)

    def test_conservative_reconciliation_rules(self):
        self.assertIn("Adjusted conservatively", self.prompt)
        self.assertIn("❔ Unable To Conclude", self.prompt)

    def test_markdown_tables_are_forbidden(self):
        self.assertIn("Do **NOT** use Markdown tables.", self.prompt)


class KnowledgeChunkTest(unittest.TestCase):
    def test_summary_lines_are_joined(self):
        chunk = build_prompt.summary_as_knowledge_chunks(["Policy one: a", "Policy two: b"])
        self.assertIn("Policy one: a\nPolicy two: b", chunk)
        self.assertIn("Summary of Policies", chunk)

    def test_policies_are_joined(self):
        chunk = build_prompt.policies_as_knowledge_chunks(["0 | first", "0 | second"])
        self.assertIn("0 | first\n0 | second", chunk)
        self.assertIn("Policy Reference", chunk)

    def test_empty_lists_still_give_a_header(self):
        self.assertIn("Summary of Policies", build_prompt.summary_as_knowledge_chunks([]))
        self.assertIn("Policy Reference", build_prompt.policies_as_knowledge_chunks([]))


def normalise_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text)


if __name__ == "__main__":
    unittest.main()
