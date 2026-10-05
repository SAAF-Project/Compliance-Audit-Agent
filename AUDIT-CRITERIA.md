# AUDIT-CRITERIA.md — Compliance-Audit-Agent

> What this agent must be judged against as an auditee: its control objectives, testable acceptance criteria, and known limits. The [README](README.md) says what the agent does and how to run it. This document follows the SAAF A2 standard (`docs/conventions/audit-criteria-template.md` in the main SAAF-Project repo).

---

## Metadata

| Field | Value |
|---|---|
| **Agent** | Compliance-Audit-Agent |
| **Repository** | https://github.com/SAAF-Project/Compliance-Audit-Agent |
| **Maintainer(s)** | Junhan Wen |
| **Last reviewed** | 2026-10-05 |
| **Status** | Draft |

**Sources used to draft this document:** the README, the four agent prompts in
`prompts/`, the pipeline code, and one offline re-run of a saved pipeline run on
2026-10-05 (cited in section 6). Not yet reviewed by a second person.

**This agent makes model calls at runtime** (four Claude calls per guideline:
selector, compliance checker, gap identifier, reporter), so AI-specific
frameworks apply.

## 1. What the agent does

Given a regulatory guideline and a library of internal policy documents, the
agent shortlists the policies most relevant to the guideline, runs two
independent assessments against them (a clause-by-clause compliance check and a
design-gap analysis), and has a reporter consolidate both into one audit report.
Optionally it verifies every quoted policy excerpt against the source documents.
The output is a draft audit report (Markdown and Word) for an auditor to review;
it supports the audit task of assessing whether internal policies cover a
regulatory requirement. It is a straight-through pipeline: it runs the same
fixed steps every time and does not interact with the auditor during a run.

## 2. Control objectives & framework mapping

These are control objectives **for the agent itself**: what must be true of its
behaviour for an auditor to rely on its output as a working draft. They are not
the objectives of the regulation or policies it happens to assess.

| Control objective | Framework + clause/area | Why relevant |
|---|---|---|
| CO-1 — Evidence is verbatim and verifiable: every policy excerpt the agent cites as evidence exists, word for word, in the policy documents it was given. | IIA Global Internal Audit Standards 14.1 (Gathering Information for Analyses and Evaluation: relevant, reliable, sufficient information) | A finding is only as good as its evidence. A paraphrased or invented quote is the main way a language model can corrupt an audit conclusion. |
| CO-2 — Sources are restricted and traceable: the assessment agents work only from the shortlisted policies, each policy label maps to a named document, and every stage's input and raw output is retained. | EU AI Act Art. 12 (record-keeping) and Art. 13 (transparency) | An auditor must be able to reconstruct which documents the agent saw and why any statement in the report is there. |
| CO-3 — Two independent assessments are reconciled conservatively: the compliance check and the gap analysis are produced separately, nothing from either is silently dropped in the merge, and the reporter adds no new evidence. | IIA Global Internal Audit Standards 14.3 (Evaluation of Findings) | Independent assessment followed by conservative reconciliation is the agent's own safeguard against a single optimistic model reply. |
| CO-4 — The output is a draft under human oversight: the report states how it was produced, failures are reported as failures, and nothing is presented as a final audit opinion. | EU AI Act Art. 14 (human oversight) | The agent supports the auditor's judgement; it does not replace it. |
| CO-5 — Credentials and audit evidence are protected: no secrets in code, and no real policy documents or run outputs in the repository. | ISO/IEC 27001 Annex A (access control and protection of information) | The inputs are confidential internal policies and the outputs quote them. |

## 3. Acceptance criteria (testable, pass/fail)

### CO-1 — Verbatim, verifiable evidence

- Given a run with `--validate`, the agent checks every quoted policy excerpt in
  the merged compliance and gap results and in the reporter's report against the
  policy files (after removing line breaks), and marks each one as found or not
  found.
- Given an excerpt that is not in any of the supplied policy files (paraphrased
  or invented), validation marks it as not found. The agent does not remove or
  rewrite the excerpt to make it pass.
- Given an excerpt attributed to one policy but present only in another, the
  validation result shows the cited reference next to the document(s) where the
  text was actually found (`found_in`).
- Given a run with `--validate`, the validation results are appended after the
  reporter's report in the final audit report.
- **Limitation, stated honestly:** validation is optional. Without `--validate`,
  excerpts are not checked. Validation confirms that the quoted text exists; it
  does not confirm the cited section or line range, and tables are cited by
  caption only.

### CO-2 — Restricted, traceable sources

- Given a selector result whose policy titles match files in the policy folder,
  the compliance checker and the gap identifier receive only those files.
- Given a run, the selector output is saved together with the mapping from each
  policy label (`Policy A`, `Policy B`, …) to its file name.
- Given any stage (selector, compliance, gap, reporter), the prompt and
  knowledge sent to the model and the raw reply are written to the progress
  folder with the guideline number and run timestamp.
- Given a selector that only receives the policy summary, the selector's output
  contains only titles that appear in that summary.
- **Limitation, stated honestly:** if the selector returns no policies, or none
  of its titles match a file name, the pipeline falls back to **all** policy
  files instead of stopping. It prints a message but the report itself does not
  flag this.

### CO-3 — Independent assessments, conservative reconciliation

- Given a guideline, the compliance check and the gap analysis are separate
  model calls, and neither receives the other's output.
- Given the two results, the merge joins rows for the same guideline requirement
  (or the same quoted excerpt), and a gap row with no compliance counterpart is
  kept in the merged results, not dropped.
- Given the merged results, the reporter's report contains no policy reference
  or excerpt that is absent from the merged results.
