# Milestone 4 — Phase 4.0: Application Architecture Audit & Implementation Plan

**Project:** Himachal Pradesh Extreme Weather RAG System (2011–2026)  
**Execution Date:** 2026-09-08  
**Component:** Milestone 4 — User-Facing Application Layer (Phase 4.0 Audit)  
**Status:** `AUDIT_COMPLETE — READY_FOR_PHASE_4.1`  

---

## 1. Executive Summary & Verification

Milestones 1, 2A, 2B, and 3 are officially **CLOSED** and verified. The backend consists of an immutable data foundation (2011–2026), an authoritative SQLite structured knowledge base, an 812-chunk semantic vector store with BAAI/bge-base-en-v1.5 embeddings, a 9-priority hybrid router, an immutable Evidence Pack normalizer, a grounded Hugging Face LLM client (`Qwen/Qwen2.5-7B-Instruct-1M` routed to `featherless-ai`), and a strict deterministic validator.

### Strict Immutability & Safety Verification:
* **Milestone 1 Data Foundation:** Verified 100% immutable (All 8 master datasets SHA-256 matched via `scripts/validate_retrieval.py`).
* **Milestone 2A Knowledge Base:** SQLite database (`data/master/hp_extreme_weather.db`) and 812 chunks untouched.
* **Milestone 2B Retrieval Engine:** Frozen FAISS index (`IndexFlatIP`), positive geographic taxonomy, and routing heuristics untouched.
* **Milestone 3 Generation & Validation:** Grounding Contract (17 rules), single-canonical enum requirement (`MIXED`), and deterministic validator untouched.
* **Hugging Face API Calls:** **Zero (0) live API calls** were executed during this architecture audit phase.
* **Secret Hygiene:** Verified zero tokens exposed or logged; `.env` remains gitignored.

---

## 2. Current Backend Architecture

The existing production pipeline strictly decouples retrieval from generation:

```
USER NATURAL LANGUAGE QUERY
             │
             ▼
[STAGE A: ENTRY POINT]
             │
             ▼
[STAGE B: QUERY ANALYZER & ROUTER] ── scripts/hybrid_retriever.py
   ├── Priority 1: Unsupported Parameter (Fail Closed -> NO_SUPPORTED_EVIDENCE)
   ├── Priority 2: Explicit Unsupported Geography (Fail Closed -> NO_SUPPORTED_EVIDENCE)
   ├── Priority 3: Temporal Out of Bounds (Fail Closed -> NO_SUPPORTED_EVIDENCE)
   ├── Priority 4-7: Structured / Hybrid / Landslide Narrative Scope
   └── Priority 8-9: Parameterized SQL & FAISS Semantic Vector Retrieval
             │
             ▼
[STAGE C: RETRIEVAL ENGINES]
   ├── SQLite Parameterized SQL (scripts/structured_retriever.py)
   └── FAISS Semantic Search + Metadata Reranking (scripts/semantic_retriever.py)
             │
             ▼
[STAGE D: STRICT EVIDENCE PACK] ── scripts/evidence_pack.py
   ├── Normalizes SQLite records & FAISS document chunks into deterministic items
   ├── Tags evidence types: OBSERVED, CALCULATED, REPORTED
   └── Preserves 100% source, document, chunk, page, and calculation provenance
             │
             ▼
[STAGE E: GROUNDED GENERATION] ── scripts/answer_generator.py & scripts/llm_client.py
   ├── If NEGATIVE_REJECTED: Deterministic router refusal WITHOUT an LLM call
   ├── If SUPPORTED: Injects Evidence Pack into 17-rule prompt
   └── Calls Hugging Face Serverless (Qwen/Qwen2.5-7B-Instruct-1M via featherless-ai)
             │
             ▼
[STAGE F & G: STRICT ANSWER VALIDATION] ── scripts/answer_validator.py
   ├── Citation Integrity: 100% cited chunks must exist in Evidence Pack
   ├── Numerical Preservation: Authoritative SQL numbers must match exactly
   ├── Temporal Check: 2026 partial-year status preserved
   └── Schema Check: Exactly one canonical enum (including MIXED for hybrid)
             │
             ▼
[STAGE H: COMPOSITE FINAL RESPONSE]
Grounded Answer + Evidence Classification + Citations + Evidence Pack + Audit Details
```

