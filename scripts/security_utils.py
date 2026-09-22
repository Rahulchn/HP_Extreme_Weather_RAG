"""Shared helpers for keeping credentials out of logs and user-facing text."""

import re
from typing import Any


def sanitize_sensitive_text(value: Any) -> str:
    """Redact common credential formats without exposing token fragments."""
    if not value:
        return ""

    text = str(value)
    text = re.sub(r"hf_[A-Za-z0-9]{10,}", "[REDACTED_HF_TOKEN]", text)
    text = re.sub(
        r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})",
        "[REDACTED_GITHUB_TOKEN]",
        text,
    )
    text = re.sub(
        r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{10,}",
        "Bearer [REDACTED_TOKEN]",
        text,
    )
    text = re.sub(
        r"(?i)basic\s+[A-Za-z0-9+/=]{8,}",
        "Basic [REDACTED_TOKEN]",
        text,
    )
    text = re.sub(
        r"(?i)\b(api[_-]?key|x-api-key|access[_-]?token|refresh[_-]?token|"
        r"client[_-]?secret|secret|token|password)\s*([:=])\s*[^\s,;&#]+",
        r"\1\2[REDACTED]",
        text,
    )
    return text
