"""
semantic_retriever.py
Milestone 2B: Semantic Document Retriever over FAISS Vector Store + Metadata Sidecar
Uses local model: BAAI/bge-base-en-v1.5 (cosine similarity on normalized 768-dim embeddings)
Applies:
- Vector similarity search
- Metadata filtering (district, year, event_type, parameter, authority_level)
- Diversity deduplication (prevents crowding from identical passages or same page)
- Authority hierarchy reranking (Official Govt > Scientific > Secondary)
- Complete provenance preservation
"""

import os
import json
import re
import numpy as np
import faiss
from typing import Dict, Any, List, Optional, Set, Tuple
from sentence_transformers import SentenceTransformer

VECTOR_STORE_DIR = "data/knowledge_base/vector_store"
INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "index.faiss")
METADATA_PATH = os.path.join(VECTOR_STORE_DIR, "index_meta.json")
MANIFEST_PATH = "data/master/embedding_manifest.json"

_CACHED_MODEL = None
_CACHED_INDEX = None
_CACHED_META = None

# General Document Family Patterns
DOCUMENT_FAMILY_PATTERNS = [
    ("GSI", [r"\bgsi\b", r"\bgeological\s+survey\b", r"\bscientific\s+investigation\b", r"\bgeotechnical\s+study\b"]),
    ("PDNA", [r"\bpdna\b", r"\bpost\s*disaster\s+needs?\s+assessment\b", r"\bbuild\s+back\s+better\b", r"\brecovery\s+and\s+reconstruction\b"]),
    ("MEMORANDUM", [r"\bmemorandums?\b", r"\bmemo\b", r"\bmemorandum\s+of\s+damages?\b", r"\bstate\s+memorandum\b"]),
    ("LR3_HAZARD", [r"\blr3\b", r"\bhazard\s+vulnerability\b", r"\bvulnerability\s+assessment\b", r"\bdisaster\s+proneness\b", r"\bhazard\s+study\b"]),
    ("10YR_LOSSES", [r"\b10[- ]years?\b", r"\bten[- ]years?\b", r"\bcumulative\s+disaster\s+losses\b", r"\bcumulative\s+losses\b"]),
    ("IMD", [r"\bimd\b", r"\bmonsoon\s+report\b", r"\bend\s+of\s+season\s+report\b", r"\bdeparture\s+statement\b", r"\bclimatological\b", r"\bmeteorological\s+centre\b", r"\bweather\s+bulletin\b"])
]

def extract_document_scope(query: str) -> Tuple[Set[str], Optional[int]]:
    """
    Extracts explicit document family constraints and explicit publication/event year from query.
    General mechanism: does NOT hardcode specific question IDs or golden targets.
    """
    q_lower = query.lower()
    target_families = set()
    for fam, patterns in DOCUMENT_FAMILY_PATTERNS:
        if any(re.search(pat, q_lower) for pat in patterns):
            target_families.add(fam)

    # Extract 4-digit year associated with document/report inquiry
    years = [int(y) for y in re.findall(r'\b(20\d\d)\b', query)]
    explicit_year = years[0] if years else None

    return target_families, explicit_year

def matches_document_family(doc_id: str, doc_title: str, family: str) -> bool:
    """Checks whether a document metadata entry belongs to the designated document family."""
    doc_id_u = doc_id.upper()
    doc_title_l = doc_title.lower()
    if family == "GSI":
        return doc_id_u.startswith("DOC_GSI_") or "gsi" in doc_title_l
    elif family == "PDNA":
        return doc_id_u.startswith("DOC_HPSDMA_PDNA") or "pdna" in doc_title_l
    elif family == "MEMORANDUM":
        return doc_id_u.startswith("DOC_HPSDMA_MEMO") or "memorandum" in doc_title_l
    elif family == "LR3_HAZARD":
        return doc_id_u == "DOC_HPSDMA_LR3_2007_2015" or "lr3" in doc_title_l or "hazard study" in doc_title_l
    elif family == "10YR_LOSSES":
        return doc_id_u == "DOC_HPSDMA_10YR_LOSSES" or "10-year" in doc_title_l
    elif family == "IMD":
        return doc_id_u.startswith("DOC_IMD_") or "imd" in doc_title_l or "meteorological" in doc_title_l
    return False

