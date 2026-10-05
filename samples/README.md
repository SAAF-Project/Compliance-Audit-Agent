# Synthetic sample set

Everything in this folder is **synthetic**. The company ("Example Insurance Group"), the five
policies and the two guidelines were written for this repository. No real policy, guideline text
or audit result is included.

The set gives the agent a small, shareable input, shows what good output looks like, and adds a
deliberately flawed case for the evidence and reconciliation criteria in
[`AUDIT-CRITERIA.md`](../AUDIT-CRITERIA.md).

## Contents

```
guidelines.json              Two guidelines: "1" (outsourcing, 4 clauses) and "2" (data quality, 3 clauses)
policy_summary.txt           One line per policy, as read by the selector
plain_docs/                  Five plain-text policies (file name = policy title)
  Outsourcing Policy.txt
  Third-Party Risk Standard.txt
  Data Governance Standard.txt
  Risk Function Charter.txt
  Business Continuity Standard.txt
expected/                    Hand-written reference outputs
  policy-labels.json         Which document each label (Policy A, Policy B, …) stands for, per guideline
  guideline-1.compliance-checker.json
  guideline-1.gap-identifier.json
  guideline-1.reporter.md
  guideline-2.compliance-checker.json
  guideline-2.gap-identifier.json
flawed-case/                 Guideline 1 results with three planted defects
  guideline-1.compliance-checker.json
  guideline-1.gap-identifier.json
  planted-defects.json       What was planted and how it should be detected
```

## Running the agent on the samples

Set `GUIDELINES_TO_CHECK = [1]` (or `[1, 2]`) in `scripts/orchestration.py`, then run from the
repository root:

```bash
python scripts/orchestration.py --validate \
  --guideline-file samples/guidelines.json \
  --policy-summary-file samples/policy_summary.txt \
  --policy-path samples/plain_docs \
  --progress-path ./runs
```

## What the samples are designed to show

| Guideline clause | Sample policies | Intended outcome |
|---|---|---|
| 1.1 written, approved outsourcing policy | Outsourcing Policy, section 3 | Fully compliant, no gap |
| 1.2 documented due diligence before outsourcing | Third-Party Risk Standard, section 3, and Outsourcing Policy, section 4 | Fully compliant; two policies cover one clause together |
| 1.3 access for the undertaking and the supervisor | Outsourcing Policy, section 5 | Partially compliant, High gap: supervisor and premises are missing |
| 1.4 exit plans, tested every two years | Outsourcing Policy, section 7 | Partially compliant, Medium gap: permissive wording ("may"), no test |
| 2.1 data quality criteria | Data Governance Standard, section 2 | Fully compliant, no gap |
| 2.2 documented deficiencies and remediation | Data Governance Standard, section 5 | Partially compliant, Low gap: remediation for material deficiencies only |
| 2.3 independent review every three years | none | Gap, Medium: no policy evidence exists |

The Business Continuity Standard is a distractor: it is not relevant to either guideline, so a
correct selector should leave it out. The Outsourcing Policy and the Business Continuity Standard
each refer to a table by its caption, for the table citation rule.

## Reference outputs

The files in `expected/` are **hand-written illustrations**, not recorded model output. They
follow the output structure defined in `scripts/build_prompt.py` and obey the evidence rules of
the prompts:

- every policy excerpt is quoted ad verbatim from a sample policy;
- line numbers are those of `with_line_numbers` and start at 0;
- each row cites the document, section and line range where the quote stands.

A real run will differ in wording, in notes and possibly in the lines it chooses to quote. Use the
reference outputs to judge the structure and the conclusions, not to compare text literally.

## Flawed case

`flawed-case/` repeats the guideline 1 results with three defects planted in the compliance
checker's output. The gap identifier's output is unchanged.

| Clause | Defect | What should happen |
|---|---|---|
| 1.2 | The excerpt is paraphrased | Evidence validation marks it as not found |
| 1.3 | The excerpt is verbatim but cited to Policy B instead of Policy A | Evidence validation finds it in a document other than the cited one (`found_in`) |
| 1.4 | Compliance says Fully Compliant, gap says PartialGap / Medium | The reporter downgrades to Partially Compliant and records "Adjusted conservatively" |

`planted-defects.json` holds the same information in machine-readable form.

## Tests

The tests in `tests/` need no API key and no installation beyond Python:

```bash
python -m unittest discover -s tests
```

They check the prompt builders, the internal consistency of this sample set (verbatim quotes, line
ranges, one row per clause) and that each planted defect is detectable from the sample policies.
They do not call a model.
