"""Regression tests for configuration safety and secret redaction."""

import os

from scripts import llm_client
from scripts.security_utils import sanitize_sensitive_text


def test_dotenv_loader_supports_export_comments_and_quotes(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# ignored comment",
                "export TEST_RAG_EXPORTED=enabled",
                'TEST_RAG_QUOTED="value # preserved" # ignored comment',
                "TEST_RAG_INLINE=value # ignored comment",
                "TEST_RAG_EMPTY=",
                "1INVALID_KEY=ignored",
            ]
        ),
        encoding="utf-8",
    )
    for key in (
        "TEST_RAG_EXPORTED",
        "TEST_RAG_QUOTED",
        "TEST_RAG_INLINE",
        "TEST_RAG_EMPTY",
    ):
        monkeypatch.delenv(key, raising=False)

    llm_client.load_dotenv(str(env_file))

    assert os.environ["TEST_RAG_EXPORTED"] == "enabled"
    assert os.environ["TEST_RAG_QUOTED"] == "value # preserved"
    assert os.environ["TEST_RAG_INLINE"] == "value"
    assert os.environ["TEST_RAG_EMPTY"] == ""
    assert "1INVALID_KEY" not in os.environ


def test_dotenv_loader_does_not_override_existing_environment(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_RAG_EXISTING=from-file\n", encoding="utf-8")
    monkeypatch.setenv("TEST_RAG_EXISTING", "from-environment")

    llm_client.load_dotenv(str(env_file))

    assert os.environ["TEST_RAG_EXISTING"] == "from-environment"


def test_invalid_numeric_environment_values_fall_back(monkeypatch):
    monkeypatch.setenv("HF_TIMEOUT", "not-a-number")
    monkeypatch.setenv("HF_TEMPERATURE", "hot")
    monkeypatch.setenv("HF_MAX_TOKENS", "many")

    config = llm_client.get_hf_config()

    assert config["timeout"] == llm_client.DEFAULT_TIMEOUT
    assert config["temperature"] == llm_client.DEFAULT_TEMPERATURE
    assert config["max_tokens"] == llm_client.DEFAULT_MAX_TOKENS


def test_out_of_range_environment_values_fall_back(monkeypatch):
    monkeypatch.setenv("HF_TIMEOUT", "0")
    monkeypatch.setenv("HF_TEMPERATURE", "3.5")
    monkeypatch.setenv("HF_MAX_TOKENS", "999999")

    config = llm_client.get_hf_config()

    assert config["timeout"] == llm_client.DEFAULT_TIMEOUT
    assert config["temperature"] == llm_client.DEFAULT_TEMPERATURE
    assert config["max_tokens"] == llm_client.DEFAULT_MAX_TOKENS


def test_config_status_never_contains_token_fragments(monkeypatch):
    token = "hf_abcdefghijklmnopqrstuvwxyz123456"
    monkeypatch.setenv("HF_TOKEN", token)

    config = llm_client.get_hf_config()

    assert config["has_token"] is True
    assert config["masked_token"] == "CONFIGURED"
    assert token[:4] not in config["masked_token"]
    assert token[-4:] not in config["masked_token"]


def test_error_sanitizer_redacts_common_credentials():
    message = (
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz "
        "token=super-secret-value "
        "hf_abcdefghijklmnopqrstuvwxyz123456 "
        "ghp_abcdefghijklmnopqrstuvwxyz123456"
    )

    sanitized = llm_client.sanitize_error_message(message)

    assert "super-secret-value" not in sanitized
    assert "hf_abcdefghijklmnopqrstuvwxyz123456" not in sanitized
    assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in sanitized
    assert sanitized.count("REDACTED") >= 4


def test_response_sanitizer_redacts_common_credentials():
    message = (
        "api_key=abcdef1234567890 "
        "github_pat_abcdefghijklmnopqrstuvwxyz123456 "
        "Bearer abcdefghijklmnopqrstuvwxyz"
    )

    sanitized = sanitize_sensitive_text(message)

    assert "abcdef1234567890" not in sanitized
    assert "github_pat_abcdefghijklmnopqrstuvwxyz123456" not in sanitized
    assert "abcdefghijklmnopqrstuvwxyz" not in sanitized
