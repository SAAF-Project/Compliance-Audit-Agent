# Compliance-Audit-Agent

A compliance audit agent for the [SAAF Project](https://github.com/SAAF-Project). Given a
regulatory clause or topic, it triages the most relevant internal policies, assesses compliance
against them using an Anthropic Claude model, and renders the results into a Word report.

This is the working-code home for the Hackathon 4 plan
[`plans/hackathon-4/plan-compliance-audit-agent.md`](https://github.com/SAAF-Project/SAAF-Project/blob/main/plans/hackathon-4/plan-compliance-audit-agent.md)
in the shared SAAF-Project repository. Per the SAAF "Building an agent" guidance, agent source code
lives in its own repo while the plan and shared utilities stay in the main repo.

## Pipeline

1. **Selector / triage** (`src/build_prompt.py`) — builds the prompts that, given a verbatim
   regulatory guideline, shortlist the most relevant internal policies (confidence ≥ 0.80) and then
   perform the per-policy compliance assessment.
2. **Model call** (`src/claude_config.py`) — Anthropic Claude client and run configuration. All
   settings come from environment variables; **no credentials are hard-coded** (the API key is read
   from `ANTHROPIC_API_KEY`).
3. **JSON sanitizing** (`src/json_utils.py`) — repairs and normalizes model JSON output (strips code
   fences, lowercases stray `True`/`False`/`Null` tokens outside strings, etc.).
4. **Reporting** (`src/convert_results.py`) — converts the assessment JSON into a formatted `.docx`
   audit report via `python-docx`.

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

## Configuration

`src/claude_config.py` reads everything from environment variables (defaults shown):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(required)_ | API key, read by the SDK automatically |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Model id |
| `audit_INPUT` | `./data` | Input folder of policy / source documents |
| `audit_TEMPERATURE` | `0.0` | Sampling temperature |
| `audit_MAX_WORKERS` | `6` | Parallel request workers |
| `audit_MAX_PROMPT_TOKENS` | `40000` | Prompt token budget |
| `audit_RESP_TOKENS` | `16384` | Max response tokens |

## Known gaps / TODO

- `src/convert_results.py` imports `validate_func` (`from validate_func import *`), which is **not yet
  included** in this repo. Add that module (or replace the import) before running the reporting step.
- No automated tests yet.
- Sample/synthetic input data is not included — never commit real audit evidence or personal data
  (SAAF rule). Use synthetic or anonymized data only.

## License / data handling

Part of the SAAF (Shared Audit Agents Framework). Do not commit real audit evidence, personal data,
or credentials.
