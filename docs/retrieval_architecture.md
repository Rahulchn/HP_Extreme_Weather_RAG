# Retrieval Layer Architecture & Design Specification

## Himachal Pradesh Extreme Weather RAG System (Milestone 2B)

### 1. Executive Architectural Summary
The retrieval layer implements a **Hybrid Dual-Engine Architecture** designed to answer complex hydro-meteorological and disaster inquiries across Himachal Pradesh (2011–2026).
Quantitative meteorological observations and tabulated event logs are routed to an **Authoritative SQLite Structured Engine**, while qualitative disaster assessments, field studies, and administrative memorandums are routed to a **Local Semantic Vector Store**.

The pipeline explicitly **STOPS at the provenanced RETRIEVAL RESULT**, producing standardized evidence packets for future LLM synthesis without fabricating natural language prose.

```
                            USER QUERY
                                 |
                                 v
                     DETERMINISTIC ROUTER
                 (docs/query_routing_rules.md)
                                 |
        +------------------------+------------------------+
        |                                                 |
        v                                                 v
[STRUCTURED ROUTE]                                [SEMANTIC ROUTE]
SQLite Engine (hp_extreme_weather.db)             FAISS Vector Store (Option A)
- Parameterized SQL functions                     - BAAI/bge-base-en-v1.5 (768-dim)
- Strict bounds & entity validation               - Cosine similarity on normalized vectors
- States: OBSERVED, CALCULATED                    - Metadata sidecar (index_meta.json)
- Explicit 2026 PARTIAL guard                     - Deduplication & Authority rerank
        |                                                 |
        +------------------------+------------------------+
                                 |
                                 v
                          EVIDENCE FUSION
                    (scripts/hybrid_retriever.py)
  - Provenance & Citation Verification
  - Missing-Data State Preservation (ZERO_RAINFALL vs ZERO_EVENTS vs NO_DATA)
  - Standardized JSON Output Contract
                                 |
                                 v
                       STANDARDIZED RETRIEVAL RESULT
```

---

## 2. Vector Store Architecture: Option A Selection

### Architectural Decision
FAISS itself is a high-performance linear algebra library for nearest neighbor search and does not provide native relational metadata filtering. 
We selected **Option A**:
1. **FAISS `IndexFlatIP`** maintains the dense 768-dimensional float32 vector space, executing inner-product search (equivalent to cosine similarity on L2-normalized vectors).
2. **Metadata Sidecar (`index_meta.json`)** maintains a zero-overhead, 1-to-1 indexed array of metadata records corresponding exactly to vector IDs `0` through `N-1`.
3. **Retrieval Pipeline**:
   - Query is encoded via `BAAI/bge-base-en-v1.5`.
   - FAISS searches the index for candidate pool ($k \times 8$).
   - Metadata sidecar evaluates explicit filters: `district`, `year`, `event_type`, `parameter`, and `authority_level`.
   - Deduplication filters near-identical passages based on text fingerprints and limits same-document page clustering.
   - Authority reranking applies a calibrated boost to government and scientific sources.
   - The top-$k$ validated candidates are returned.

### Rationale
- **Zero External Dependencies**: Eliminates the overhead, networking, and instability of separate client-server vector databases.
- **Idempotency**: Chunks have deterministic identifiers (`chunk_id = CHK_{doc_id}_P{page}_{idx}`). Rebuilding the vector store always produces the exact same vector sequence.
- **Deterministic Filtering**: Guarantees 100% precision on categorical metadata without relying on approximate vector filtering.

---

## 3. Embedding Model Specifications

| Property | Value | Notes |
| :--- | :--- | :--- |
| **Model Name** | `BAAI/bge-base-en-v1.5` | Preferred local embedding model |
| **HuggingFace ID** | `BAAI/bge-base-en-v1.5` | Executed locally via PyTorch |
| **Embedding Dimension** | `768` | Fixed dense vector length |
| **Normalization** | `True` (L2 normalized) | $\|\mathbf{v}\|_2 = 1.0$ |
| **Similarity Metric** | `Cosine Similarity` | Computed via FAISS `IndexFlatIP` |
| **Query Instruction** | `Represent this sentence for searching relevant passages: ` | Recommended BGE query prompt |
| **Passage Instruction** | None (Raw chunk text) | Direct chunk embedding |
| **Target Scope** | `document_chunks` ONLY | Never embeds 328k rainfall observations |

---

## 4. Controlled SQL Engine & Safety Guarantees

Direct user-to-SQL generation is **strictly prohibited** to prevent SQL injection, schema corruption, and mathematical hallucinations.
All structured queries are handled through typed, parameterized Python functions in `scripts/structured_retriever.py`:

