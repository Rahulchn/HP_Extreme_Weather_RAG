"""
answer_generator.py
Milestone 3: Grounded Answer Generation Layer

Consumes the normalized Evidence Pack from scripts/evidence_pack.py,
constructs a strictly bounded prompt embodying the 16 Grounding Rules,
calls the Hugging Face Inference API via scripts/llm_client.py,
and parses the structured grounded answer conforming to the Answer Contract.

Safety Invariants:
- The LLM is ONLY a generation/synthesis component; it is NOT the source of truth.
- Answers are strictly grounded in the supplied Evidence Pack.
- NEGATIVE_REJECTED queries receive a deterministic safe refusal without an LLM call.
- Structured numerical answers preserve exact SQL metrics without recalculation.
- Hybrid answers strictly partition Rainfall vs Reported Impacts.
- API failures return status GENERATION_UNAVAILABLE without fabricating answers.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
import scripts.llm_client as llm
import scripts.evidence_pack as ep

GROUNDING_SYSTEM_PROMPT = """You are the grounded answering engine for the Himachal Pradesh Extreme Weather RAG System (2011-2026).
You are a language synthesizer, NOT a source of truth. You must answer questions using ONLY the facts present in the provided Evidence Pack.

STRICT GROUNDING RULES:
1. Answer ONLY from the supplied Evidence Pack. Do not use outside world knowledge to supplement missing information.
2. NEVER invent numerical values. If a number is not in the Evidence Pack, you must not state it.
3. NEVER invent dates, years, districts, locations, disaster events, or institutions.
4. NEVER invent or fabricate citations or source names.
5. NEVER silently broaden geographic scope beyond the target districts (Kangra, Mandi, Shimla, Kullu).
6. NEVER treat CALCULATED values (such as spatial grid means or SQL aggregates) as official observed station readings. Explicitly label them as CALCULATED.
7. Strictly distinguish evidence types:
    - OBSERVED: Direct sensor/gauge observations.
    - CALCULATED: Spatial grid or statistical aggregates.
    - REPORTED: Government memorandums, disaster reports, scientific studies.
    - INFERRED: Logical deduction derived strictly from supplied evidence.
    - MIXED: Used whenever the Evidence Pack contains multiple distinct evidence types (e.g. CALCULATED + REPORTED).
8. If an inference is made, explicitly tag it as INFERRED. Do not present inferences as facts.
9. State clearly when evidence is insufficient or when no records exist.
10. Respect distinct data states:
    - ZERO_RAINFALL: Valid observation recorded as 0.0 mm.
    - ZERO_DOCUMENTED_EVENTS: The official record documents 0 occurrences.
    - NO_DATA: No observation exists for the specified query criteria.
    - INSUFFICIENT_FOR_FULL_YEAR: The period has incomplete temporal coverage (e.g., 2026 data is partial).
    - NO_SUPPORTED_EVIDENCE: Out of scope geography, unsupported parameter, or unverified entity.
11. Treat 2026 data as strictly PARTIAL/interim telemetry; NEVER imply that 2026 is a complete historical annual record.
12. NEVER convert absence of evidence into evidence of absence. If a document does not mention an event, state that it is not documented in the supplied source, not that it never happened.
13. If sources conflict, explicitly report the conflict and cite both sources rather than choosing one.
14. Cite ONLY evidence_id, chunk_id, and source_id values that exist in the supplied Evidence Pack.
15. For HYBRID queries containing both structured rainfall and document narratives, you MUST present your answer with two distinct, labeled sections:
    - Rainfall: [structured/calculated or observed evidence with exact figures]
    - Reported Impacts: [document-supported narrative findings with citations]
16. "evidence_type" MUST contain EXACTLY ONE canonical enum string from: ["OBSERVED", "CALCULATED", "REPORTED", "INFERRED", "MIXED", "INSUFFICIENT"].
    - If the supplied Evidence Pack contains multiple distinct evidence types (such as CALCULATED + REPORTED), you MUST use: "MIXED".
    - NEVER concatenate, combine, or join enum values.
    - Examples:
      * Evidence types supplied: CALCULATED + REPORTED
        CORRECT:   "evidence_type": "MIXED"
        INCORRECT: "evidence_type": "REPORTED | CALCULATED"
        INCORRECT: "evidence_type": "CALCULATED/REPORTED"
        INCORRECT: "evidence_type": "OBSERVED + REPORTED"
