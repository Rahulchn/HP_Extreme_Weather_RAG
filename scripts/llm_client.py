"""
llm_client.py
Milestone 3: Hugging Face Inference API Client Layer

Provides a clean, authenticated communication interface with the Hugging Face Inference API.
Configured for the available Hugging Face inference/free-access allowance.
Provider availability, model status, and rate limits are subject to provider policy.

Safety Invariants:
- NEVER hardcodes or logs API tokens.
- NEVER performs silent model fallback: HF_MODEL selects exactly ONE model.
- If the configured model fails, times out, is unauthorized, or rate-limited,
  returns structured client failure status without fabricating responses.
"""

import os
import sys
import time
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from scripts.security_utils import sanitize_sensitive_text


_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _parse_dotenv_line(line: str) -> Optional[tuple[str, str]]:
    """Parse one dotenv assignment while preserving comments inside quotes."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].lstrip()
    if "=" not in stripped:
        return None

    key, raw_value = stripped.split("=", 1)
    key = key.strip()
    if not _ENV_KEY_PATTERN.fullmatch(key):
        return None

    raw_value = raw_value.strip()
    if raw_value and raw_value[0] in "'\"":
        quote = raw_value[0]
        closing_quote = raw_value.find(quote, 1)
        trailing = raw_value[closing_quote + 1:].strip() if closing_quote >= 0 else ""
        if closing_quote >= 0 and (not trailing or trailing.startswith("#")):
            value = raw_value[1:closing_quote]
        else:
            value = raw_value
    else:
        value = raw_value.split(" #", 1)[0].rstrip()
    return key, value

# Load environment variables from .env if present (without external dependencies)
def load_dotenv(env_path: Optional[str] = None) -> None:
    candidate_paths = []
    if env_path:
        candidate_paths.append(env_path)
    else:
        candidate_paths.append(".env")
        # Try parent directory if executed from scripts/ or evaluation/
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_paths.append(os.path.join(os.path.dirname(script_dir), ".env"))
        candidate_paths.append(os.path.join(script_dir, ".env"))

    for p in candidate_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        assignment = _parse_dotenv_line(line)
                        if assignment:
                            key, value = assignment
                            os.environ.setdefault(key, value)
                break
            except Exception:
                pass

# Load local .env if available
load_dotenv()

DEFAULT_HF_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_TIMEOUT = 30
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 1024

logger = logging.getLogger("llm_client")


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    """Read a bounded integer setting, falling back safely on invalid input."""
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if minimum <= value <= maximum else default


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    """Read a bounded floating-point setting, falling back safely on invalid input."""
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if minimum <= value <= maximum else default


def sanitize_error_message(value: Any) -> str:
    """Remove common credential formats before an exception reaches callers."""
    return sanitize_sensitive_text(value)

def get_hf_config() -> Dict[str, Any]:
    """
    Returns current configuration settings without exposing the token secret.
    """
    token = os.environ.get("HF_TOKEN")
    model = os.environ.get("HF_MODEL", DEFAULT_HF_MODEL).strip() or DEFAULT_HF_MODEL
    timeout = _env_int("HF_TIMEOUT", DEFAULT_TIMEOUT, minimum=1, maximum=300)
    temperature = _env_float("HF_TEMPERATURE", DEFAULT_TEMPERATURE, minimum=0.0, maximum=2.0)
    max_tokens = _env_int("HF_MAX_TOKENS", DEFAULT_MAX_TOKENS, minimum=1, maximum=32768)

    has_token = bool(token and len(token.strip()) > 5)
    # Preserve the existing status field without revealing any token fragments.
    masked_token = "CONFIGURED" if has_token else "NOT_CONFIGURED"

    provider = os.environ.get("HF_PROVIDER", "featherless-ai").strip() or "featherless-ai"

    return {
        "model": model,
        "provider": provider,
        "has_token": has_token,
        "masked_token": masked_token,
        "timeout": timeout,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "provider_display": f"Hugging Face Inference Provider: {provider} (configured for the available Hugging Face inference/free-access allowance)",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def call_hf_inference(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    token: Optional[str] = None,
    timeout: Optional[int] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calls the Hugging Face Inference API with a list of chat messages.
    Returns a structured dictionary with execution status and content.
    
    Status codes:
    - OK: Successful inference
    - MISSING_TOKEN: HF_TOKEN environment variable not set
    - UNAUTHORIZED: 401 Invalid or expired token
    - RATE_LIMITED: 429 API rate limit exceeded
    - MODEL_UNAVAILABLE: 503 Model loading or decommissioned
    - TIMEOUT: Request timed out
    - API_ERROR: Other network or HTTP error
    - MALFORMED_RESPONSE: Output could not be parsed
    """
    from huggingface_hub import InferenceClient

    cfg = get_hf_config()
    selected_model = model or cfg["model"]
    selected_provider = provider or cfg["provider"]
    auth_token = token or os.environ.get("HF_TOKEN")
    req_timeout = timeout or cfg["timeout"]
    req_temp = temperature if temperature is not None else cfg["temperature"]
    req_max_tokens = max_tokens or cfg["max_tokens"]

    if not auth_token or not auth_token.strip():
        return {
            "status": "MISSING_TOKEN",
            "model": selected_model,
            "provider": selected_provider,
            "content": None,
            "error_message": "HF_TOKEN environment variable is not configured. Set HF_TOKEN in .env or environment to enable live LLM generation.",
            "latency_ms": 0.0
        }

    t0 = time.time()
    try:
        client = InferenceClient(
            model=selected_model,
            provider=selected_provider,
            token=auth_token.strip(),
            timeout=req_timeout
        )

        # Execute chat completion
        response = client.chat.completions.create(
            messages=messages,
            temperature=req_temp,
            max_tokens=req_max_tokens
        )

        latency_ms = round((time.time() - t0) * 1000, 2)

        if not response or not response.choices:
            return {
                "status": "MALFORMED_RESPONSE",
                "model": selected_model,
                "provider": selected_provider,
                "content": None,
                "error_message": "Hugging Face returned an empty response object.",
                "latency_ms": latency_ms
            }

        content = response.choices[0].message.content

        return {
            "status": "OK",
            "model": selected_model,
            "provider": selected_provider,
            "content": content,
            "error_message": None,
            "latency_ms": latency_ms
        }

    except Exception as e:
        latency_ms = round((time.time() - t0) * 1000, 2)
        err_str = sanitize_error_message(e)

        # Categorize known HTTP / client exceptions
        if "401" in err_str or "unauthorized" in err_str.lower() or "invalid token" in err_str.lower():
            status = "UNAUTHORIZED"
            msg = "Hugging Face API returned 401 Unauthorized: Invalid or expired HF_TOKEN."
        elif "429" in err_str or "rate limit" in err_str.lower() or "too many requests" in err_str.lower():
            status = "RATE_LIMITED"
            msg = "Hugging Face API returned 429: Free tier inference rate limit reached. Please retry shortly."
        elif "503" in err_str or "currently loading" in err_str.lower() or "estimated_time" in err_str.lower():
            status = "MODEL_UNAVAILABLE"
            msg = f"Hugging Face API returned 503: Model '{selected_model}' is currently loading or unavailable."
        elif "timeout" in err_str.lower() or "timed out" in err_str.lower():
            status = "TIMEOUT"
            msg = f"Hugging Face API request timed out after {req_timeout}s."
        else:
            status = "API_ERROR"
            msg = f"Hugging Face API error: {err_str}"

        return {
            "status": status,
            "model": selected_model,
            "provider": selected_provider,
            "content": None,
            "error_message": msg,
            "latency_ms": latency_ms
        }