1. `get_max_rainfall(district, year, start_date, end_date)`
2. `get_rainfall_by_date(district, date)`
3. `get_rainfall_statistics(district, year, start_date, end_date)`
4. `get_events_by_year(year, district, event_type)`
5. `get_events_by_type(event_type, district, start_year, end_year)`
6. `get_cloudburst_summary(district)`
7. `get_event_by_id(event_id)`
8. `get_telemetry_2026(district)`

### Validation Parameters:
- **Districts**: Strictly validated against `{"Kangra", "Mandi", "Shimla", "Kullu"}`. Out-of-scope districts return `NO_SUPPORTED_EVIDENCE`.
- **Temporal Bounds**: Allowed years: `2011` through `2026`. Future years (e.g. 2027) return `NO_SUPPORTED_EVIDENCE`.
- **2026 Guard**: Any annual calculation requested for 2026 returns `INSUFFICIENT_FOR_FULL_YEAR`.

---

## 5. Source Authority Hierarchy & Reranking

When multiple documents provide evidence for a query, authority level is strictly preserved and influences reranking:

1. **Rank 1: Official Government Publications (`GOVERNMENT_OFFICIAL`)**
   - HPSDMA (Disaster Management Cell), IMD Shimla, Ministry of Home Affairs, NDRF.
   - Rerank Bonus: `+0.030`
2. **Rank 2: Peer-Reviewed Scientific Literature (`SCIENTIFIC_LITERATURE`)**
   - Geological Survey of India (GSI), Wadia Institute of Himalayan Geology.
   - Rerank Bonus: `+0.015`
3. **Rank 3: Reputable Secondary Reports (`REPUTABLE_SECONDARY`)**
   - Multi-agency assessments, technical working papers.
   - Rerank Bonus: `+0.000`

### Scoring Formula:
$$\text{Score}_{\text{final}} = \text{Sim}_{\text{cosine}}(\mathbf{q}, \mathbf{d}) + \text{Bonus}_{\text{authority}} - \text{Penalty}_{\text{diversity}}$$

*Note*: The authority bonus is intentionally small (0.015–0.030) so that high-authority evidence is preferred among closely scoring passages without promoting irrelevant passages over genuinely relevant evidence.

---

## 6. Standard Evidence Contract

Every retrieval operation outputs a standard JSON structure adhering to this contract:

```json
{
  "query": "Was the July 2023 Kullu disaster associated with extreme rainfall, and what damage occurred?",
  "route": "HYBRID",
  "routing_confidence": 0.90,
  "intent": "HAZARD_RAINFALL_CORRELATION",
  "status": "OK",
  "detected_entities": {
    "district": "Kullu",
    "year": 2023,
    "event_type": "Flash Flood",
    "parameter": "Rainfall"
  },
  "structured_evidence": [
    {
      "evidence_id": "EVID_RAIN_STAT_Kullu_2023",
      "evidence_type": "CALCULATED",
      "source_id": "SRC_IMD_GRIDDED_025",
      "district": "Kullu",
      "year": 2023,
      "absolute_peak_cell_mm": 218.4,
      "heavy_rain_days": 14
    }
  ],
  "document_evidence": [
    {
      "chunk_id": "CHK_DOC_HPSDMA_PDNA_2023_P019_01",
      "evidence_type": "REPORTED",
      "score": 0.842,
      "rerank_score": 0.872,
      "source_id": "SRC_HPSDMA_PDNA_2023",
      "document_title": "Post Disaster Needs Assessment (PDNA) Monsoon 2023",
      "page_number": 19,
      "authority_level": "GOVERNMENT_OFFICIAL",
      "text": "The Beas basin experienced unprecedented cloudbursts and flash floods between July 7 and July 11, 2023, washing away bridges and roads..."
    }
  ],
  "sources": [
    {
      "source_id": "SRC_IMD_GRIDDED_025",
      "source_name": "IMD Pune 0.25° x 0.25° Daily Gridded Rainfall Matrix",
      "organization": "India Meteorological Department, Climate Research and Services (CRS) Pune"
    },
    {
      "source_id": "SRC_HPSDMA_PDNA_2023",
      "source_name": "Report on Post Disaster Need Assessment (PDNA) HP Monsoon-2023",
      "organization": "Himachal Pradesh State Disaster Management Authority (HPSDMA)"
    }
  ],
  "warnings": []
}
```

---

## 7. Strict Milestone Boundary
This retrieval engine strictly produces provenanced, validated evidence structures. It **does not generate natural-language answers**, connect to external chatbots, or execute speculative predictive models.
