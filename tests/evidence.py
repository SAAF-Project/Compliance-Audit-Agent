"""Small helpers for checking quoted evidence against the synthetic sample policies.

The helpers follow the rules that the agent prompts impose on evidence:

- excerpts are quoted ad verbatim; long sentences may only be shortened with "...";
- a quote counts as found when it appears in a policy after line breaks are removed;
- line numbers follow ``with_line_numbers`` in ``scripts/build_prompt.py`` and start at 0.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = REPO_ROOT / "samples"
POLICY_DIR = SAMPLES_DIR / "plain_docs"
EXPECTED_DIR = SAMPLES_DIR / "expected"
FLAWED_DIR = SAMPLES_DIR / "flawed-case"

# Statements that an agent writes when it has no policy text to quote.
NO_EVIDENCE_STATEMENTS = (
    "No corresponding policy evidence found.",
    "No corresponding section identified",
)

_REFERENCE = re.compile(
    r"^(?P<label>Policy [A-Z]) > (?P<section>.+) > lines? (?P<start>\d+)(?:[-–](?P<end>\d+))?$"
)
_SOURCE = re.compile(r"^(?P<document>.+\.txt), lines? (?P<start>\d+)(?:[-–](?P<end>\d+))?$")


def normalise(text: str) -> str:
    """Collapse every run of whitespace, including line breaks, into one space."""
    return re.sub(r"\s+", " ", text).strip()


def load_json(path: Path):
    """Read a UTF-8 JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_policies(policy_dir: Path = POLICY_DIR) -> Dict[str, List[str]]:
    """Return ``{file name: lines}`` for every plain-text policy in ``policy_dir``."""
    policies: Dict[str, List[str]] = {}
    for path in sorted(policy_dir.glob("*.txt")):
        policies[path.name] = path.read_text(encoding="utf-8").splitlines()
    return policies


def split_excerpt(excerpt: str) -> List[str]:
    """Split a "Policy Excerpt" value into the separate verbatim fragments it quotes.

    Several quotes in one row are joined with "..." and a long sentence may be
    shortened with "...", so each part between the dots must be found on its own.
    """
    if excerpt.strip() in NO_EVIDENCE_STATEMENTS:
        return []
    fragments = [normalise(part) for part in excerpt.split("...")]
    return [fragment for fragment in fragments if fragment]


def find_in(fragment: str, policies: Dict[str, List[str]]) -> List[str]:
    """Return the names of the policy files that contain ``fragment`` verbatim."""
    target = normalise(fragment)
    return [name for name, lines in policies.items() if target in normalise(" ".join(lines))]


def parse_reference(reference: str) -> Optional[Tuple[str, str, int, int]]:
    """Parse ``Policy A > Section > line 58-59`` into (label, section, first, last)."""
    match = _REFERENCE.match(reference.strip())
    if not match:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    return match.group("label"), match.group("section"), start, end


def parse_references(value: str) -> List[Tuple[str, str, int, int]]:
    """Parse a "Policy Reference" value that may combine several references with ';'."""
    parsed = []
    for part in value.split(";"):
        reference = parse_reference(part)
        if reference is not None:
            parsed.append(reference)
    return parsed


def parse_source(source: str) -> Optional[Tuple[str, int, int]]:
    """Parse ``Outsourcing Policy.txt, lines 58-59`` into (document, first, last)."""
    match = _SOURCE.match(source.strip())
    if not match:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    return match.group("document"), start, end


def lines_contain(lines: List[str], start: int, end: int, fragment: str) -> bool:
    """True when ``fragment`` appears in lines ``start``..``end`` (0-based, inclusive)."""
    if start < 0 or end >= len(lines) or start > end:
        return False
    return normalise(fragment) in normalise(" ".join(lines[start:end + 1]))


def section_of(lines: List[str], line_no: int) -> Optional[str]:
    """Return the heading of the numbered section that contains line ``line_no``."""
    for line in reversed(lines[:line_no + 1]):
        match = re.match(r"^\d+\. (\S.*)$", line)
        if match:
            return match.group(1)
    return None


def clause_number(requirement: str) -> str:
    """Return the leading clause number of a requirement, e.g. "1.3" for "1.3. The ..."."""
    match = re.match(r"^(\d+\.\d+)\.", requirement.strip())
    return match.group(1) if match else ""


def check_row(row: dict, labels: Dict[str, str], policies: Dict[str, List[str]]) -> List[dict]:
    """Check every quoted fragment of one clause row.

    Returns one result per fragment with the documents the row cites, the
    documents where the fragment was actually found, and whether the two agree.
    """
    cited = [labels.get(label, label) for label, _, _, _ in parse_references(row.get("Policy Reference", ""))]
    results = []
    for fragment in split_excerpt(row.get("Policy Excerpt", "")):
        found = find_in(fragment, policies)
        results.append({
            "fragment": fragment,
            "cited": cited,
            "found_in": found,
            "found": bool(found),
            "attribution_ok": bool(found) and any(name in cited for name in found),
        })
    return results
