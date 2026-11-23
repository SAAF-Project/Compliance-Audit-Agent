# Public launcher security boundary

The current public distribution intentionally omits the assessment engine,
internal prompts, private test suite and sample material. Do not recover those
artifacts from history and republish them as part of routine repair. The original
author remains Junhan Wen; this batch does not assign a current accepted owner,
contact SLA or license. Use GitHub private reporting if enabled or an existing
trusted private contact, never a public issue containing policy text or secrets.

`--status` loads no private runtime or audit inputs. A normal public checkout
returns 2 for missing `scripts/utils.py` before reading guideline data or creating
outputs. An explicitly supplied regular sibling helper is trusted executable
code, not an untrusted document. A working-directory `utils.py` is not selected;
a symlink helper is refused. Python's `-I -S` invocation is the tested boundary.
This is not a sandbox for supplied private code.

No model/provider version, region, retention, authorization, cost limits or
network behavior of that private code is verified here. Existing dependency
names are historical private-runtime declarations, not a tested lock. Replay
flags cannot prove that private code makes no network calls. Use only an accepted
runtime in an environment authorized for the actual audit material.

Launcher failures, including private `SystemExit(0)`, return 2; interruption 130; existing or partial output files may
remain and must not be treated as fresh successful evidence. Private exception
content is not printed by the launcher's catch handler, but private code may
itself log content. A zero exit only reports completion of this launcher protocol;
it does not inspect or approve findings, prove grounding or license a report.
Combined output uses exclusive creation, preserving any existing same-name file.
This does not make the private helper idempotent: a retry may repeat private
operations, provider calls or writes before a filename collision is detected.

CI runs only newly authored public launcher fixtures in temporary directories,
with synthetic local helper stubs and a minimal environment. It does not load
private modules, restore withdrawn tests, call a provider or process real audit
material. The unchanged historical control objectives remain separately
unassessed against the current private implementation.
