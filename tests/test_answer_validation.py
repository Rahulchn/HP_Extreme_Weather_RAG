from scripts.answer_validator import validate_answer


def _evidence_pack():
    return {
        "query": "What was the maximum rainfall in Kangra in 2023?",
        "route": "STRUCTURED",
        "status": "OK",
        "evidence_items": [
            {
                "evidence_id": "E1",
                "source_id": "SRC1",
                "structured_value": {"max_rainfall_mm": 79.8, "count": 3},
                "text": "Kangra 2023 maximum rainfall was 79.8 mm across 3 events.",
            }
        ],
    }


def _answer(text, citations=None):
    return {
        "status": "OK",
        "answer": text,
        "evidence_type": "CALCULATED",
        "confidence": "HIGH",
        "citations": citations
        if citations is not None
        else [{"evidence_id": "E1", "source_id": "SRC1"}],
    }


def test_accepts_grounded_integer_decimal_and_year():
    result = validate_answer(
        _answer("In 2023, Kangra recorded 79.8 mm across 3 events."),
        _evidence_pack(),
    )

    assert result["status"] == "PASSED"


def test_rejects_fabricated_integer_claim():
    result = validate_answer(
        _answer("In 2023, Kangra recorded 79.8 mm across 99 events."),
        _evidence_pack(),
    )

    assert result["status"] == "FAILED"
    assert any(
        "NUMERICAL_FABRICATION_VIOLATION" in error
        for error in result["validation_errors"]
    )


def test_malformed_citation_fails_without_crashing():
    result = validate_answer(
        _answer("Kangra recorded 79.8 mm across 3 events.", citations=["E1"]),
        _evidence_pack(),
    )

    assert result["status"] == "FAILED"
    assert any(
        "CITATION_INTEGRITY_VIOLATION" in error
        for error in result["validation_errors"]
    )
