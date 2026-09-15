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
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

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
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
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

def get_hf_config() -> Dict[str, Any]:
    """
    Returns current configuration settings without exposing the token secret.
    """
    token = os.environ.get("HF_TOKEN")
    model = os.environ.get("HF_MODEL", DEFAULT_HF_MODEL).strip()
    timeout = int(os.environ.get("HF_TIMEOUT", DEFAULT_TIMEOUT))
    temperature = float(os.environ.get("HF_TEMPERATURE", DEFAULT_TEMPERATURE))
    max_tokens = int(os.environ.get("HF_MAX_TOKENS", DEFAULT_MAX_TOKENS))

    has_token = bool(token and len(token.strip()) > 5)
    masked_token = f"{token[:4]}...{token[-4:]}" if has_token else "NOT_CONFIGURED"

    provider = os.environ.get("HF_PROVIDER", "featherless-ai").strip()

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
        err_str = str(e)

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
            "content": None,
            "error_message": msg,
            "latency_ms": latency_ms
        }