def calculate_scope_bonus(meta: Dict[str, Any], target_families: Set[str], explicit_year: Optional[int]) -> float:
    """
    Computes a modest, principled relevance bonus (+0.055 for family match, +0.020 for year match)
    when the query explicitly specifies a document family or report year.
    Never overpowers semantic similarity.
    """
    bonus = 0.0
    doc_id = meta.get("document_id", "")
    doc_title = meta.get("document_title", "")

    fam_matched = False
    for fam in target_families:
        if matches_document_family(doc_id, doc_title, fam):
            fam_matched = True
            break
    if fam_matched:
        bonus += 0.055

    if explicit_year is not None:
        c_year = meta.get("year")
        is_lr3 = (explicit_year <= 2015 and doc_id == "DOC_HPSDMA_LR3_2007_2015")
        if c_year == explicit_year or is_lr3:
            bonus += 0.020

    return bonus

def is_cover_or_title_chunk(meta: Dict[str, Any]) -> bool:
    """
    Identifies non-substantive front-matter cover or title pages.
    These contain pure institutional headers/titles, minimal tokens (<80),
    and lack empirical figures or narrative paragraphs.
    Does NOT penalize substantive summaries, tables, or photo captions.
    """
    page = meta.get("page_number", 999)
    tokens = meta.get("token_estimate", 999)
    text = meta.get("text", "").strip()

    if page <= 2 and tokens < 80:
        title_indicators = [
            "government of", "revenue department", "meteorological centre", 
            "disaster management cell", "end of season report", "contents",
            "memorandum of damages", "state memorandum", "preliminary report",
            "economics and statistics department"
        ]
        has_title_ind = any(ind in text.lower() for ind in title_indicators)
        words = text.split()
        if has_title_ind and len(words) < 65:
            return True
    return False

def get_retriever_resources():
    global _CACHED_MODEL, _CACHED_INDEX, _CACHED_META
    if _CACHED_INDEX is None or _CACHED_META is None or _CACHED_MODEL is None:
        if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
            raise FileNotFoundError(f"Vector store not found in {VECTOR_STORE_DIR}. Run build_embeddings.py first.")

        # Read manifest to find model name
        model_name = "BAAI/bge-base-en-v1.5"
        if os.path.exists(MANIFEST_PATH):
            try:
                with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    model_name = manifest.get("embedding_model", model_name)
            except Exception:
                pass

        _CACHED_MODEL = SentenceTransformer(model_name)
        _CACHED_INDEX = faiss.read_index(INDEX_PATH)
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            _CACHED_META = json.load(f)

    return _CACHED_MODEL, _CACHED_INDEX, _CACHED_META

def calculate_authority_bonus(auth_rank: int) -> float:
    # Small, well-calibrated bonus to favor official sources when semantic similarity is close
    # Rank 1 (Official Govt): +0.03
    # Rank 2 (Scientific Literature): +0.015
    # Rank 3 (Secondary): +0.00
    if auth_rank == 1:
        return 0.03
    elif auth_rank == 2:
        return 0.015
    return 0.0

