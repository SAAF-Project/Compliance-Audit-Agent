"""Anthropic Claude API configuration for the compliance audit pipeline.

All settings are read from environment variables — no provider endpoints or
credentials are hard-coded. The API key is taken from ANTHROPIC_API_KEY by the
SDK automatically.
"""
import os

import anthropic

# -------------------- Model config --------------------
MODEL_NAME          = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
TEMPERATURE         = float(os.getenv("MODEL_TEMPERATURE", "0.0"))

MAX_WORKERS          = int(os.getenv("MAX_WORKERS", "6"))
MAX_RETRIES          = int(os.getenv("MAX_RETRIES", "4"))
REQUEST_TIMEOUT_SEC  = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "600"))
LIMIT_FILES          = int(os.getenv("FILE_LIMIT", "0"))  # 0 = no limit

MAX_TOKENS          = int(os.getenv("MAX_PROMPT_TOKENS", "40000"))
CONTENT_CHAR_BUDGET = MAX_TOKENS * 4
RESPONSE_MAX_TOKENS = int(os.getenv("RESPONSE_MAX_TOKENS", "16384"))

# -------------------- Client --------------------
# Reads ANTHROPIC_API_KEY from the environment.
# The SDK retries connection errors, 408, 409, 429 and 5xx with exponential backoff (honouring retry-after).
client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT_SEC, max_retries=MAX_RETRIES)