---

## 3. Existing Reusable Backend Components

Every phase of the application will strictly consume the following existing Python modules without duplicating or modifying them:

| Pipeline Stage | Module Path | Primary Functions / Classes | Inputs | Outputs |
| :--- | :--- | :--- | :--- | :--- |
| **Routing** | [`scripts/hybrid_retriever.py`](file:///c:/Users/rahul/Desktop/RAG/HP_Extreme_Weather_RAG/scripts/hybrid_retriever.py) | `retrieve(query, top_k_docs=5)`<br>`extract_entities(query)`<br>`classify_query(query, entities)` | `query: str` | `Dict[str, Any]` (route, intent, detected_entities, structured_evidence, document_evidence, sources, warnings) |
| **Structured SQL** | [`scripts/structured_retriever.py`](file:///c:/Users/rahul/Desktop/RAG/HP_Extreme_Weather_RAG/scripts/structured_retriever.py) | `get_max_rainfall()`<br>`get_rainfall_by_date()`<br>`get_rainfall_statistics()`<br>`get_events_by_year()`<br>`get_telemetry_2026()` | District, Year, Date | `Dict[str, Any]` (authoritative SQL metrics, calculation methods, source IDs) |
| **Semantic FAISS** | [`scripts/semantic_retriever.py`](file:///c:/Users/rahul/Desktop/RAG/HP_Extreme_Weather_RAG/scripts/semantic_retriever.py) | `semantic_search(query, top_k=5, district=None, year=None)` | `query: str` | `Dict[str, Any]` (top-$k$ document chunks with document-scope boost and title demotion) |
| **Evidence Pack** | [`scripts/evidence_pack.py`](file:///c:/Users/rahul/Desktop/RAG/HP_Extreme_Weather_RAG/scripts/evidence_pack.py) | `build_evidence_pack(raw_retrieval)` | Output from `retrieve()` | `Dict[str, Any]` (strictly normalized `evidence_items`, tagged `OBSERVED`, `CALCULATED`, `REPORTED`) |
| **LLM Client** | [`scripts/llm_client.py`](file:///c:/Users/rahul/Desktop/RAG/HP_Extreme_Weather_RAG/scripts/llm_client.py) | `get_hf_config()`<br>`call_hf_inference(messages, ...)` | `messages: List[Dict]` | `Dict[str, Any]` (status, content, model, provider, latency_ms) |
| **Answer Generation** | [`scripts/answer_generator.py`](file:///c:/Users/rahul/Desktop/RAG/HP_Extreme_Weather_RAG/scripts/answer_generator.py) | `generate_answer(evidence_pack)`<br>`generate_deterministic_negative_answer(evidence_pack)` | Normalized Evidence Pack | `Dict[str, Any]` (answer, status, evidence_type, confidence, citations, metadata) |
| **Answer Validator** | [`scripts/answer_validator.py`](file:///c:/Users/rahul/Desktop/RAG/HP_Extreme_Weather_RAG/scripts/answer_validator.py) | `validate_answer(answer_obj, evidence_pack)` | Generated answer & Evidence Pack | `Dict[str, Any]` (is_valid, numerical_preservation_pass, citation_integrity_pct, validation_errors) |

---

## 4. Exact Query Execution Path

For any incoming user query $Q$, the execution path through the Python runtime is completely deterministic:

```python
# 1. Routing & Multi-Engine Retrieval
raw_retrieval = scripts.hybrid_retriever.retrieve(query=Q, top_k_docs=5)

# 2. Strict Evidence Pack Normalization
evidence_pack = scripts.evidence_pack.build_evidence_pack(raw_retrieval)

# 3. Answer Generation (Zero LLM calls for rejections)
if evidence_pack.get("route") == "NEGATIVE_REJECTED" or evidence_pack.get("status") == "NO_SUPPORTED_EVIDENCE":
    answer_obj = scripts.answer_generator.generate_deterministic_negative_answer(evidence_pack)
else:
    answer_obj = scripts.answer_generator.generate_answer(evidence_pack)

# 4. Strict Deterministic Answer Validation
validation_report = scripts.answer_validator.validate_answer(answer_obj, evidence_pack)

# 5. Composite Presentation Assembly
final_response = assemble_response(Q, evidence_pack, answer_obj, validation_report)
```

---

## 5. Proposed Application Architecture & UI/Backend Boundary

To maintain complete scientific integrity and prevent code clutter, the UI layer will be decoupled from the core pipeline via a single facade class:

```
┌─────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                     │
│               app/main.py  (Streamlit Local UI)             │
│   ├── Query Input & Pre-Populated Category Examples         │
│   ├── Answer Card & Evidence-Type Badges                    │
│   ├── Interactive Citations (Document / Structured)         │
│   ├── Collapsible Evidence Pack & Provenance Inspector      │
│   └── 2026 Telemetry / Out-of-Scope Warning Banners        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Calls execute_query(query_text)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 APPLICATION ORCHESTRATOR                    │
│                    app/rag_engine.py                        │
│   ├── Encapsulates stages 1 to 5 cleanly                    │
│   ├── Sanitizes query inputs                                │
│   ├── Computes performance latencies                        │
│   └── Logs execution metadata without exposing tokens       │
└──────────────────────────────┬──────────────────────────────┘
                               │ Consumes existing backend
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               EXISTING SCIENTIFIC BACKEND (FROZEN)          │
│  scripts.hybrid_retriever  │  scripts.evidence_pack         │
│  scripts.llm_client        │  scripts.answer_generator      │
│  scripts.answer_validator  │  data/master/hp_extreme_weather │
└─────────────────────────────────────────────────────────────┘
```

### Strict Boundary Rules:
1. **The UI NEVER queries SQLite or FAISS directly:** All database access is channeled through `hybrid_retriever.py`.
2. **The UI NEVER calls the LLM directly:** Generation is handled strictly by `answer_generator.py` consuming an immutable Evidence Pack.
3. **The UI NEVER displays unvalidated text:** Every response must pass through `answer_validator.py`.

---

## 6. Response Object Design

The facade (`app/rag_engine.py`) returns a typed composite dictionary conforming to the following structure:

```json
{
  "query": "What was the maximum district-level rainfall recorded in Kangra during 2023, and on what date?",
  "execution_timestamp": "2026-09-08T12:21:40.123456Z",
  "total_latency_ms": 7892.1,
  
  "answer": {
    "text": "The maximum district-level rainfall recorded in Kangra during 2023 was 246.81 mm, which occurred on 2023-08-14.",
    "status": "OK",
    "evidence_type": "CALCULATED",
    "confidence": "HIGH"
  },
  
  "citations": [
    {
      "evidence_id": "EVID_MAX_RAIN_Kangra_2023-08-14",
      "source_id": "SRC_IMD_GRIDDED_025",
      "source_name": "IMD Pune 0.25° x 0.25° Daily Gridded Rainfall Matrix",
      "district": "Kangra",
      "year": 2023,
      "chunk_id": null,
      "page": null
    }
  ],
  
  "evidence_pack": {
    "route": "STRUCTURED",
    "intent": "MAX_RAINFALL",
    "detected_entities": {"district": "Kangra", "year": 2023, "parameter_status": "RAINFALL"},
    "evidence_count": 1,
    "warnings": []
  },
  
  "validation": {
    "is_valid": true,
    "citation_integrity_pct": 100.0,
    "numerical_preservation_pass": true,
    "rejection_preserved": true,
    "validation_errors": [],
    "warnings": []
  },
  
  "engine_metadata": {
    "model": "Qwen/Qwen2.5-7B-Instruct-1M",
    "provider": "featherless-ai",
    "client_status": "OK"
  }
}
```

---

## 7. Error-State & Rejection Design

The application will cleanly handle all system and domain error states without exposing raw stack traces:

| Status Code | Trigger Condition | UI Presentation Pattern | LLM Call Made? |
| :--- | :--- | :--- | :---: |
| **`NO_SUPPORTED_EVIDENCE`** | Unsupported geography (e.g. Pune), unsupported parameter (e.g. wind speed), or out-of-bounds year. | **Amber Info Card:** Displays clear refusal explaining authorized project scope (Kangra, Mandi, Shimla, Kullu; 2011–2026; Rainfall, Cloudbursts, Flash Floods). | **NO (Zero)** |
| **`GENERATION_UNAVAILABLE`** | Upstream provider cold-start timeout, network drop, or rate limit. | **Yellow Warning Card:** Informs user that language synthesis is temporarily unavailable. **Crucial:** Displays the retrieved Evidence Pack and SQL/passages directly so the user still gets the grounded facts. | **YES (Attempted)** |
| **`INSUFFICIENT_FOR_FULL_YEAR`** | Queries requesting annual aggregates for incomplete years (e.g., 2026). | **Warning Badge + Telemetry Banner:** Clarifies that records represent partial/interim observations only. | **YES / Handled** |
| **`ZERO_RAINFALL`** | Gauge/grid recording 0.0 mm on a verified date. | **Neutral Info Badge:** Clarifies that zero rainfall was a valid observation, not missing data. | **YES** |
| **`ZERO_DOCUMENTED_EVENTS`** | Disaster registry shows 0 events for specified criteria. | **Neutral Info Badge:** Clarifies official sources document 0 events. | **YES** |

---

## 8. Citation Presentation Design

Citations will be presented with clear distinction between structured data and narrative publications:

### A. Document Passages:
* **Visual Card:** Displays Document Title (e.g., *HPSDMA Post-Disaster Needs Assessment 2023*), Page Number (`Page 19`), and Chunk ID (`CHK_DOC_HPSDMA_PDNA_2023_P019_02`).
* **Passage Snippet:** Collapsible viewer revealing the exact grounded text excerpt with matched keywords highlighted.

### B. Structured Database Metrics:
* **Visual Card:** Displays Official Source (e.g., *IMD Pune 0.25° Gridded Matrix*), Table Name (`structured_tables`), and Calculation Provenance (`Spatial grid average across district boundary`).
* **Authoritative Values:** Exact numbers matching SQL metrics (e.g., `246.81 mm`).

---

## 9. 2026 Data Presentation Policy

The system contains partial/interim telemetry for 2026 through September 2026. The UI must strictly follow these constraints:
1. **Prominent Banner:** Any query mentioning 2026 will render a visible amber notice:
   > ⚠️ **Interim Telemetry Notice:** Data for 2026 represents partial observations through September 2026. It must NOT be interpreted or cited as a complete annual record.
2. **Comparison Guards:** Annual comparisons between 2026 and prior years (2011–2025) will explicitly display an `INCOMPLETE_COMPARISON` disclaimer.

---

## 10. Evidence-Type Presentation (Badges & Color Coding)

The application will prominently tag the answer with canonical color-coded badges to prevent scientific misunderstanding:

* <span style="background-color:#059669; color:white; padding:2px 8px; border-radius:4px; font-weight:bold;">OBSERVED</span> — Direct physical gauge observation (e.g., IMD daily station reading).
* <span style="background-color:#0284c7; color:white; padding:2px 8px; border-radius:4px; font-weight:bold;">CALCULATED</span> — Mathematical aggregate (e.g., spatial grid mean, multi-day total). Tooltip: *"Spatial aggregation or statistical mean across grid cells; not a single point gauge."*
* <span style="background-color:#d97706; color:white; padding:2px 8px; border-radius:4px; font-weight:bold;">REPORTED</span> — Government report, disaster memorandum, or scientific study (e.g., PDNA loss assessment).
* <span style="background-color:#7c3aed; color:white; padding:2px 8px; border-radius:4px; font-weight:bold;">MIXED</span> — Hybrid fusion combining structured quantitative evidence with documentary impacts.
* <span style="background-color:#6b7280; color:white; padding:2px 8px; border-radius:4px; font-weight:bold;">INSUFFICIENT</span> — Retrieved evidence is inadequate to answer conclusively.

---

## 11. Security & Secrets Handling

1. **Token Invariant:** `HF_TOKEN` is loaded strictly via environment / `.env`.
2. **Zero Display Invariant:** Neither the full token nor the masked token will ever appear in the UI DOM, source attributes, tooltips, or error messages.
3. **Provider Transparency:** The UI will display engine status cleanly:
   * **Active Model:** `Qwen/Qwen2.5-7B-Instruct-1M`
   * **Inference Routing:** `featherless-ai (Hugging Face Serverless)`
   * **Credentials:** *Authenticated (Hidden)*

---

## 12. Logging & Local Audit Trail Requirements

`app/rag_engine.py` will log each query execution to `evaluation/app_query_logs.jsonl` containing:
* Query timestamp (ISO-8601 UTC)
* User query string
* Route selected (`STRUCTURED`, `DOCUMENT`, `HYBRID`, `NEGATIVE_REJECTED`)
* Retrieval status & item count
* LLM latency in milliseconds
* Validation outcome (`PASSED` or `FAILED`)
* **Never logs:** Secrets, API tokens, or user environment variables.

---

## 13. Recommended UI Technology

### Analysis of Available Local Frameworks:
1. **Streamlit (`streamlit`):**
   * **Availability:** **Installed and verified** in the active environment (`streamlit>=1.40.0`).
   * **Evaluation:** Highly recommended. Native Python implementation, excellent support for interactive dataframes, JSON tree inspectors, markdown rendering, collapsible accordions for evidence, and reactive tabs. Runs locally via `streamlit run app/main.py`.
   * **Overhead:** Zero build steps, zero HTML/CSS/JS bundling.
2. **Tkinter Desktop GUI (`tkinter`):**
   * **Evaluation:** Available in Python standard library, but poorly suited for complex markdown, collapsible passage cards, and citation badges.
3. **FastAPI (`fastapi`):**
   * **Evaluation:** Installed, but requires separate frontend implementation (HTML/JS), creating unnecessary complexity.

### Decision:
Implement the user-facing interface using **Streamlit** as a lightweight, clean, local application running in `app/main.py`.

---

## 14. Files Proposed for Milestone 4 (Phase 4.1)

Only files within `app/` and relevant evaluation logs will be created:

1. **`app/rag_engine.py`** — Orchestration engine wrapping `scripts/hybrid_retriever.py`, `scripts/evidence_pack.py`, `scripts/answer_generator.py`, and `scripts/answer_validator.py`.
2. **`app/components.py`** — UI rendering utilities (citation cards, evidence-type badges, 2026 warning banners, latency timers).
3. **`app/main.py`** — Streamlit local application entry point.
4. **`app/examples.py`** — Curated pre-populated example queries across all 6 core query categories.

---

## 15. Protected Files (Strictly Immutable)

The following files are authoritative and must **NOT** be modified under any circumstances during Milestone 4:

* `data/master/*` (All 8 Milestone 1 processed CSVs, SQLite `hp_extreme_weather.db`, `milestone1_checksums.json`).
* `data/knowledge_base/vector_store/*` (`index.faiss`, `index_meta.json`, `embedding_manifest.json`).
* `scripts/hybrid_retriever.py`
* `scripts/structured_retriever.py`
* `scripts/semantic_retriever.py`
* `scripts/evidence_pack.py`
* `scripts/llm_client.py`
* `scripts/answer_generator.py`
* `scripts/answer_validator.py`
* `evaluation/golden_questions.json`

---

## 16. Risks and Mitigations

| Identified Risk | Severity | Mitigation Strategy |
| :--- | :---: | :--- |
| **Upstream Provider Cold-Start Latency** | Low / Medium | Streamlit reactive status spinner with elapsed timer (`st.spinner("Retrieving evidence & querying Featherless AI...")`). |
| **Transient Provider Rate Limiting (429)** | Medium | `app/rag_engine.py` passes through `GENERATION_UNAVAILABLE` fail-safe; UI renders the authoritative Evidence Pack directly to the user so information access is never blocked. |
| **User Misinterprets CALCULATED as Station Observation** | High | Visual color-coded badge (`CALCULATED`) paired with an explanatory caption detailing grid spatial averaging. |
| **2026 Extrapolation Confusion** | High | Automatic conditional alert banner rendered whenever 2026 is detected in entities. |

---

## 17. Phase 4 Implementation Plan

```
[PHASE 4.0: ARCHITECTURE AUDIT]  <--- COMPLETED HERE
             │
             ▼
[PHASE 4.1: ORCHESTRATION ENGINE (app/rag_engine.py)]
   ├── Implement single-call execute_query() facade
   ├── Connect hybrid_retriever -> evidence_pack -> answer_generator -> answer_validator
   └── Verify execution locally via headless script
             │
             ▼
[PHASE 4.2: UI PRESENTATION LAYER (app/main.py & app/components.py)]
   ├── Implement Streamlit interface layout
   ├── Render category tabs & pre-populated example buttons
   ├── Render Evidence Badges (OBSERVED, CALCULATED, REPORTED, MIXED)
   ├── Render Collapsible Evidence Pack & Provenance Inspector
   └── Render Citation Cards & 2026 Warning Banners
             │
             ▼
[PHASE 4.3: END-TO-END ACCEPTANCE VALIDATION]
   ├── Test 1: Exact rainfall query (Kangra 2023 max rain)
   ├── Test 2: Document narrative query (PDNA recovery principles)
   ├── Test 3: Hybrid query (Kullu 2023 rainfall + impacts)
   ├── Test 4: Negative unsupported geography (Pune refusal)
   ├── Test 5: Negative unsupported parameter (Wind speed refusal)
   └── Test 6: 2026 partial-year status query
             │
             ▼
[PHASE 4.4: FINAL APPLICATION WALKTHROUGH & DOCUMENTATION]
   └── Create reports/milestone4_application_validation.md
```

---

## 18. Acceptance Criteria for Phase 4.1 UI Implementation

1. **Routing Fidelity:** Supported queries route properly; unsupported queries display deterministic refusals without an LLM call.
2. **Badging Fidelity:** Exactly reflects `OBSERVED`, `CALCULATED`, `REPORTED`, `MIXED`, or `INSUFFICIENT`.
3. **Citation Completeness:** Every factual claim cites valid Evidence IDs from the Evidence Pack with zero hallucinated URLs.
4. **2026 Safety:** Prominently flags 2026 as partial/interim data.
5. **Backend Immutability:** All 10 protected core scripts and datasets remain 100% byte-for-byte identical.
6. **No-Cost / Security Invariant:** Never requires third-party keys, never exposes tokens, operates within free Hugging Face routing allowance.

---

```text
===========================================================================
AUDIT COMPLETE: READY FOR PHASE 4.1 IMPLEMENTATION
===========================================================================
```
