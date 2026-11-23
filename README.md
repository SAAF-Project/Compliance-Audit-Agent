# Compliance-Audit-Agent

**Public launcher only.** This checkout does not include the assessment engine
and cannot perform a policy audit. The status and refusal commands below run
without a provider key, site packages or private material.

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
modules, the synthetic sample data, and the private test suite all live only in the
author's local working copy and are intentionally excluded from version
control (see `.gitignore`). A public checkout of this repository is not
sufficient to run the pipeline or to reconstruct how it works internally. The
new public tests cover only the launch protocol with small newly authored stubs;
they do not restore or execute the withdrawn private tests or samples.

## Public status and checks

The public launcher and tests need only Python's standard library. CI checks
Python 3.10 and 3.12; no package installation, provider key or `.env` is needed.

```bash
python3 -I -S scripts/orchestration.py --status
python3 -I -S scripts/orchestration.py
python3 -I -S -m unittest discover -s tests/public_entrypoint -v
```

`--status` exits 0 with `pipeline_verified: false`. A default public checkout
exits 2 for missing `scripts/utils.py`, before reading audit data or creating
progress files. The public tests use fake helpers in fresh temporary directories,
not the author's private implementation. `requirements.txt` retains historical
private-runtime dependency declarations; these ranges are not a tested install
contract and public CI does not install them.

## Supplying a private runtime

The original author-managed runtime remains outside this distribution. If a
separately authorized local copy is supplied, the launcher uses only the regular
`utils.py` beside itself, never a same-named helper from the working directory.
That helper must provide `configure`, `main` and the missing-reply list. Existing
argument names and the guideline selection `[27]` are retained; no sample content
or assessment logic is supplied here. Guideline input, including duplicate JSON keys, is checked before importing
the helper. Private code is trusted executable code, not sandboxed by this
launcher, and may need its own dependency environment and review.

Empty results, missing saved replies, invalid input and runtime failures
(including an internal `SystemExit(0)`) return 2; interruption returns 130.
Combined output files are created exclusively: a same-second filename collision
fails instead of overwriting earlier evidence. Existing or partial artifacts are
retained for inspection. This does not establish private-helper idempotency: a
retry can still repeat its work, provider calls or private output writes. A zero exit reports only completion of the launcher protocol, not
valid findings, adequate audit evidence or a passing assessment. `--load-progress`
is a request to the private runtime: the public launcher cannot prove no provider
call occurred. `--no-data-testmode` requires both `--validate` and `--load-progress`.

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
intentional publication decision, not an instruction to republish them. The public status/refusal contract and public launcher tests are assessed
separately from the author's unpublished pipeline; see [`SECURITY.md`](SECURITY.md).

The original standards contribution identifies unresolved findings-schema
mapping, model/data residency, command restrictions and licensing. These remain
review tasks: the public code cannot establish the private implementation's
model version, processing region, retention, allowed tools or control operation.
The historical author is Junhan Wen; a preferred private contact and current
accepted ownership still need confirmation. No license grant is inferred.
