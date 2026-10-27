"""Focused tests for robust structured-answer parsing."""

import json

import pytest

from scripts import answer_generator
from scripts.answer_generator import parse_llm_json_response


def _answer_payload(answer: str = "Grounded answer") -> dict:
    return {
        "answer": answer,
        "status": "OK",
        "evidence_type": "REPORTED",
        "confidence": "HIGH",
        "citations": [],
    }


def test_parser_accepts_plain_and_fenced_json():
    payload = _answer_payload()
    encoded = json.dumps(payload)

    assert parse_llm_json_response(encoded) == payload
    assert parse_llm_json_response(f"```json\n{encoded}\n```") == payload


def test_parser_finds_answer_after_invalid_brace_fragment():
    payload = _answer_payload("Recovered answer")
    raw = f"Model note {{not valid json}}\nFinal response: {json.dumps(payload)}"

    assert parse_llm_json_response(raw) == payload


def test_parser_skips_invalid_fence_and_uses_later_valid_fence():
    payload = _answer_payload("Second block")
    raw = (
        "```json\n{invalid}\n```\n"
        f"```json\n{json.dumps(payload)}\n```"
    )

    assert parse_llm_json_response(raw) == payload


def test_parser_rejects_non_answers_and_invalid_input():
    invalid_values = [
        None,
        "",
        "   ",
        "[]",
        '{"status": "OK"}',
        '{"answer": "   "}',
        '{"answer": 42}',
        '{"metadata": {"answer": "nested only"}}',
        "No JSON here",
    ]

    for value in invalid_values:
        assert parse_llm_json_response(value) is None


@pytest.mark.parametrize(
    "route,status",
    [("NEGATIVE_REJECTED", "OK"), ("STRUCTURED", "NO_SUPPORTED_EVIDENCE")],
)
@pytest.mark.parametrize("has_evidence", [False, True])
def test_rejected_queries_never_call_model(monkeypatch, route, status, has_evidence):
    def unexpected_inference(*args, **kwargs):
        pytest.fail("Rejected queries must not call the language model")

    monkeypatch.setattr(answer_generator.llm, "call_hf_inference", unexpected_inference)
    evidence_pack = {
        "query": "Show rainfall outside the supported region",
        "route": route,
        "status": status,
        "warnings": ["The requested geography is outside authorized scope."],
        "evidence_items": [{"evidence_id": "LEFTOVER_EVIDENCE"}] if has_evidence else [],
    }

    result = answer_generator.generate_answer(evidence_pack)

    assert result["status"] == "NO_SUPPORTED_EVIDENCE"
    assert result["citations"] == []
    assert evidence_pack["warnings"][0] in result["answer"]
    assert result["metadata"]["mode"] == "DETERMINISTIC_ROUTER_REFUSAL"
