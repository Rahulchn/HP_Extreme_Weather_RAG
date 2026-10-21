"""
answer_validator.py
Milestone 3: Strict Answer Validation Layer

Performs deterministic validation on generated answers against the Evidence Pack.
Ensures zero hallucinations, 100% citation integrity, numerical preservation for SQL metrics,
rejection adherence, and 2026 partial-year safety.

Safety Invariants:
- Every cited evidence_id, source_id, chunk_id, document_id MUST exist in the Evidence Pack.
- Hallucinated citations cause immediate failure.
- For structured queries, authoritative numerical values from SQL must be preserved exactly.
- Rejection states must remain strictly rejected.
- 2026 answers must preserve partial/interim status.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

VALID_STATUSES = {
    "OK", "NO_SUPPORTED_EVIDENCE", "ZERO_RAINFALL", "ZERO_DOCUMENTED_EVENTS",
    "NO_DATA", "INSUFFICIENT_FOR_FULL_YEAR", "CONFLICTING_SOURCES", "GENERATION_UNAVAILABLE"
}

VALID_EVIDENCE_TYPES = {
    "OBSERVED", "CALCULATED", "REPORTED", "INFERRED", "MIXED", "INSUFFICIENT"
}

VALID_CONFIDENCES = {
    "HIGH", "MEDIUM", "LOW", "INSUFFICIENT"
}

DISALLOWED_GEOGRAPHIES = [
    "pune", "delhi", "mumbai", "chandigarh", "dehradun", "bilaspur", "solan",
    "atlantis", "xandaria", "jaipur", "bangalore", "kolkata"
]

_NUMBER_PATTERN = re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b")


def _extract_numbers(value: Any) -> List[float]:
    """Extract standalone integers and decimals from user-facing text."""
    if not isinstance(value, str):
        return []

    numbers: List[float] = []
    for token in _NUMBER_PATTERN.findall(value):
        try:
            numbers.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return numbers

def validate_answer(
    answer_obj: Dict[str, Any],
    evidence_pack: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deterministically validates answer_obj against evidence_pack across 6 criteria:
    A. Schema validation
    B. Citation integrity
    C. Numerical preservation
    D. Temporal boundary validation (2026 partial)
    E. Geographic scope validation
    F. Rejection validation
    """
    errors = []
    warnings = []

    # -------------------------------------------------------------
    # 0. API Failure Handling Pass-Through
    # -------------------------------------------------------------
    if answer_obj.get("status") == "GENERATION_UNAVAILABLE":
        return {
            "is_valid": True,
            "status": "GENERATION_UNAVAILABLE",
            "schema_valid": True,
            "citation_integrity_pct": 100.0,
            "numerical_preservation_pass": True,
            "rejection_preserved": True,
            "validation_errors": [],
            "warnings": ["LLM generation was unavailable; fallback handled safely."]
        }

    # -------------------------------------------------------------
    # A. Schema Validation
    # -------------------------------------------------------------
    raw_ans_text = answer_obj.get("answer")
    if not raw_ans_text or not isinstance(raw_ans_text, str) or len(raw_ans_text.strip()) == 0:
        errors.append("SCHEMA_ERROR: Missing or empty 'answer' text.")
    ans_text = raw_ans_text if isinstance(raw_ans_text, str) else ""

    ans_status = answer_obj.get("status")
    if ans_status not in VALID_STATUSES:
        errors.append(f"SCHEMA_ERROR: Invalid status '{ans_status}'. Must be one of {VALID_STATUSES}.")

    ans_ev_type = answer_obj.get("evidence_type")
    if ans_ev_type not in VALID_EVIDENCE_TYPES:
        errors.append(f"SCHEMA_ERROR: Invalid evidence_type '{ans_ev_type}'. Must be one of {VALID_EVIDENCE_TYPES}.")

    ans_conf = answer_obj.get("confidence")
    if ans_conf not in VALID_CONFIDENCES:
        errors.append(f"SCHEMA_ERROR: Invalid confidence '{ans_conf}'. Must be one of {VALID_CONFIDENCES}.")

    citations = answer_obj.get("citations")
    if not isinstance(citations, list):
        errors.append("SCHEMA_ERROR: 'citations' must be a list of citation dictionaries.")
        citations = []

    # -------------------------------------------------------------
    # B. Citation Integrity Validation
    # -------------------------------------------------------------
    raw_supplied_items = evidence_pack.get("evidence_items", [])
    if not isinstance(raw_supplied_items, list):
        warnings.append("EVIDENCE_PACK_WARNING: 'evidence_items' must be a list; ignoring malformed value.")
        raw_supplied_items = []
    supplied_items = [item for item in raw_supplied_items if isinstance(item, dict)]
    malformed_item_count = len(raw_supplied_items) - len(supplied_items)
    if malformed_item_count:
        warnings.append(
            f"EVIDENCE_PACK_WARNING: Ignored {malformed_item_count} malformed evidence item(s)."
        )
    citation_count = len(citations)
    valid_citations_count = 0
    hallucinated_citations = []

    for c in citations:
        if not isinstance(c, dict):
            hallucinated_citations.append(c)
            continue
        c_ev_id = c.get("evidence_id")
        c_chunk_id = c.get("chunk_id")
        c_src_id = c.get("source_id")
        c_doc_id = c.get("document_id")

        # Every supplied identifier must resolve to the same evidence item.
        # This prevents cross-wiring a valid evidence ID to another item's
        # otherwise-valid source or document ID.
        has_locator = bool(c_ev_id or c_chunk_id or c_src_id)
        matching_items = supplied_items
        for field, value in (
            ("evidence_id", c_ev_id),
            ("chunk_id", c_chunk_id),
            ("source_id", c_src_id),
        ):
            if value:
                matching_items = [
                    item for item in matching_items if item.get(field) == value
                ]
        if c_doc_id is not None:
            matching_items = [
                item for item in matching_items if item.get("document_id") == c_doc_id
            ]

        is_valid = has_locator and bool(matching_items)

        if is_valid:
            valid_citations_count += 1
        else:
            hallucinated_citations.append(c)

    if hallucinated_citations:
        errors.append(f"CITATION_INTEGRITY_VIOLATION: Found {len(hallucinated_citations)} citations not present in Evidence Pack: {hallucinated_citations}")

    citation_integrity_pct = 100.0 if citation_count == 0 else round(valid_citations_count / citation_count * 100, 2)

    # Document route must have citations if evidence was supplied
    route = evidence_pack.get("route", "")
    if route == "DOCUMENT" and supplied_items and citation_count == 0:
        warnings.append("DOCUMENT route answer provided 0 citations despite retrieved document evidence.")

    # Negative queries must have 0 citations
    if route == "NEGATIVE_REJECTED" and citation_count > 0:
        errors.append(f"REJECTION_CITATION_VIOLATION: Rejection response contained {citation_count} citations; expected 0.")

    # -------------------------------------------------------------
    # C. Numerical Preservation Validation (Structured Queries)
    # -------------------------------------------------------------
    numerical_pass = True
    if route == "STRUCTURED" and supplied_items:
        # Collect all valid authoritative numeric metrics from the Evidence Pack
        # Query numbers, such as a requested year, are safe context to repeat.
        valid_numbers = set(_extract_numbers(evidence_pack.get("query", "")))
        primary_metrics = []
        for item in supplied_items:
            s_val = item.get("structured_value") or {}
            for k in ["max_rainfall_mm", "mean_rainfall_mm", "min_rainfall_mm",
                      "annual_total_rainfall_mm", "annual_mean_daily_rainfall_mm",
                      "max_single_day_rainfall_mm", "count", "valid_cells_count"]:
                if k in s_val and s_val[k] is not None:
                    val = s_val[k]
                    try:
                        numeric_val = float(val)
                    except (TypeError, ValueError):
                        continue
                    valid_numbers.add(numeric_val)
                    if k in ("max_rainfall_mm", "mean_rainfall_mm", "annual_total_rainfall_mm", "max_single_day_rainfall_mm", "count"):
                        primary_metrics.append((k, numeric_val))

            # Also extract numbers from text notes
            valid_numbers.update(_extract_numbers(item.get("text", "")))

        # 1. Primary metric preservation: at least one key metric or zero indication must be in answer
        ans_status = answer_obj.get("status", "")
        if ans_status in ("ZERO_RAINFALL", "ZERO_DOCUMENTED_EVENTS"):
            # Check for 0, 0.0, zero, or none
            has_zero_mention = bool(re.search(r"\b(?:0|0\.0|zero|none|no events|no rainfall)\b", ans_text.lower()))
            if not has_zero_mention:
                errors.append(f"NUMERICAL_PRESERVATION_VIOLATION: Expected zero-value state '{ans_status}' not reflected in answer text.")
                numerical_pass = False
        elif primary_metrics and ans_status == "OK":
            found_primary = False
            for k, val in primary_metrics:
                patterns = [
                    re.escape(candidate)
                    for candidate in {str(val), f"{val:g}", f"{val:.1f}", f"{val:.2f}"}
                ]
                regex = r"(?<!\d)(" + "|".join(patterns) + r")(?!\d)"
                if re.search(regex, ans_text):
                    found_primary = True
                    break
            if not found_primary:
                errors.append(f"NUMERICAL_PRESERVATION_VIOLATION: Authoritative primary metric(s) missing from answer: {primary_metrics}")
                numerical_pass = False

        # 2. Prevent fabricated numerical metrics, including whole-number claims.
        for answer_number in _extract_numbers(ans_text):
            if not any(abs(answer_number - valid_number) < 0.05 for valid_number in valid_numbers):
                errors.append(f"NUMERICAL_FABRICATION_VIOLATION: Number '{answer_number}' in answer text is not grounded in Evidence Pack.")
                numerical_pass = False

    # -------------------------------------------------------------
    # D. Temporal Validation (2026 Partial Year)
    # -------------------------------------------------------------
    query_text = evidence_pack.get("query", "").lower()
    if "2026" in query_text:
        ans_lower = ans_text.lower() if ans_text else ""
        has_partial_mention = any(k in ans_lower for k in ["partial", "interim", "september 2026", "incomplete", "telemetry", "aws"])
        if not has_partial_mention and "annual" in query_text:
            errors.append("TEMPORAL_SAFETY_VIOLATION: 2026 annual inquiry did not explicitly preserve partial/interim status.")

    # -------------------------------------------------------------
    # E. Geographic Scope Validation
    # -------------------------------------------------------------
    if route != "NEGATIVE_REJECTED":
        ans_lower = ans_text.lower() if ans_text else ""
        for disallowed in DISALLOWED_GEOGRAPHIES:
            # Check if disallowed geography appears in answer unless it was part of the query
            if disallowed in ans_lower and disallowed not in query_text:
                errors.append(f"GEOGRAPHIC_HALLUCINATION: Disallowed out-of-scope geography '{disallowed}' introduced in answer.")

    # -------------------------------------------------------------
    # F. Rejection Validation
    # -------------------------------------------------------------
    rejection_pass = True
    if route == "NEGATIVE_REJECTED" or evidence_pack.get("status") == "NO_SUPPORTED_EVIDENCE":
        if answer_obj.get("status") not in ("NO_SUPPORTED_EVIDENCE", "GENERATION_UNAVAILABLE"):
            errors.append(f"REJECTION_OVERRIDE_VIOLATION: Rejected route status was overridden to '{answer_obj.get('status')}'.")
            rejection_pass = False

    # -------------------------------------------------------------
    # G. Hybrid Separation Validation
    # -------------------------------------------------------------
    if route == "HYBRID" and len(supplied_items) >= 2:
        ans_lower = ans_text.lower() if ans_text else ""
        has_rainfall_section = "rainfall" in ans_lower
        has_impact_section = any(k in ans_lower for k in ["impact", "damage", "casualt", "loss", "devastat", "flood"])
        if not (has_rainfall_section and has_impact_section):
            warnings.append("HYBRID_PARTITION_WARNING: Hybrid answer did not clearly separate rainfall from reported impacts.")

    is_valid = (len(errors) == 0)

    return {
        "is_valid": is_valid,
        "status": "PASSED" if is_valid else "FAILED",
        "schema_valid": ans_status in VALID_STATUSES and ans_ev_type in VALID_EVIDENCE_TYPES and ans_conf in VALID_CONFIDENCES,
        "citation_integrity_pct": citation_integrity_pct,
        "citation_count": citation_count,
        "valid_citations_count": valid_citations_count,
        "numerical_preservation_pass": numerical_pass,
        "rejection_preserved": rejection_pass,
        "validation_errors": errors,
        "warnings": warnings
    }
