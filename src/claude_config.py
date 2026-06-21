"""Anthropic Claude API configuration for the compliance audit pipeline.

All settings are read from environment variables — no provider endpoints or
credentials are hard-coded. The API key is taken from ANTHROPIC_API_KEY by the
SDK automatically.
"""
import os
from pathlib import Path

import anthropic

# -------------------- Paths --------------------
INPUT_FOLDER = Path(os.getenv("audit_INPUT", "./data"))

# -------------------- Model config --------------------
MODEL_NAME          = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
TEMPERATURE         = float(os.getenv("audit_TEMPERATURE", "0.0"))
TOPPVALUE           = float(os.getenv("audit_TOPPVALUE", "0.1"))

MAX_WORKERS          = int(os.getenv("audit_MAX_WORKERS", "6"))
MAX_RETRIES          = int(os.getenv("audit_MAX_RETRIES", "4"))
RETRY_BASE_DELAY_SEC = float(os.getenv("audit_RETRY_BASE", "2.0"))
REQUEST_TIMEOUT_SEC  = float(os.getenv("audit_TIMEOUT", "120"))
LIMIT_FILES          = int(os.getenv("audit_LIMIT_FILES", "0"))  # 0 = no limit

MAX_TOKENS          = int(os.getenv("audit_MAX_PROMPT_TOKENS", "40000"))
CONTENT_CHAR_BUDGET = MAX_TOKENS * 4
RESPONSE_MAX_TOKENS = int(os.getenv("audit_RESP_TOKENS", "16384"))

# -------------------- Client --------------------
# Reads ANTHROPIC_API_KEY from the environment.
client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT_SEC)