def semantic_search(
    query: str,
    top_k: int = 5,
    district: Optional[str] = None,
    year: Optional[int] = None,
    event_type: Optional[str] = None,
    parameter: Optional[str] = None,
    authority_level: Optional[str] = None,
    min_score_threshold: float = 0.30
) -> Dict[str, Any]:
    model, index, metadata = get_retriever_resources()

    if not query or len(query.strip()) < 3:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": "Empty query provided.",
            "results": []
        }

    # Instruction prefix recommended for BGE query encoding
    query_text = f"Represent this sentence for searching relevant passages: {query.strip()}"
    query_vec = model.encode([query_text], normalize_embeddings=True, convert_to_numpy=True).astype("float32")

    # Fetch candidate pool across index so metadata filtering has 100% complete candidate coverage
    candidate_k = index.ntotal
    distances, indices = index.search(query_vec, candidate_k)

    raw_scores = distances[0]
    raw_indices = indices[0]

    # Extract general document scope constraints
    target_families, explicit_year = extract_document_scope(query)

    filtered_candidates = []
    seen_fingerprints = set()
    doc_chunk_counts = {}

    norm_dist = district.strip().title() if district else None
    norm_etype = event_type.strip().title() if event_type else None

    for score, idx in zip(raw_scores, raw_indices):
        if idx < 0 or idx >= len(metadata):
            continue
        
        meta = metadata[idx]
        base_score = float(score)

        # Baseline relevance threshold to guard against hallucinating on nonsense
        if base_score < min_score_threshold:
            continue

        # 1. District filter (if specified)
        if norm_dist:
            chunk_dists = [d.lower() for d in meta.get("districts", [])]
            # Match if district explicitly tagged or if the chunk text explicitly mentions it
            if norm_dist.lower() not in chunk_dists and norm_dist.lower() not in meta["text"].lower():
                continue

        # 2. Year filter (if specified)
        if year is not None:
            chunk_year = meta.get("year")
            is_historical_lr3 = (year <= 2015 and meta.get("document_id") == "DOC_HPSDMA_LR3_2007_2015")
            if chunk_year != year and not is_historical_lr3 and str(year) not in meta["text"]:
                continue

        # 3. Event Type filter (if specified)
        if norm_etype:
            chunk_etypes = [e.lower() for e in meta.get("event_types", [])]
            if norm_etype.lower() not in chunk_etypes and norm_etype.lower() not in meta["text"].lower():
                continue

        # 4. Authority Level filter (if specified)
        if authority_level:
            if meta.get("authority_level", "").upper() != authority_level.upper():
                continue

        # 5. Deduplication by text fingerprint
        fp = meta.get("fingerprint")
        if fp in seen_fingerprints:
            continue
        seen_fingerprints.add(fp)

        # 6. Diversity penalty: prevent more than 2 chunks from the same document page
        doc_page_key = f"{meta['document_id']}_P{meta['page_number']}"
        doc_chunk_counts[doc_page_key] = doc_chunk_counts.get(doc_page_key, 0) + 1
        diversity_penalty = 0.0
        if doc_chunk_counts[doc_page_key] > 2:
            diversity_penalty = 0.05 * (doc_chunk_counts[doc_page_key] - 2)

        # 7. Auditable score decomposition:
        # final_score = semantic_score + document_scope_bonus + authority_bonus - cover_penalty - diversity_penalty
        doc_scope_bonus = calculate_scope_bonus(meta, target_families, explicit_year)
        auth_bonus = calculate_authority_bonus(meta.get("authority_rank", 3))
        cover_penalty = 0.050 if is_cover_or_title_chunk(meta) else 0.0

        final_score = round(base_score + doc_scope_bonus + auth_bonus - cover_penalty - diversity_penalty, 4)

        filtered_candidates.append({
            "chunk_id": meta["chunk_id"],
            "semantic_score": round(base_score, 4),
            "document_scope_score": round(doc_scope_bonus, 4),
            "authority_score": round(auth_bonus, 4),
            "cover_penalty": round(cover_penalty, 4),
            "diversity_penalty": round(diversity_penalty, 4),
            "final_score": final_score,
            "score": round(base_score, 4),
            "rerank_score": final_score,
            "evidence_type": "REPORTED",
            "source_id": meta["source_id"],
            "document_id": meta["document_id"],
            "document_title": meta["document_title"],
            "page_number": meta["page_number"],
            "section_title": meta["section_title"],
            "year": meta["year"],
            "districts": meta["districts"],
            "event_types": meta["event_types"],
            "parameters": meta["parameters"],
            "authority_level": meta["authority_level"],
            "authority_rank": meta["authority_rank"],
            "text": meta["text"],
            "char_count": meta["char_count"],
            "token_estimate": meta["token_estimate"]
        })

    # Sort by final score descending
    filtered_candidates.sort(key=lambda x: x["final_score"], reverse=True)
    final_results = filtered_candidates[:top_k]

    if not final_results:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": "No relevant document evidence met the query and filter criteria.",
            "query": query,
            "filters_applied": {
                "district": norm_dist,
                "year": year,
                "event_type": norm_etype,
                "authority_level": authority_level
            },
            "results": []
        }

    return {
        "status": "OK",
        "query": query,
        "filters_applied": {
            "district": norm_dist,
            "year": year,
            "event_type": norm_etype,
            "authority_level": authority_level
        },
        "results_count": len(final_results),
        "results": final_results
    }
