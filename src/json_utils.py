import re
import json

# -------------------- JSON sanitizer --------------------
_token_re = re.compile(r'''
    (")
    (?:\\.|[^"\\])*
    (")
    \b(True|False|Null)\b
''', re.VERBOSE)

def _strip_fences(s: str) -> str:
    if not isinstance(s, str): return ""
    t = s.strip()
    if t.startswith("```"):
        i = t.find("\n")
        if i != -1:
            t = t[i+1:]
        if t.endswith("```"):
            t = t[:-3].strip()
    return t

def _lower_tokens_outside_strings(text: str) -> str:
    out, last = [], 0
    for m in _token_re.finditer(text):
        start, end = m.span()
        out.append(text[last:start])
        if m.group(3):  # True/False/Null
            out.append(m.group(3).lower())
        else:
            out.append(text[start:end])
        last = end
    out.append(text[last:])
    return ''.join(out)

def sanitize_json_like(text: str) -> str:
    t = _strip_fences(text or "")
    t = t.replace("\r\n", "\n")
    t = _lower_tokens_outside_strings(t)
    t = re.sub(r',\s*(?=[}\]])', '', t)
    t = re.sub(r'\bNaN\b|\bInfinity\b|\b-?Inf\b', 'null', t)
    return t

def parse_details_json(text: str) -> dict | None:
    t = sanitize_json_like(text)
    try:
        return json.loads(t)
    except Exception:
        return None