17. Your response MUST be valid JSON conforming exactly to the Answer Contract.

ANSWER CONTRACT SCHEMA:
{
  "answer": "Concise, factual, grounded answer text.",
  "status": "OK | NO_SUPPORTED_EVIDENCE | ZERO_RAINFALL | ZERO_DOCUMENTED_EVENTS | NO_DATA | INSUFFICIENT_FOR_FULL_YEAR | CONFLICTING_SOURCES",
  "evidence_type": "OBSERVED | CALCULATED | REPORTED | INFERRED | MIXED | INSUFFICIENT",
  "confidence": "HIGH | MEDIUM | LOW | INSUFFICIENT",
  "citations": [
    {
      "evidence_id": "Exact evidence_id from Evidence Pack",
      "source_id": "Exact source_id from Evidence Pack",
      "document_id": "document_id or null",
      "chunk_id": "chunk_id or null",
      "page": "page number or null"
    }
  ]
}
"""

def generate_deterministic_negative_answer(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates an authoritative, deterministic refusal for NEGATIVE_REJECTED queries.
    Per Phase 5: NEGATIVE_REJECTED queries must NOT call an LLM to hallucinate or reinterpret facts.
    """
    warnings = evidence_pack.get("warnings", [])
    reason_msg = warnings[0] if warnings else "Query references entities, parameters, or dates outside authorized project scope."
    detected = evidence_pack.get("detected_entities", {})

    refusal_text = f"Refusal / No Supported Evidence: {reason_msg} " \
                   f"The system covers 4 authorized districts (Kangra, Mandi, Shimla, Kullu) across 2011-2026 " \
                   f"for rainfall, cloudbursts, and flash floods."

    return {
        "answer": refusal_text,
        "status": "NO_SUPPORTED_EVIDENCE",
        "evidence_type": "REPORTED",
        "confidence": "HIGH",
        "citations": [],
        "metadata": {
            "mode": "DETERMINISTIC_ROUTER_REFUSAL",
            "detected_entities": detected,
            "route": "NEGATIVE_REJECTED"
        }
    }

def format_evidence_pack_for_prompt(evidence_pack: Dict[str, Any]) -> str:
    """Formats the Evidence Pack into a clean, serialized string for the LLM user prompt."""
    lines = [
        f"USER QUERY: {evidence_pack.get('query')}",
        f"ROUTE: {evidence_pack.get('route')}",
        f"INTENT: {evidence_pack.get('intent')}",
        f"RETRIEVAL STATUS: {evidence_pack.get('status')}",
    ]

    warnings = evidence_pack.get("warnings", [])
    if warnings:
        lines.append(f"RETRIEVAL WARNINGS: {'; '.join(warnings)}")

    items = evidence_pack.get("evidence_items", [])
    lines.append(f"\nSUPPLIED EVIDENCE ITEMS ({len(items)} items):")

    if not items:
        lines.append("  [NO EVIDENCE RETRIEVED]")
    else:
        for idx, item in enumerate(items, 1):
            lines.append(f"\n--- Evidence Item {idx} ---")
            lines.append(f"  evidence_id: {item.get('evidence_id')}")
            lines.append(f"  evidence_type: {item.get('evidence_type')}")
            lines.append(f"  source_id: {item.get('source_id')}")
            lines.append(f"  source_name: {item.get('source_name')}")
            if item.get("document_id"):
                lines.append(f"  document_id: {item.get('document_id')}")
            if item.get("chunk_id"):
                lines.append(f"  chunk_id: {item.get('chunk_id')}")
            if item.get("page") is not None:
                lines.append(f"  page: {item.get('page')}")
            if item.get("district"):
                lines.append(f"  district: {item.get('district')}")
            if item.get("year"):
                lines.append(f"  year: {item.get('year')}")
            if item.get("calculation_method"):
                lines.append(f"  calculation_method: {item.get('calculation_method')}")
            if item.get("structured_value"):
                lines.append(f"  structured_value: {json.dumps(item.get('structured_value'))}")
            if item.get("text"):
                lines.append(f"  content_text: {item.get('text').strip()}")
            lines.append(f"  provenance: {item.get('provenance')}")

    lines.append("\nINSTRUCTIONS FOR RESPONSE:")
    lines.append("Synthesize the response according to the 17 Grounding Rules. Produce ONLY a single JSON object conforming to the Answer Contract.")
    lines.append("CRITICAL: 'evidence_type' MUST be exactly ONE canonical string from ['OBSERVED', 'CALCULATED', 'REPORTED', 'INFERRED', 'MIXED', 'INSUFFICIENT'].")
    lines.append("If multiple evidence types are supplied in the Evidence Pack (e.g. CALCULATED + REPORTED), you MUST use 'MIXED'. NEVER output concatenated strings such as 'REPORTED | CALCULATED'.")
    return "\n".join(lines)

