# Compliance-Audit-Agent

A pilot company policy compliance auditing assistant. Given a regulatory
guideline, it narrows down to the internal policies that matter, runs more
than one independent reasoning pass over them, reconciles what each pass
found, and produces a single consolidated audit report for a human auditor
to review.

**This is a straight-through processing tool, not an interactive/agentic
assistant.** It follows a fixed sequence of stages rather than improvising
its own plan, and a human auditor reviews the output before it is used for
anything. The exact number of stages, their order, and how they communicate
with each other are intentionally not detailed here.

This is the working-code home for a plan submitted as part of a SAAF
hackathon exercise. What the agent is judged against is in
[`AUDIT-CRITERIA.md`](AUDIT-CRITERIA.md).

## Design focus

The project's central design problem is **evidence integrity**: making sure
that anything the system claims is "in the policy" can actually be checked
against the source text, and that no stage of the pipeline is able to
quietly invent, reshuffle, or misattribute a citation. A meaningful share of
the engineering effort (and of the test suite) exists specifically to catch
that failure mode, rather than to produce a nicer-looking report.

How that guarantee is actually implemented — the verification method, the
internal data contracts between stages, and the specific prompt engineering
behind each reasoning step — is deliberately not published in this README.
If you're evaluating this work and need those details, ask the author
directly.

## What's actually in this repository

Only a thin, non-functional slice is tracked in git: the entry point
(`scripts/orchestration.py`), the project documentation, and configuration
plumbing. The prompts that drive each reasoning stage, the internal helper
modules, the synthetic sample data, and the test suite all live only in the
author's local working copy and are intentionally excluded from version
control (see `.gitignore`). A public checkout of this repository is not
sufficient to run the pipeline or to reconstruct how it works internally.

## Requirements

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

- Python 3.10+
- An Anthropic API key in your environment:
  ```bash
  export ANTHROPIC_API_KEY=sk-ant-...
  ```

## Running

The entry point is `scripts/orchestration.py`. It expects its supporting
modules, prompt files, and input data to be present locally — none of which
are included in this public checkout. This repository is published as a
record of the work, not as a runnable distribution.

## Known gaps / TODO

- Add user checkpoints so auditors can pause mid-run, give feedback, and
  have only the affected part of the analysis redone, instead of the tool
  running straight through every time.
- Deepen evidence validation beyond verbatim-text checks to also confirm
  *where* in the source document each citation comes from.
- Grow the synthetic sample set; its current reference outputs are
  hand-written illustrations rather than recorded model runs.

## Ownership / data handling

Built by Junhan Wen and polished/processed with Claude. This is a pilot
project developed to assist real-life audit work; this repository is the
SAAF-hackathon version. Do not commit real audit evidence, personal data, or
credentials; use synthetic or anonymized data only.

If you are referencing, building on, or demonstrating ideas from this
project, please credit the original author rather than presenting the
approach as your own.

## Public boundary and SAAF standards

The public checkout cannot run the private pipeline. Its missing helpers are an
intentional publication decision, not an instruction to republish them. A safe
public status/refusal contract and public launcher tests can be assessed
separately from the author's unpublished pipeline.

The original standards contribution identifies unresolved findings-schema
mapping, model/data residency, command restrictions and licensing. These remain
review tasks: the public code cannot establish the private implementation's
model version, processing region, retention, allowed tools or control operation.
The historical author is Junhan Wen; a preferred private contact and current
accepted ownership still need confirmation. No license grant is inferred.
