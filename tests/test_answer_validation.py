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


def test_missing_answer_fails_without_crashing():
    answer = _answer("placeholder")
    answer.pop("answer")

    result = validate_answer(answer, _evidence_pack())

    assert result["status"] == "FAILED"
    assert any("Missing or empty 'answer'" in error for error in result["validation_errors"])


def test_malformed_evidence_items_are_ignored_safely():
    evidence_pack = _evidence_pack()
    evidence_pack["evidence_items"].append("not-an-evidence-object")

    result = validate_answer(
        _answer("In 2023, Kangra recorded 79.8 mm across 3 events."),
        evidence_pack,
    )

    assert result["status"] == "PASSED"
    assert any("Ignored 1 malformed evidence item" in warning for warning in result["warnings"])


def test_rejects_cross_wired_citation_identifiers():
    evidence_pack = _evidence_pack()
    evidence_pack["evidence_items"].append(
        {
            "evidence_id": "E2",
            "source_id": "SRC2",
            "document_id": "DOC2",
            "chunk_id": "CHUNK2",
            "text": "A separate evidence record.",
        }
    )

    result = validate_answer(
        _answer(
            "In 2023, Kangra recorded 79.8 mm across 3 events.",
            citations=[{"evidence_id": "E1", "source_id": "SRC2"}],
        ),
        evidence_pack,
    )

    assert result["status"] == "FAILED"
    assert result["citation_integrity_pct"] == 0.0
    assert any(
        "CITATION_INTEGRITY_VIOLATION" in error
        for error in result["validation_errors"]
    )


def test_rejects_invalid_identifier_even_if_another_identifier_is_valid():
    evidence_pack = _evidence_pack()
    evidence_pack["evidence_items"][0]["chunk_id"] = "CHUNK1"

    result = validate_answer(
        _answer(
            "In 2023, Kangra recorded 79.8 mm across 3 events.",
            citations=[{"evidence_id": "UNKNOWN", "chunk_id": "CHUNK1"}],
        ),
        evidence_pack,
    )

    assert result["status"] == "FAILED"
    assert result["citation_integrity_pct"] == 0.0


def test_rejects_citation_page_from_another_evidence_record():
    evidence_pack = _evidence_pack()
    evidence_pack["evidence_items"][0].update(
        {"document_id": "DOC1", "chunk_id": "CHUNK1", "page": 4}
    )

    result = validate_answer(
        _answer(
            "In 2023, Kangra recorded 79.8 mm across 3 events.",
            citations=[
                {
                    "evidence_id": "E1",
                    "source_id": "SRC1",
                    "document_id": "DOC1",
                    "chunk_id": "CHUNK1",
                    "page": 5,
                }
            ],
        ),
        evidence_pack,
    )

    assert result["status"] == "FAILED"
    assert result["citation_integrity_pct"] == 0.0


def test_accepts_equivalent_string_page_number():
    evidence_pack = _evidence_pack()
    evidence_pack["evidence_items"][0]["page"] = 4

    result = validate_answer(
        _answer(
            "In 2023, Kangra recorded 79.8 mm across 3 events.",
            citations=[{"evidence_id": "E1", "source_id": "SRC1", "page": "4"}],
        ),
        evidence_pack,
    )

    assert result["status"] == "PASSED"
    assert result["citation_integrity_pct"] == 100.0


def test_rejects_page_when_evidence_has_no_page():
    result = validate_answer(
        _answer(
            "In 2023, Kangra recorded 79.8 mm across 3 events.",
            citations=[{"evidence_id": "E1", "source_id": "SRC1", "page": "None"}],
        ),
        _evidence_pack(),
    )

    assert result["status"] == "FAILED"
    assert result["citation_integrity_pct"] == 0.0