def parse_llm_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """Strips markdown formatting and parses JSON response from the LLM."""
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    # Strip markdown code blocks ```json ... ```
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "answer" in data:
            return data
    except Exception:
        pass

    # Try searching for outermost curly braces
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cand = cleaned[start:end+1]
            data = json.loads(cand)
            if isinstance(data, dict) and "answer" in data:
                return data
    except Exception:
        pass

    return None

def generate_answer(evidence_pack: Dict[str, Any], **hf_kwargs) -> Dict[str, Any]:
    """
    Main entry point for grounded answer generation.
    Accepts normalized Evidence Pack and returns structured Answer Contract.
    """
    route = evidence_pack.get("route", "")

    # 1. Phase 5: NEGATIVE_REJECTED queries use deterministic safe refusal
    if route == "NEGATIVE_REJECTED" or evidence_pack.get("status") == "NO_SUPPORTED_EVIDENCE":
        if not evidence_pack.get("evidence_items"):
            return generate_deterministic_negative_answer(evidence_pack)

    # 2. Build user prompt
    user_prompt = format_evidence_pack_for_prompt(evidence_pack)
    messages = [
        {"role": "system", "content": GROUNDING_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    # 3. Call Hugging Face API
    llm_resp = llm.call_hf_inference(messages, **hf_kwargs)
    status = llm_resp.get("status")

    # 4. Phase 13: Handle API Failures Gracefully
    if status != "OK":
        return {
            "answer": f"Generation unavailable: {llm_resp.get('error_message')}",
            "status": "GENERATION_UNAVAILABLE",
            "evidence_type": "INSUFFICIENT",
            "confidence": "INSUFFICIENT",
            "citations": [],
            "metadata": {
                "client_status": status,
                "model": llm_resp.get("model"),
                "error": llm_resp.get("error_message"),
                "latency_ms": llm_resp.get("latency_ms", 0.0),
                "evidence_pack_preserved": True
            }
        }

    # 5. Parse JSON response
    raw_content = llm_resp.get("content", "")
    parsed = parse_llm_json_response(raw_content)

    if not parsed:
        return {
            "answer": "Generation failed: The language model returned a response that could not be parsed into the required Answer Contract schema.",
            "status": "GENERATION_UNAVAILABLE",
            "evidence_type": "INSUFFICIENT",
            "confidence": "INSUFFICIENT",
            "citations": [],
            "metadata": {
                "client_status": "MALFORMED_OUTPUT",
                "raw_content": raw_content[:500],
                "model": llm_resp.get("model"),
                "latency_ms": llm_resp.get("latency_ms", 0.0)
            }
        }

    # Ensure required fields exist in parsed output
    ans_text = parsed.get("answer", "").strip()
    ans_status = parsed.get("status", evidence_pack.get("status", "OK"))
    ans_ev_type = parsed.get("evidence_type", "REPORTED")
    ans_conf = parsed.get("confidence", "HIGH")
    citations = parsed.get("citations", [])

    return {
        "answer": ans_text,
        "status": ans_status,
        "evidence_type": ans_ev_type,
        "confidence": ans_conf,
        "citations": citations,
        "metadata": {
            "client_status": "OK",
            "model": llm_resp.get("model"),
            "latency_ms": llm_resp.get("latency_ms", 0.0),
            "evidence_pack_query": evidence_pack.get("query"),
            "route": route
        }
    }
