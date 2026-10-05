"""Consistency tests for the synthetic sample set in ``samples/``.

The expected outputs are hand-written illustrations of what the agents should
return for the synthetic guidelines. These tests make sure they obey the same
evidence rules the prompts impose, so the samples can be trusted as a reference.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_prompt  # noqa: E402
import evidence  # noqa: E402

GUIDELINES = evidence.load_json(evidence.SAMPLES_DIR / "guidelines.json")
POLICIES = evidence.load_policies()
LABELS = evidence.load_json(evidence.EXPECTED_DIR / "policy-labels.json")

COMPLIANCE_STATUSES = {
    "✅Fully Compliant",
    "⚠️Partially Compliant",
    "❌Gap Identified",
}
GAP_OUTCOMES = {"NoGap", "PartialGap", "Gap", "UnableToConclude"}
GAP_SEVERITIES = {"Low", "Medium", "High", "Critical", "None"}


def expected(guideline: str, agent: str) -> dict:
    return evidence.load_json(
        evidence.EXPECTED_DIR / f"guideline-{guideline}.{agent}.json"
    )


def clauses_of(guideline: str):
    """The numbered clauses of a guideline; the first line is its title."""
    return GUIDELINES[guideline].split("\n")[1:]


class InputFilesTest(unittest.TestCase):
    def test_guidelines_have_a_title_and_numbered_clauses(self):
        self.assertEqual(sorted(GUIDELINES), ["1", "2"])
        for number, text in GUIDELINES.items():
            with self.subTest(guideline=number):
                lines = text.split("\n")
                self.assertTrue(lines[0].startswith(f"Guideline {number} – "))
                self.assertGreaterEqual(len(lines), 3)
                for position, clause in enumerate(lines[1:], 1):
                    self.assertEqual(
                        evidence.clause_number(clause), f"{number}.{position}"
                    )

    def test_five_policy_documents(self):
        self.assertEqual(len(POLICIES), 5)

    def test_every_policy_is_marked_as_synthetic(self):
        for name, lines in POLICIES.items():
            with self.subTest(policy=name):
                self.assertIn(
                    "Classification: synthetic sample, not a real policy",
                    lines,
                )

    def test_policy_title_matches_the_file_name(self):
        for name, lines in POLICIES.items():
            with self.subTest(policy=name):
                self.assertEqual(f"{lines[0]}.txt", name)

    def test_policy_header_fields(self):
        for name, lines in POLICIES.items():
            with self.subTest(policy=name):
                header = lines[2:7]
                for position, field in enumerate(
                    ("Document type", "Owner", "Version", "Approved")
                ):
                    self.assertTrue(header[position].startswith(f"{field}: "))

    def test_policy_lines_are_wrapped(self):
        for name, lines in POLICIES.items():
            with self.subTest(policy=name):
                self.assertLessEqual(max(len(line) for line in lines), 80)

    def test_summary_has_one_line_per_policy(self):
        summary = (
            (evidence.SAMPLES_DIR / "policy_summary.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertEqual(len(summary), len(POLICIES))
        titles = {line.split(" (")[0] for line in summary}
        self.assertEqual(titles, {name[: -len(".txt")] for name in POLICIES})

    def test_summary_document_types_match_the_policies(self):
        summary = (
            (evidence.SAMPLES_DIR / "policy_summary.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        for line in summary:
            title, rest = line.split(" (", 1)
            with self.subTest(policy=title):
                self.assertIn(
                    f"Document type: {rest.split(',')[0]}",
                    POLICIES[f"{title}.txt"],
                )

    def test_labels_point_to_existing_policies(self):
        for guideline, labels in LABELS.items():
            for label, name in labels.items():
                with self.subTest(guideline=guideline, label=label):
                    self.assertIn(name, POLICIES)

    def test_samples_contain_no_placeholders(self):
        for path in evidence.SAMPLES_DIR.rglob("*"):
            if path.is_file() and path.suffix in {".txt", ".json", ".md"}:
                with self.subTest(file=path.name):
                    self.assertNotIn(
                        "[placeholder]", path.read_text(encoding="utf-8")
                    )


class PromptsOnSamplesTest(unittest.TestCase):
    def test_title_is_taken_from_the_first_line(self):
        for number, text in GUIDELINES.items():
            with self.subTest(guideline=number):
                title = text.split("\n")[0]
                self.assertIn(
                    f'"Guideline Title": "{title}"',
                    build_prompt.compliance_prompt(int(number), text),
                )
                self.assertIn(
                    f'"Guideline Title": "{title}"',
                    build_prompt.gap_prompt(int(number), text),
                )

    def test_selector_knowledge_holds_every_policy_title(self):
        summary = (
            (evidence.SAMPLES_DIR / "policy_summary.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        knowledge = build_prompt.summary_as_knowledge_chunks(summary)
        for name in POLICIES:
            with self.subTest(policy=name):
                self.assertIn(name[: -len(".txt")], knowledge)

    def test_numbered_policy_keeps_every_line(self):
        for name, lines in POLICIES.items():
            with self.subTest(policy=name):
                numbered = build_prompt.with_line_numbers(lines).split("\n")
                self.assertEqual(len(numbered), len(lines))
                self.assertTrue(numbered[-1].endswith(f"| {lines[-1]}"))


class ExpectedOutputTest(unittest.TestCase):
    AGENTS = (
        (
            "compliance-checker",
            "Detailed Compliance Audit",
            "Compliance Audit Policy Source References",
        ),
        ("gap-identifier", "Detailed Gap Audit", "Policy Source References"),
    )

    def each_output(self):
        for guideline in GUIDELINES:
            for agent, rows_key, sources_key in self.AGENTS:
                yield guideline, agent, expected(
                    guideline, agent
                ), rows_key, sources_key

    def test_header_matches_the_guideline(self):
        for guideline, agent, output, _, _ in self.each_output():
            with self.subTest(guideline=guideline, agent=agent):
                self.assertEqual(output["Guideline Items"], guideline)
                self.assertEqual(
                    output["Guideline Title"],
                    GUIDELINES[guideline].split("\n")[0],
                )

    def test_exactly_one_row_per_clause_in_order(self):
        for guideline, agent, output, rows_key, _ in self.each_output():
            with self.subTest(guideline=guideline, agent=agent):
                requirements = [
                    row["SoG Requirement"] for row in output[rows_key]
                ]
                self.assertEqual(requirements, clauses_of(guideline))

    def test_every_excerpt_is_verbatim(self):
        for guideline, agent, output, rows_key, _ in self.each_output():
            for row in output[rows_key]:
                for result in evidence.check_row(
                    row, LABELS[guideline], POLICIES
                ):
                    with self.subTest(
                        guideline=guideline,
                        agent=agent,
                        fragment=result["fragment"][:40],
                    ):
                        self.assertTrue(
                            result["found"],
                            "excerpt is not in any sample policy",
                        )
                        self.assertTrue(
                            result["attribution_ok"],
                            "excerpt is cited to the wrong policy",
                        )

    def test_references_point_at_the_quoted_lines(self):
        for guideline, agent, output, rows_key, _ in self.each_output():
            for row in output[rows_key]:
                references = evidence.parse_references(row["Policy Reference"])
                fragments = evidence.split_excerpt(row["Policy Excerpt"])
                with self.subTest(
                    guideline=guideline,
                    agent=agent,
                    clause=row["SoG Requirement"][:4],
                ):
                    self.assertEqual(len(references), len(fragments))
                    for (label, section, start, end), fragment in zip(
                        references, fragments
                    ):
                        lines = POLICIES[LABELS[guideline][label]]
                        self.assertTrue(
                            evidence.lines_contain(lines, start, end, fragment)
                        )
                        self.assertEqual(
                            evidence.section_of(lines, start), section
                        )

    def test_rows_without_evidence_say_so(self):
        for guideline, agent, output, rows_key, _ in self.each_output():
            for row in output[rows_key]:
                if not evidence.split_excerpt(row["Policy Excerpt"]):
                    with self.subTest(guideline=guideline, agent=agent):
                        self.assertIn(
                            row["Policy Excerpt"],
                            evidence.NO_EVIDENCE_STATEMENTS,
                        )
                        self.assertEqual(
                            row["Policy Reference"], "Not specified"
                        )

    def test_source_references_cover_every_reference(self):
        for (
            guideline,
            agent,
            output,
            rows_key,
            sources_key,
        ) in self.each_output():
            sources = {
                evidence.parse_source(source) for source in output[sources_key]
            }
            self.assertNotIn(None, sources)
            for row in output[rows_key]:
                for label, _, start, end in evidence.parse_references(
                    row["Policy Reference"]
                ):
                    with self.subTest(
                        guideline=guideline, agent=agent, label=label
                    ):
                        self.assertIn(
                            (LABELS[guideline][label], start, end), sources
                        )

    def test_compliance_statuses_are_valid(self):
        for guideline in GUIDELINES:
            for row in expected(guideline, "compliance-checker")[
                "Detailed Compliance Audit"
            ]:
                with self.subTest(guideline=guideline):
                    self.assertIn(
                        row["Compliance Status"], COMPLIANCE_STATUSES
                    )
                    self.assertTrue(row["Compliance Audit Note"])

    def test_gap_outcomes_and_severities_are_valid(self):
        for guideline in GUIDELINES:
            for row in expected(guideline, "gap-identifier")[
                "Detailed Gap Audit"
            ]:
                with self.subTest(guideline=guideline):
                    self.assertIn(row["Gap Outcome"], GAP_OUTCOMES)
                    self.assertIn(row["Gap Severity"], GAP_SEVERITIES)
                    no_severity = row["Gap Outcome"] in {
                        "NoGap",
                        "UnableToConclude",
                    }
                    self.assertEqual(
                        row["Gap Severity"] == "None", no_severity
                    )

    def test_compliance_and_gap_agree(self):
        for guideline in GUIDELINES:
            compliance = expected(guideline, "compliance-checker")[
                "Detailed Compliance Audit"
            ]
            gap = expected(guideline, "gap-identifier")["Detailed Gap Audit"]
            for c_row, g_row in zip(compliance, gap):
                with self.subTest(
                    guideline=guideline, clause=c_row["SoG Requirement"][:4]
                ):
                    fully = c_row["Compliance Status"] == "✅Fully Compliant"
                    self.assertEqual(fully, g_row["Gap Outcome"] == "NoGap")


class ReporterExampleTest(unittest.TestCase):
    def setUp(self):
        self.report = (
            evidence.EXPECTED_DIR / "guideline-1.reporter.md"
        ).read_text(encoding="utf-8")
        self.lines = self.report.split("\n")

    def test_one_block_per_clause(self):
        blocks = [
            line for line in self.lines if line.startswith("### Clause ")
        ]
        self.assertEqual(
            blocks,
            [f"### Clause {n}" for n in range(1, len(clauses_of("1")) + 1)],
        )

    def test_sections_follow_the_canonical_template(self):
        headings = [line for line in self.lines if line.startswith("## ")]
        self.assertEqual(
            headings,
            [
                "## Guideline Information",
                "## Executive Summary — Consolidated Audit View",
                "## Detailed Clause-by-Clause Audit Report",
                "## Policy Source References",
                "## Consolidated Audit Conclusion",
                "## Metadata",
            ],
        )

    def test_no_markdown_tables_and_balanced_fences(self):
        self.assertFalse([line for line in self.lines if line.startswith("|")])
        self.assertEqual(
            len([line for line in self.lines if line == "```"]) % 2, 0
        )

    def test_requirements_are_the_guideline_clauses(self):
        requirements = [
            line[len("SoG Requirement: ") :]
            for line in self.lines
            if line.startswith("SoG Requirement: ")
        ]
        self.assertEqual(requirements, clauses_of("1"))

    def test_excerpts_come_from_the_merged_results(self):
        compliance = expected("1", "compliance-checker")[
            "Detailed Compliance Audit"
        ]
        excerpts = [
            line[len("Policy Excerpt(s): ") :].strip('"')
            for line in self.lines
            if line.startswith("Policy Excerpt(s): ")
        ]
        self.assertEqual(
            excerpts, [row["Policy Excerpt"] for row in compliance]
        )

    def test_reporter_adds_no_new_sources(self):
        start = self.lines.index("## Policy Source References")
        block = self.lines[start : self.lines.index("---", start)]
        sources = [
            line for line in block if line.endswith(tuple("0123456789"))
        ]
        allowed = expected("1", "compliance-checker")[
            "Compliance Audit Policy Source References"
        ]
        self.assertTrue(sources)
        self.assertTrue(set(sources) <= set(allowed))


if __name__ == "__main__":
    unittest.main()
