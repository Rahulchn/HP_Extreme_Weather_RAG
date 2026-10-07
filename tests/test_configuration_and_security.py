"""Regression tests for configuration safety and secret redaction."""

import os
from types import SimpleNamespace

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


def test_request_overrides_are_coerced_and_bounded():
    config = {"timeout": 30, "temperature": 0.1, "max_tokens": 1024}

    assert llm_client.resolve_inference_options("15", "0.5", "256", config) == (
        15,
        0.5,
        256,
    )
    assert llm_client.resolve_inference_options(0, 3.5, -1, config) == (
        30,
        0.1,
        1024,
    )
    assert llm_client.resolve_inference_options(True, False, True, config) == (
        30,
        0.1,
        1024,
    )


def test_explicit_empty_token_does_not_fall_back_to_environment(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_environment_token_that_should_not_be_used")
    monkeypatch.setenv("HF_MODEL", "test/model")
    monkeypatch.setenv("HF_PROVIDER", "test-provider")

    response = llm_client.call_hf_inference(
        messages=[],
        model="   ",
        provider="   ",
        token="",
        timeout=0,
        temperature=4.0,
        max_tokens=-5,
    )

    assert response["status"] == "MISSING_TOKEN"
    assert response["model"] == "test/model"
    assert response["provider"] == "test-provider"
    assert response["latency_ms"] == 0.0


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


def test_hf_error_classification_is_stable_and_sanitized():
    cases = [
        ("401 Unauthorized", "UNAUTHORIZED"),
        ("Too many requests", "RATE_LIMITED"),
        ("503 model currently loading", "MODEL_UNAVAILABLE"),
        ("Connection timed out", "TIMEOUT"),
        ("Socket failure token=provider-secret", "API_ERROR"),
    ]

    for error, expected_status in cases:
        status, message = llm_client.classify_hf_error(
            error,
            model="example/model",
            timeout=15,
        )

        assert status == expected_status
        assert message
        assert "provider-secret" not in message


def test_hf_error_messages_include_safe_context():
    status, message = llm_client.classify_hf_error(
        "503 Service Unavailable",
        model="example/model",
        timeout=15,
    )
    assert status == "MODEL_UNAVAILABLE"
    assert "example/model" in message

    status, message = llm_client.classify_hf_error(
        "request timeout",
        model="example/model",
        timeout=15,
    )
    assert status == "TIMEOUT"
    assert "15s" in message


def test_hf_response_content_requires_nonempty_text():
    valid = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="  grounded answer  "))]
    )
    assert llm_client.extract_hf_response_content(valid) == "  grounded answer  "

    malformed_responses = [
        None,
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=None),
        SimpleNamespace(choices=[SimpleNamespace(message=None)]),
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
        ),
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="   "))]
        ),
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content={"text": "no"}))]
        ),
    ]

    for response in malformed_responses:
        assert llm_client.extract_hf_response_content(response) is None


def test_chat_message_validation_accepts_supported_roles():
    messages = [
        {"role": "system", "content": "Use only the supplied evidence."},
        {"role": "user", "content": "Summarize the rainfall record."},
        {"role": "assistant", "content": "I will ground the answer."},
        {"role": "tool", "content": "Evidence payload."},
    ]

    assert llm_client.validate_chat_messages(messages) is None


def test_chat_message_validation_rejects_malformed_inputs():
    malformed_inputs = [
        None,
        [],
        "not-a-list",
        ["not-an-object"],
        [{"role": "developer", "content": "unsupported"}],
        [{"role": "user"}],
        [{"role": "user", "content": None}],
        [{"role": "user", "content": "   "}],
    ]

    for messages in malformed_inputs:
        error = llm_client.validate_chat_messages(messages)
        assert isinstance(error, str)
        assert error


def test_invalid_messages_fail_before_sdk_or_network(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)

    response = llm_client.call_hf_inference(
        messages=[],
        token="hf_test_token_for_local_validation",
    )

    assert response["status"] == "INVALID_REQUEST"
    assert response["content"] is None
    assert response["latency_ms"] == 0.0


def test_response_sanitizer_redacts_common_credentials():
    message = (
        "api_key=abcdef1234567890 "
        "github_pat_abcdefghijklmnopqrstuvwxyz123456 "
        "Bearer abcdefghijklmnopqrstuvwxyz "
        "Authorization: Basic dXNlcjpwYXNzd29yZA== "
        "x-api-key: header-secret "
        "https://example.test/callback?token=query-secret&mode=safe"
    )

    sanitized = sanitize_sensitive_text(message)

    assert "abcdef1234567890" not in sanitized
    assert "github_pat_abcdefghijklmnopqrstuvwxyz123456" not in sanitized
    assert "abcdefghijklmnopqrstuvwxyz" not in sanitized
    assert "dXNlcjpwYXNzd29yZA==" not in sanitized
    assert "header-secret" not in sanitized
    assert "query-secret" not in sanitized
    assert "&mode=safe" in sanitized


def test_response_sanitizer_handles_password_and_refresh_token():
    message = "password=hunter2; refresh_token=refresh-me, result=denied"

    sanitized = sanitize_sensitive_text(message)

    assert "hunter2" not in sanitized
    assert "refresh-me" not in sanitized
    assert "result=denied" in sanitized
