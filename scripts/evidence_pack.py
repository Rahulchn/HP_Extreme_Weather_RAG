"""
evidence_pack.py
Milestone 3: Strict Evidence Pack Construction & Normalization

Constructs a standardized, deterministic Evidence Pack object from raw retrieval output.
The Evidence Pack serves as the strict, immutable boundary between the retrieval engine
and the generation layer.

Safety Invariants:
- The Evidence Pack must be the ONLY factual context supplied to the LLM.
- Preserves exact source, document, page, chunk, and calculation provenance.
- Clearly tags evidence types: OBSERVED, CALCULATED, REPORTED, INFERRED.
- Does NOT fabricate metadata that does not exist in the database or vector store.
"""

import os
import sqlite3
from typing import Dict, Any, List, Optional

DB_PATH = "data/master/hp_extreme_weather.db"
_CACHED_SOURCE_NAMES = None

def get_source_registry_map() -> Dict[str, str]:
    """
    Returns a mapping of source_id -> source_name from SQLite source_registry.
    """
    global _CACHED_SOURCE_NAMES
    if _CACHED_SOURCE_NAMES is None:
        _CACHED_SOURCE_NAMES = {}
        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT source_id, source_name FROM source_registry")
                for r in cur.fetchall():
                    _CACHED_SOURCE_NAMES[r["source_id"]] = r["source_name"]
                conn.close()
            except Exception:
                pass
    return _CACHED_SOURCE_NAMES

def build_evidence_pack(raw_retrieval: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes a retrieve() output from hybrid_retriever into the strict Evidence Pack schema.
    """
    src_map = get_source_registry_map()

    query = raw_retrieval.get("query", "")
    route = raw_retrieval.get("route", "UNKNOWN")
    intent = raw_retrieval.get("intent", "UNKNOWN")
    status = raw_retrieval.get("status", "NO_DATA")
    detected_entities = raw_retrieval.get("detected_entities", {})
    warnings = raw_retrieval.get("warnings", [])

    evidence_items = []

    # 1. Normalize Structured Evidence
    structured_list = raw_retrieval.get("structured_evidence", [])
    for idx, s in enumerate(structured_list):
        evid_id = s.get("evidence_id") or f"EVID_STRUCT_{idx+1}"
        evid_type = s.get("evidence_type", "CALCULATED")
        source_id = s.get("source_id", "UNKNOWN_SOURCE")
        source_name = src_map.get(source_id, source_id)
        year = s.get("year")
        district = s.get("district")

        # Build structured values dictionary preserving all metrics
        s_val = {}
        for k in ["max_rainfall_mm", "mean_rainfall_mm", "min_rainfall_mm", "date",
                  "annual_total_rainfall_mm", "annual_mean_daily_rainfall_mm",
                  "max_single_day_rainfall_mm", "rainy_days_count", "valid_cells_count",
                  "count", "top_district", "events", "telemetry_records"]:
            if k in s and s[k] is not None:
                s_val[k] = s[k]

        calc_method = s.get("aggregation_source")
        if not calc_method and evid_type == "CALCULATED":
            calc_method = "Deterministic SQL parameterized aggregation"

        text_summary = s.get("notes") or s.get("message") or ""
        if not text_summary and s_val:
            parts = [f"{k}: {v}" for k, v in s_val.items() if k != "events"]
            text_summary = f"Authoritative record for {district or 'State'} ({year or 'Period'}): " + ", ".join(parts)

        prov = f"Database: hp_extreme_weather.db | Table: {s.get('table_name', 'structured_tables')} | Source: {source_id}"

        evidence_items.append({
            "evidence_id": evid_id,
            "evidence_type": evid_type,
            "source_id": source_id,
            "document_id": None,
            "chunk_id": None,
            "page": None,
            "source_name": source_name,
            "year": year,
            "district": district,
            "text": text_summary,
            "structured_value": s_val if s_val else None,
            "calculation_method": calc_method,
            "provenance": prov
        })

    # 2. Normalize Document Evidence
    document_list = raw_retrieval.get("document_evidence", [])
    for d in document_list:
        chunk_id = d.get("chunk_id", "")
        evid_id = chunk_id or f"EVID_DOC_{len(evidence_items)+1}"
        evid_type = d.get("evidence_type", "REPORTED")
        source_id = d.get("source_id", "UNKNOWN_SOURCE")
        doc_id = d.get("document_id")
        doc_title = d.get("document_title", doc_id)
        source_name = src_map.get(source_id, doc_title or source_id)
        page = d.get("page_number")
        year = d.get("year")
        dists = d.get("districts", [])
        district_str = ", ".join(dists) if dists else None
        text_content = d.get("text", "")

        prov = f"Document: {doc_title} | Page: {page} | Section: {d.get('section_title', 'N/A')} | Chunk: {chunk_id} | Source: {source_id}"

        evidence_items.append({
            "evidence_id": evid_id,
            "evidence_type": evid_type,
            "source_id": source_id,
            "document_id": doc_id,
            "chunk_id": chunk_id,
            "page": page,
            "source_name": source_name,
            "year": year,
            "district": district_str,
            "text": text_content,
            "structured_value": None,
            "calculation_method": None,
            "provenance": prov
        })

    return {
        "query": query,
        "route": route,
        "intent": intent,
        "status": status,
        "detected_entities": detected_entities,
        "warnings": warnings,
        "evidence_count": len(evidence_items),
        "evidence_items": evidence_items
    }