- Given a clause where the compliance check and the gap analysis disagree, the
  reporter adopts the more conservative status, explains why in the clause's
  Audit Note, and sets its Consistency Check to "Adjusted conservatively".
- **Limitation, stated honestly:** the last two criteria are instructions in the
  reporter prompt. They are checked by a person reading the report (and, for
  excerpts, by `--validate`), not enforced by code.

### CO-4 — Draft under human oversight

- Given a completed run, the first lines of the audit report state the model and
  temperature used, or state that it was an offline run loaded from a saved run.
- Given `--load-progress`, the agent makes no API calls. If a saved reply is
  missing for a stage, that stage fails with a message naming the missing file,
  and the combined results note which steps have no results.
- Given a stage that fails or returns a reply that cannot be parsed, the results
  record `status: Error` with the reason. The agent does not substitute
  generated content, and a failed reporter stage yields a report that says no
  reporter report was produced.
- **Limitation, stated honestly:** there are no checkpoints during a run. The
  auditor reviews only at the end.

### CO-5 — Credentials and evidence protection

- Given the repository, no file contains an API key or other credential; the key
  is read from `ANTHROPIC_API_KEY`.
- Given the repository, no real policy text and no run output is tracked.

## 4. Good output / never do

| A correct output MUST contain | The agent must NEVER |
|---|---|
| ✓ For each guideline clause: the verbatim requirement, the policy evidence or an explicit statement that none was found, a compliance status, and a gap outcome with severity | ✕ Invent or paraphrase policy text, policy titles or guideline clauses |
| ✓ The policy reference for every excerpt, using the saved policy labels | ✕ Add evidence in the reporter stage that is not in the merged results |
| ✓ A header stating the model and settings, or that the run was offline | ✕ Present the report as a final audit opinion without auditor review |
| ✓ With `--validate`: a found / not found result for every quoted excerpt | ✕ Hide a failed stage behind generated content |
| ✓ An explicit error status when a stage failed | ✕ Hard-code credentials, or commit real policy documents or run outputs |

## 5. Coverage gaps

- **No automatic sync with the policy library.** In the organisation where the
  agent is piloted, all policies are kept in a SharePoint library and reach the
  agent through a synced OneDrive folder. The agent does not read the library
  itself. In particular, the policy summary that the selector relies on is
  produced by a separate, manually started agent run, so it can fall behind the
  library: a new or changed policy is invisible to the selector until someone
  regenerates the summary.
- **Plain-text policies only.** The pipeline reads `.txt` files, while most
  policies exist as `.docx`. Each user converts the documents by hand, which
  adds effort and a place where text, tables or headings can be lost before the
  agent ever sees them.
- **Public tests cover the prompts and a small synthetic set only.** `samples/`
  holds two synthetic guidelines, five synthetic policies, hand-written
  reference outputs and a flawed case with three planted defects; `tests/`
  checks the prompt builders and the consistency of that set without calling a
  model. Tests on real company policies and on the audit results derived from
  them cannot be published, and no recorded model run on the synthetic set is
  included yet.
- **Evidence validation is optional and checks existence only.** Location
  validation (policy title, section and line range) is planned but not built.
- **Silent fallback to all policies** when the selector's titles match no file
  (see CO-2).
- **No cross-model or repeated-run check.** Each stage is one call to one model;
  consistency across runs is not measured.
- **No auditor checkpoints.** A run cannot be paused for review so that only the
  affected part is redone.
- **Guidelines are selected by editing a constant** in `orchestration.py`, which
  is easy to get wrong and is not recorded outside the output file names.
- **Run logs are plain local files that contain confidential policy text**, with
  no retention rule or integrity protection.

## 6. Status / validation

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| CO-2 — assessment agents receive only the matched policy files | ☑ (one run) | Offline re-run on 2026-10-05 of a saved run for one guideline: the selector's titles matched 8 of 34 policy files, and only those were loaded |
| CO-2 — stage inputs and raw replies are saved per run | ☑ (one run) | Same run: selector, compliance, gap and reporter input files were written to the progress folder |
| CO-4 — `--load-progress` makes no API calls | ☑ (one run) | Same run: every stage reported that the API call was skipped and the saved reply was loaded |
| CO-4 — report header states how the report was produced | ☑ (one run) | Same run: the audit report was written as Markdown and Word with the offline note |
| CO-1 — validation runs and its results are appended | ☑ (ran) / ☐ (correctness) | Same run with `--validate` produced validation reports. Whether each found / not found verdict is correct has not been checked against a deliberately wrong excerpt |
| CO-1 — wrong-policy attribution is exposed via `found_in` | ☐ | Needs a synthetic case with a misattributed quote |
| CO-2 — selector uses only titles from the summary | ☐ | Needs a synthetic policy summary and a check of the selector output |
| CO-3 — all criteria | ☐ | Merge behaviour and reporter behaviour not yet tested against constructed disagreements |
| CO-4 — failed stage is recorded as an error | ☐ | Read from the code, not exercised |
| CO-5 — no credentials or evidence in the repository | ☑ | Tracked files reviewed on 2026-10-05: none contains credentials, policy text or run output |

Next steps: run the agent on the synthetic set in `samples/` and on its flawed
case (a paraphrased excerpt, a misattributed excerpt, a compliance/gap
disagreement), and record the results here to exercise CO-1 and CO-3.

## 7. Observability

Logged today: for every guideline and stage, the prompt and knowledge sent to
the model, the raw reply and the parsed output are written to the progress
folder under the run timestamp, together with the merged results, the validation
reports and the final report. A refusal or a reply cut off at the token limit is
printed with the request id. Missing: no structured log, no token or cost
accounting, no alerting, no integrity protection, and no retention rule for
files that contain confidential policy text.
