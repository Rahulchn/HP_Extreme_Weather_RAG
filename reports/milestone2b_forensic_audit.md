# Milestone 2B — Forensic Audit Report

**Audit Date:** 2026-09-08  
**Audit Target:** Himachal Pradesh Extreme Weather RAG System (Milestone 2B Retrieval Implementation)  
**Auditor:** DeepMind Antigravity Advanced Agentic Coding  
**Status Prior to Audit:** `READY_FOR_MILESTONE_3`  
**Audit Type:** Forensic Implementation Audit (Non-destructive, zero code modification)

---

## Executive Summary

A comprehensive, independent forensic audit was conducted across the generated files, SQLite database (`hp_extreme_weather.db`), FAISS vector store (`index.faiss` and `index_meta.json`), embedding manifest (`embedding_manifest.json`), evaluation benchmarks (`golden_questions.json`, `retrieval_results.json`), and the retrieval engines (`semantic_retriever.py`, `structured_retriever.py`, `hybrid_retriever.py`, `validate_retrieval.py`).

While the underlying datasets, FAISS vector embeddings, SQLite parameterized access, provenance metadata, and Milestone 1 immutable baselines passed all technical integrity checks with high fidelity, the forensic audit revealed **critical architectural vulnerabilities in query routing and negative query rejection** that invalidate the claim of 100% retrieval reliability:
1. **Negative Query Fragility & Silent Hallucinations:** The negative rejection guard in `scripts/hybrid_retriever.py` relies exclusively on a hardcoded 10-word blacklist of disallowed districts and a 10-word blacklist of unsupported phenomena. When tested adversarially with an out-of-scope district not in the hardcoded blacklist (e.g., *"What was the maximum rainfall in Pune in 2023?"*), the router failed to reject the query, set `district = None`, and executed a global SQLite query that returned Kangra maximum rainfall as the authoritative answer for Pune.
2. **Unsupported Parameter Routing Collisions:** The router defaults to SQL rainfall lookups or document searches on unsupported parameters: asking for *"wind speed in Shimla on 2023-07-09"* returned rainfall figures; asking for *"solar radiation in Kangra"* returned flood disaster chapters; asking for *"avalanche accidents in Kullu"* returned cloudburst events.
3. **Hit@k Metric Conflation:** The reported 100% Hit@1, Hit@3, and Hit@5 metrics conflated structured SQL queries with semantic document retrieval (8 of the 17 evaluable queries were pure SQL queries scored as "Hit@1" because the hardcoded database source ID matched the ground truth source ID), evaluated semantic relevance only at coarse document/source granularity rather than chunk granularity, and tested only 25 hand-crafted benchmark queries.

Consequently, the audit issues a verdict of **`NOT_READY — RETRIEVAL_REPAIR_REQUIRED`**.

---

## 1. Golden Evaluation Integrity

### Question-by-Question Forensic Evaluation Matrix

The 25 golden questions from `evaluation/golden_questions.json` and their corresponding execution traces in `evaluation/retrieval_results.json` were audited:

| QID | Question Text | Expected Route | Expected Structured Operation OR Expected Relevant Source/Doc/Chunk IDs | Actual Retrieved IDs | Relevance Criterion | Evaluation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GQ_01** | What was the maximum rainfall in Kangra in 2023? | `STRUCTURED` | `get_max_rainfall`; Sources: `SRC_IMD_GRIDDED_025`, `SRC_IMD_SHIMLA_DISTRICT_MONSOON` | `EVID_MAX_RAIN_Kangra_2023-08-14`; Source: `SRC_IMD_GRIDDED_025` | Source ID in `expected_source_ids` | PASS (Structured) |
| **GQ_02** | How many documented flash floods occurred in Kullu between 2011 and 2025? | `STRUCTURED` | `get_events_by_type`; Sources: `SRC_HPSDMA_LOSS_MEMORANDUMS`, `SRC_HPSDMA_HISTORICAL_LOSS_2007_2015` | `EVID_TYPE_Flash Flood_Kullu`; Source: `SRC_HPSDMA_LOSS_MEMORANDUMS` | Source ID in `expected_source_ids` | PASS (Structured) |
| **GQ_03** | What happened during the Boh/Dharamshala disaster in July 2021? | `DOCUMENT` | `semantic_search`; Docs: `DOC_GSI_BOH_2021`, `DOC_HPSDMA_MEMO_2021`; Sources: `SRC_GSI_WADIA_EVENT_STUDIES`, `SRC_HPSDMA_LOSS_MEMORANDUMS` | Chunks from `DOC_GSI_BOH_2021`; Source: `SRC_GSI_WADIA_EVENT_STUDIES` | Doc ID in `expected_document_ids` | PASS (Document) |
| **GQ_04** | Which district had the most documented cloudburst events? | `STRUCTURED` | `get_cloudburst_summary`; Sources: `SRC_HPSDMA_LOSS_MEMORANDUMS`, `SRC_HPSDMA_10YR_LOSSES_2016_2025` | `EVID_CLOUDBURST_SUMMARY`; Source: `SRC_HPSDMA_LOSS_MEMORANDUMS` | Source ID in `expected_source_ids` | PASS (Structured) |
| **GQ_05** | Was the July 2023 Kullu disaster associated with extreme rainfall? | `HYBRID` | `hybrid_search`; Docs: `DOC_HPSDMA_PDNA_2023`, `DOC_HPSDMA_MEMO_2023`; Sources: `SRC_HPSDMA_PDNA_2023`, `SRC_IMD_GRIDDED_025` | `EVID_RAIN_STAT_Kullu_2023`, `EVID_EVENTS_2023_Kullu`; Docs: `DOC_HPSDMA_MEMO_2023`, `DOC_HPSDMA_PDNA_2023` | Doc ID in `expected_document_ids` AND Source in `expected_source_ids` | PASS (Hybrid) |
| **GQ_06** | What does HPSDMA report about infrastructure damage during the 2023 monsoon? | `DOCUMENT` | `semantic_search`; Docs: `DOC_HPSDMA_PDNA_2023`, `DOC_HPSDMA_MEMO_2023`; Sources: `SRC_HPSDMA_PDNA_2023`, `SRC_HPSDMA_LOSS_MEMORANDUMS` | Chunks from `DOC_HPSDMA_PDNA_2023`, `DOC_HPSDMA_MEMO_2023` | Doc ID in `expected_document_ids` | PASS (Document) |
| **GQ_07** | What information is currently available for 2026? | `HYBRID` | `hybrid_search`; Sources: `SRC_IMD_SHIMLA_TELEMETRY_2026`; State: `PARTIAL` | `EVID_TELEMETRY_2026`; Docs: `DOC_IMD_TELEMETRY_2026`, `DOC_IMD_CHIEF_RAIN_2026` | Source ID in `expected_source_ids` | PASS (Hybrid) |
| **GQ_08** | What was the rainfall in Shimla on 2023-07-09? | `STRUCTURED` | `get_rainfall_by_date`; Sources: `SRC_IMD_GRIDDED_025` | `EVID_RAIN_OBS_Shimla_2023-07-09`; Source: `SRC_IMD_GRIDDED_025` | Source ID in `expected_source_ids` | PASS (Structured) |
| **GQ_09** | What was the average annual rainfall in Mandi between 2011 and 2025? | `STRUCTURED` | `get_rainfall_statistics`; Sources: `SRC_IMD_GRIDDED_025` | `EVID_RAIN_STAT_Mandi_RANGE`; Source: `SRC_IMD_GRIDDED_025` | Source ID in `expected_source_ids` | PASS (Structured) |
| **GQ_10** | List documented cloudburst events in Mandi district in 2023. | `STRUCTURED` | `get_events_by_year`; Sources: `SRC_HPSDMA_LOSS_MEMORANDUMS`, `SRC_HPSDMA_PDNA_2023` | `EVID_EVENTS_2023_Mandi`; Source: `SRC_HPSDMA_LOSS_MEMORANDUMS` | Source ID in `expected_source_ids` | PASS (Structured) |
| **GQ_11** | What geological factors triggered the 2017 Kotrupi Mandi disaster according to GSI? | `DOCUMENT` | `semantic_search`; Docs: `DOC_GSI_KOTRUPI_2017`; Sources: `SRC_GSI_WADIA_EVENT_STUDIES` | Chunks from `DOC_GSI_KOTRUPI_2017`; Source: `SRC_GSI_WADIA_EVENT_STUDIES` | Doc ID in `expected_document_ids` | PASS (Document) |
| **GQ_12** | What was the annual rainfall in Kangra in 2026? | `STRUCTURED` | `get_rainfall_statistics`; State: `INSUFFICIENT_FOR_FULL_YEAR` | `EVID_INSUFFICIENT_2026_Kangra`; Status: `INSUFFICIENT_FOR_FULL_YEAR` | State matches `INSUFFICIENT_FOR_FULL_YEAR` | PASS (State) |
| **GQ_13** | How many cloudburst events were documented in Kangra in 2016? | `STRUCTURED` | `get_events_by_year`; State: `ZERO_DOCUMENTED_EVENTS` | `EVID_EVENTS_2016_Kangra`; Status: `ZERO_DOCUMENTED_EVENTS` | State matches `ZERO_DOCUMENTED_EVENTS` | PASS (State) |
| **GQ_14** | Was zero rainfall recorded anywhere in Kangra on 2011-01-02? | `STRUCTURED` | `get_rainfall_by_date`; State: `ZERO_RAINFALL` | `EVID_RAIN_OBS_Kangra_2011-01-02`; Status: `ZERO_RAINFALL` | State matches `ZERO_RAINFALL` | PASS (State) |
| **GQ_15** | What were the total casualties reported from the June 2013 Kullu flash flood disaster? | `HYBRID` | `hybrid_search`; Sources: `SRC_HPSDMA_LOSS_MEMORANDUMS` | `EVID_RAIN_STAT_Kullu_2013`, `EVID_EVENTS_2013_Kullu` | Source ID in `expected_source_ids` | PASS (Hybrid) |
| **GQ_16** | What does the 10-year disaster report indicate about total human losses in Himachal Pradesh from 2016 to 2025? | `DOCUMENT` | `semantic_search`; Docs: `DOC_HPSDMA_10YR_LOSSES`, `DOC_HPSDMA_LR3_2007_2015`; Sources: `SRC_HPSDMA_10YR_LOSSES_2016_2025`, `SRC_HPSDMA_HISTORICAL_LOSS_2007_2015` | Chunks from `DOC_HPSDMA_LR3_2007_2015`, `DOC_HPSDMA_PDNA_2023` | Doc ID in `expected_document_ids` | PASS (Document) |
| **GQ_17** | What was the highest single-day rainfall recorded in Kullu in August 2023? | `STRUCTURED` | `get_max_rainfall`; Sources: `SRC_IMD_GRIDDED_025` | `EVID_MAX_RAIN_Kullu_2023-07-09` (Calculated for August range) | Source ID in `expected_source_ids` | PASS (Structured) |
| **GQ_18** | How did the August 2023 landslides impact the road network between Mandi and Kullu? | `DOCUMENT` | `semantic_search`; Docs: `DOC_HPSDMA_PDNA_2023`, `DOC_HPSDMA_MEMO_2023`; Sources: `SRC_HPSDMA_PDNA_2023` | Chunks from `DOC_HPSDMA_PDNA_2023`, `DOC_HPSDMA_MEMO_2023` | Doc ID in `expected_document_ids` | PASS (Document) |
| **GQ_19** | What was the total rainfall in Shimla during the peak monsoon month of July 2023? | `STRUCTURED` | `get_rainfall_statistics`; Sources: `SRC_IMD_GRIDDED_025` | `EVID_RAIN_STAT_Shimla_2023`; Source: `SRC_IMD_GRIDDED_025` | Source ID in `expected_source_ids` | PASS (Structured) |
| **GQ_20** | What emergency response measures did NDRF and SDRF deploy during the July 2023 Mandi floods? | `DOCUMENT` | `semantic_search`; Docs: `DOC_HPSDMA_PDNA_2023`, `DOC_HPSDMA_MEMO_2023`; Sources: `SRC_HPSDMA_PDNA_2023`, `SRC_HPSDMA_LOSS_MEMORANDUMS` | Chunks from `DOC_HPSDMA_MEMO_2023`, `DOC_HPSDMA_MEMO_2024` | Doc ID in `expected_document_ids` | PASS (Document) |
| **GQ_21** | What was the rainfall in Jaipur district in July 2022? | `NEGATIVE_REJECTED` | State: `NO_SUPPORTED_EVIDENCE` | `NO_SUPPORTED_EVIDENCE` (Early rejection: out-of-scope district) | Status matches `NO_SUPPORTED_EVIDENCE` | PASS (Negative) |
| **GQ_22** | Describe the catastrophic tsunami that struck Mandi in August 2023. | `NEGATIVE_REJECTED` | State: `NO_SUPPORTED_EVIDENCE` | `NO_SUPPORTED_EVIDENCE` (Early rejection: fictional event) | Status matches `NO_SUPPORTED_EVIDENCE` | PASS (Negative) |
| **GQ_23** | How many flash floods occurred in Kullu in 2027? | `NEGATIVE_REJECTED` | State: `NO_SUPPORTED_EVIDENCE` | `NO_SUPPORTED_EVIDENCE` (Early rejection: future year) | Status matches `NO_SUPPORTED_EVIDENCE` | PASS (Negative) |
| **GQ_24** | What was the Richter scale earthquake reading in Kangra on 2023-07-09? | `NEGATIVE_REJECTED` | State: `NO_SUPPORTED_EVIDENCE` | `NO_SUPPORTED_EVIDENCE` (Early rejection: unsupported parameter) | Status matches `NO_SUPPORTED_EVIDENCE` | PASS (Negative) |
| **GQ_25** | What does the 1995 Bilaspur district flood report say about dam overflow? | `NEGATIVE_REJECTED` | State: `NO_SUPPORTED_EVIDENCE` | `NO_SUPPORTED_EVIDENCE` (Early rejection: out of period & district) | Status matches `NO_SUPPORTED_EVIDENCE` | PASS (Negative) |

### Independence Analysis
- **Circular Generation Check:** Inspection of `golden_questions.json` confirms that expected relevance was **not** derived from running the FAISS retriever first and copying the retrieved chunk IDs into ground truth. Instead, the golden benchmark specified domain-level institutional documents (`DOC_GSI_BOH_2021`, `DOC_HPSDMA_PDNA_2023`) and authoritative source registries (`SRC_IMD_GRIDDED_025`).
- **Verdict:** `GOLDEN_EVALUATION_INDEPENDENCE: PASS`

---

## 2. FAISS Metadata Filtering Audit

### Architecture Analysis
Inspection of `scripts/semantic_retriever.py` lines 86–177 demonstrates how filtering operates:
```python
candidate_k = min(max(top_k * 8, 40), index.ntotal)
distances, indices = index.search(query_vec, candidate_k)
...
for score, idx in zip(raw_scores, raw_indices):
    meta = metadata[idx]
    # Filter by district, year, event_type, authority_level
```
- The architecture implements **Method B**: it retrieves a wider candidate pool (`candidate_k >= 40` or `top_k * 8`) and filters candidates prior to final reranking. It does not perform Option C (searching FAISS and merely displaying metadata after the fact).

### Adversarial Filter Test Execution

Adversarial queries were executed using the live FAISS index:

1. **Adversarial District Test (Query mentions Kullu, Filter `district = Kangra`):**
   - Result: 5 chunks returned. 100% of returned chunks contained `Kangra` in their metadata `districts` list and/or text body. Zero chunks isolated solely to Kullu leaked into the results.
2. **Adversarial District Test (Query mentions Dharamshala, Filter `district = Kullu`):**
   - Result: 5 chunks returned. 100% of returned chunks were verified to have `Kullu` in their metadata `districts` list and/or text body.
3. **Adversarial Year Test (Query mentions 2023, Filter `year = 2021`):**
   - Result: Returned `NO_SUPPORTED_EVIDENCE` (0 candidates survived the 2021 temporal filter).
4. **Adversarial Event Type Test (Query mentions flash flood, Filter `event_type = Cloudburst`):**
   - Result: 5 chunks returned. All returned chunks contained `Cloudburst` in metadata event tags and chunk text.
5. **Adversarial Authority Level Test (`authority_level = GOVERNMENT_OFFICIAL`):**
   - Result: 3 chunks returned, all strictly tagged `GOVERNMENT_OFFICIAL`.
6. **Adversarial Authority Level Test (`authority_level = SCIENTIFIC_LITERATURE`):**
   - Result: 3 chunks returned, all strictly tagged `SCIENTIFIC_LITERATURE`.

- **Verdict:** `METADATA_FILTERING: PASS`

---

## 3. Authority Reranking Audit

### Formula & Weights
The scoring formula implemented in `scripts/semantic_retriever.py` is:
$$\text{rerank\_score} = \text{base\_score} + \text{auth\_bonus} - \text{diversity\_penalty}$$

Where:
- $\text{base\_score} = \text{Cosine Similarity} \in [0.30, 1.00]$ (Inner product of L2-normalized 768-dim embeddings).
- $\text{auth\_bonus}$:
  - Rank 1 (`GOVERNMENT_OFFICIAL`): $+0.03$
  - Rank 2 (`SCIENTIFIC_LITERATURE`): $+0.015$
  - Rank 3 (Secondary / Other): $+0.00$
- $\text{diversity\_penalty}$: $0.05 \times (\text{chunk\_count} - 2)$ for chunks originating from the same document page.

### Dominance Verification & Adversarial Ranking Test
Because the maximum authority bonus delta between Government and Scientific sources is only $0.03 - 0.015 = 0.015$, **semantic relevance strictly dominates the ranking**. An irrelevant government chunk ($\text{score} = 0.40 \to \text{rerank} = 0.43$) can never outrank a relevant scientific chunk ($\text{score} = 0.60 \to \text{rerank} = 0.615$).

**Adversarial Ranking Test Execution:**
Query: *"Kotrupi landslide geological initiation shear failure"*
- Rank 1: `CHK_DOC_GSI_KOTRUPI_2017_P015_01` (GSI, Scientific, Rank 2) | base: `0.7350` | rerank: `0.7500`
- Rank 2: `CHK_DOC_GSI_KOTRUPI_2017_P008_01` (GSI, Scientific, Rank 2) | base: `0.7134` | rerank: `0.7284`
- Rank 3: `CHK_DOC_GSI_KOTRUPI_2017_P014_01` (GSI, Scientific, Rank 2) | base: `0.7092` | rerank: `0.7242`
- Rank 4: `CHK_DOC_GSI_KOTRUPI_2017_P002_01` (GSI, Scientific, Rank 2) | base: `0.7033` | rerank: `0.7183`
- Rank 5: `CHK_DOC_GSI_KOTRUPI_2017_P009_01` (GSI, Scientific, Rank 2) | base: `0.7014` | rerank: `0.7164`

Government official documents from HPSDMA were present in the candidate pool but were not artificially boosted above GSI's scientific investigation.
- **Verdict:** `AUTHORITY_RERANKING: PASS`

---

## 4. Embedding Integrity

Forensic inspection of `data/master/embedding_manifest.json`, `data/knowledge_base/vector_store/index.faiss`, and `data/knowledge_base/vector_store/embeddings.npy` verified:
- **Model:** `BAAI/bge-base-en-v1.5` (version 1.5).
- **Dimension:** Strictly 768 across index (`index.d = 768`) and numpy vector store (`(812, 768)`).
- **Normalized Vectors:** Verified. L2 norms computed on `embeddings.npy`: $\min = 1.000000$, $\max = 1.000000$, $\text{mean} = 1.000000$.
- **Metric:** Cosine-equivalent Inner Product (`faiss.IndexFlatIP`, `metric_type = 0`).
- **Vector Count:** 812 vectors (`index.ntotal = 812`).
- **Chunk Count:** 812 chunks in `data/master/document_chunks.json`.
- **Failures:** 0 failed chunks (`failed_count = 0`).
- **Mapping:** Strict 1-to-1 correspondence between vector IDs ($0$ to $811$) and metadata sidecar entries in `data/knowledge_base/vector_store/index_meta.json`.
- **Duplicate Vectors Analysis:** 798 unique vector rows out of 812 rows. Forensic inspection traced the 14 duplicate vectors to 9 distinct groups of verbatim repeated demographic tables (e.g. Table 1.1 *"Demographic Features Since 1901"*, Table 1.5 *"Population and distribution data"*) across consecutive annual HPSDMA loss memorandums (2017 through 2025). The retriever's text-fingerprint deduplication engine (`seen_fingerprints`) successfully prevents duplicate presentation at query time.
- **Query / Index Model Parity:** Verified that `semantic_retriever.py` and `build_embeddings.py` load the exact same model `BAAI/bge-base-en-v1.5`, using identical L2-normalization and float32 conversion.
- **Verdict:** `EMBEDDING_INTEGRITY: PASS`

---

## 5. Idempotency Audit

- **Index Generation Architecture:** In `scripts/build_embeddings.py`, the vector store constructor instantiates a fresh `faiss.IndexFlatIP(embedding_dim)` and adds the exact validated array of 812 embeddings. Repeated executions write cleanly over the destination file rather than appending.
- **Hash Verification:**
  - `data/knowledge_base/vector_store/index.faiss`:
    - Measured on disk: `60e510e488e86bd80f695155ff009130e2f7256e201626286f97d4afcbf3c3be`
    - Manifest recorded: `60e510e488e86bd80f695155ff009130e2f7256e201626286f97d4afcbf3c3be` (MATCH)
  - `data/knowledge_base/vector_store/index_meta.json`:
    - Measured on disk: `bb03e48e16324609ad6a17da6bea71e9bbc71c97513602526e863de9402ecdfe`
    - Manifest recorded: `bb03e48e16324609ad6a17da6bea71e9bbc71c97513602526e863de9402ecdfe` (MATCH)
- **Vector Count Stability:** Exactly 812 chunks produce 812 vectors with 0 drift.
- **Verdict:** `IDEMPOTENCY: PASS`

---

## 6. Structured SQL Authority

Inspection of `scripts/structured_retriever.py` verified that exact numerical, categorical, and statistical queries execute exclusively against SQLite (`data/master/hp_extreme_weather.db`):
- `get_max_rainfall`: Parameterized query on `district_daily_rainfall` ordered by `max_rainfall_mm DESC LIMIT 1`.
- `get_rainfall_by_date`: Parameterized query on `district_daily_rainfall` for exact district/date observation.
- `get_rainfall_statistics`: Parameterized aggregate query (`SUM`, `AVG`, `MAX`, `MIN`) over `district_daily_rainfall`.
- `get_events_by_year`: Parameterized query on `extreme_weather_events` for specific year/district.
- `get_events_by_type`: Parameterized query on `extreme_weather_events` filtering by canonical event type.
- `get_cloudburst_summary`: Parameterized aggregation over `cloudburst_events`.
- `get_event_by_id`: Parameterized query by `canonical_event_id`.
- `get_telemetry_2026`: Parameterized query on `telemetry_rainfall`.
- **Parameter Safety:** All functions use SQLite `?` parameter placeholders with Python parameter tuples. No user-supplied text is interpolated into SQL queries. Entity validation guards enforce membership in `ALLOWED_DISTRICTS` and temporal ranges (`2011–2026`).
- **Verdict:** `STRUCTURED_SQL_AUTHORITY: PASS`

---

## 7. 2026 Source Coverage Audit

### The Telemetry vs Station Discrepancy Investigation
The previous Milestone 1 final sanity check noted 9 total 2026 records, whereas the retrieval evaluation report highlighted `telemetry_rainfall = 4 rows`. A direct audit of the database and raw datasets resolved the apparent discrepancy:

1. **Upstream Datasets:**
   - `data/processed/rainfall/telemetry_rainfall.csv`: Contains **4 rows** of real-time AWS telemetry records timestamped `2026-09-05 08:30:00` (Kangra Aero AWS, Sundernagar AWS, Shimla AWS, Bhuntar AWS) derived from `imd_shimla_three_hourly_telemetry_2026.pdf`. Source type: `IMD_TELEMETRY`.
   - `data/processed/rainfall/station_district_rainfall.csv`: Contains **5 rows** for 2026 (4 daily station observations on `2026-08-01` from `imd_shimla_daily_bulletin_2026.pdf` plus 1 chief rainfall report on `2026-09-07` from `imd_shimla_chief_rainfall_2026.pdf`). Source type: `IMD_STATION_OR_DISTRICT_OBSERVATION`.
2. **SQLite Database Presence:**
   - Table `telemetry_rainfall`: Contains exactly 4 rows (all 4 AWS records).
   - Table `station_district_rainfall`: Contains 25 rows, of which exactly 5 rows belong to 2026.
   - **Total 2026 rainfall observations in SQLite:** $4 + 5 = 9$ records.
3. **Findings:**
   - Zero records were lost.
   - The discrepancy was an artifact of terminology: `telemetry_rainfall` refers to the specific sub-table for 3-hourly automated AWS telemetry (`IMD_TELEMETRY`), whereas the Milestone 1 summary aggregated telemetry and daily station bulletins together ($4 + 5 = 9$).
4. **Partial Period Integrity:**
   - Queries requesting annual aggregates for 2026 (such as GQ_12) strictly return status `INSUFFICIENT_FOR_FULL_YEAR` with an explicit scientific advisory message.
- **Verdict:** `2026_SOURCE_COVERAGE: PASS`

---

## 8. Event Count Consistency Audit

A cross-table verification was performed across all event tables:
- `data/processed/cloudburst/cloudburst_events.csv`: **23 rows**.
- `data/processed/flash_flood/flash_flood_events.csv`: **17 rows**.
- **Sum of raw source records:** $23 + 17 = 40$ rows.
- `data/processed/combined/extreme_weather_events.csv`: **39 canonical events**.
- `reports/event_source_mapping.csv`: **40 rows** (100% source records mapped).
- `reports/event_deduplication_audit.csv`: **40 rows**.

### July 2021 Boh / Dharamshala Consolidation Audit
- `CB_2021_KANGRA_001` (Cloudburst in Dharamshala/Boh from `hpsdma_memo_monsoon_2021.pdf`) and `FF_2021_KANGRA_001` (Flash flood in Manjhi Khad from `hpsdma_memo_monsoon_2021.pdf`) both occurred on 2021-07-12 in Kangra district.
- In `extreme_weather_events.csv`, these two records were consolidated into a single canonical event: `CANON_20210712_KAN_DHA` with `primary_event_type = 'Cloudburst and Flash Flood'` and `source_count = 2`.
- Both original source records remain intact in their respective source CSVs and in `event_source_mapping.csv`. No source record disappeared.
- **Verdict:** `EVENT_PROVENANCE: PASS`

---

## 9. Evidence-Type Integrity Audit

Audit of retrieval outputs across all route handlers verified the strict taxonomy:
- **`OBSERVED`:** Applied strictly to raw physical measurements (e.g., daily gridded observation `EVID_RAIN_OBS_Kangra_2011-01-02`, AWS telemetry `EVID_TELEMETRY_2026`, specific disaster log `EVID_EVENTS_2023_Mandi`).
- **`CALCULATED`:** Applied to mathematical aggregations (e.g., peak spatial cell calculation `EVID_MAX_RAIN_Kangra_2023-08-14`, multi-year averages `EVID_RAIN_STAT_Mandi_RANGE`, summary event frequency `EVID_TYPE_Flash Flood_Kullu`).
- **`REPORTED`:** Applied to all narrative statements extracted from government and scientific documents (`scripts/semantic_retriever.py` line 157: `"evidence_type": "REPORTED"`).
- **Negative Isolation:** Verified that **zero document claims are labeled as `OBSERVED`**.
- **Verdict:** `EVIDENCE_TYPE_INTEGRITY: PASS`

---

## 10. Negative Query Audit — CRITICAL VULNERABILITY IDENTIFIED

The 5 benchmark negative queries (GQ_21–GQ_25) returned `NO_SUPPORTED_EVIDENCE`. However, a forensic inspection of `scripts/hybrid_retriever.py` lines 37–43 and lines 126–138 revealed that this rejection was **not** produced by evidence exhaustion or database validation, but by a brittle, hardcoded keyword blacklist:
```python
DISALLOWED_KNOWN_DISTRICTS = ["jaipur", "bilaspur", "solan", "una", "hamirpur", "chamba", "lahaul", "spiti", "kinnaur", "sirmour"]
FICTIONAL_OR_UNSUPPORTED = [
    "tsunami", "volcano", "cyclone", "tornado", "earthquake", "richter", 
    "magnitude", "snowfall depth", "avalanche pressure", "meteor"
]
```

### Adversarial Forensic Failures
When subjected to queries with out-of-scope entities not included in this 10-word list, the negative rejection guard **completely broke down**:

1. **Out-of-Scope District (*"What was the maximum rainfall in Pune in 2023?"*):**
   - **Behavior:** The query was **not** rejected. "Pune" is neither in `ALLOWED_DISTRICTS` nor in `DISALLOWED_KNOWN_DISTRICTS`.
   - **Execution:** `extract_entities` returned `district = None`. The query matched `STRUCTURED_SIGNALS` ("maximum"). It routed to `STRUCTURED` with `intent = "MAX_RAINFALL"`.
   - **Result:** `sr.get_max_rainfall(district=None, year=2023)` executed a SQL query finding the maximum rainfall across *all* target districts, and authoritatively returned:
     > *"Peak spatial grid cell rainfall in Kangra on 2023-08-14 was 246.81 mm."*
   - **Impact:** **Severe silent hallucination.** Asking for rainfall in Pune silently returned rainfall in Kangra.
2. **Unsupported Environmental Parameter (*"What was the wind speed in Shimla on 2023-07-09?"*):**
   - **Behavior:** Routed to `STRUCTURED` with `intent = "DATE_RAINFALL"`. Authoritatively returned Shimla's rainfall observation for a wind speed query.
3. **Unsupported Parameter (*"What was the solar radiation in Kangra in July 2023?"*):**
   - **Behavior:** Routed to `DOCUMENT` (`GENERAL_DOCUMENT_SEARCH`), returning 5 passages describing monsoon rainfall and landslide loss.
4. **Unsupported Disaster Type (*"How many avalanche accidents occurred in Kullu in 2022?"*):**
   - **Behavior:** Routed to `STRUCTURED` (`EVENT_COUNT`). Returned cloudburst event `CANON_20220706_KUL_MAN` in Chojh village as the answer.

- **Conclusion:** The negative rejection system does not verify entity applicability or evidence absence; it relies on superficial pattern matching on 5 known test queries.
- **Verdict:** `NEGATIVE_QUERY_INTEGRITY: FAIL`

---

## 11. Router Audit — CRITICAL VULNERABILITY IDENTIFIED

Inspection of `docs/query_routing_rules.md` and `scripts/hybrid_retriever.py` revealed:
- **Routing Terminology:** The documentation explicitly defines `DOCUMENT` as using the FAISS vector store for semantic document retrieval. This terminology is consistently maintained.
- **Multi-Signal Evaluation:** The router extracts districts, dates, years, event types, parameters, and intent signals.
- **Structural Routing Defects:**
  1. **Unbounded Null Fallback:** When a query contains an unrecognized entity, `entities["district"]` evaluates to `None`. Rather than failing fast or rejecting the entity, `hybrid_retriever.py` treats `None` as "query the entire state", routing unconstrained SQL queries that fabricate false evidence.
  2. **Intent Collision:** Structured rules check only for query keywords (`"maximum"`, `"how many"`, ISO dates) without validating whether the requested parameter belongs to the project's authorized schema (Rainfall, Cloudburst, Flash Flood). Any question containing an ISO date (`YYYY-MM-DD`) is unconditionally assumed to be a rainfall query.
- **Verdict:** `ROUTER_INTEGRITY: FAIL`

---

## 12. Provenance Audit

A random stratified sample of 20 evidence items was drawn from retrieval results across structured and document routes:

```text
[01/20] (DOCUMENT  ) [GQ_18] CHK_DOC_HPSDMA_PDNA_2023_P180_01     -> PASS
[02/20] (DOCUMENT  ) [GQ_05] CHK_DOC_HPSDMA_MEMO_2023_P012_01     -> PASS
[03/20] (STRUCTURED) [GQ_02] EVID_TYPE_Flash Flood_Kullu          -> PASS
[04/20] (DOCUMENT  ) [GQ_20] CHK_DOC_HPSDMA_MEMO_2023_P019_02     -> PASS
[05/20] (STRUCTURED) [GQ_07] EVID_TELEMETRY_2026                  -> PASS
[06/20] (DOCUMENT  ) [GQ_06] CHK_DOC_HPSDMA_PDNA_2023_P030_01     -> PASS
[07/20] (DOCUMENT  ) [GQ_06] CHK_DOC_HPSDMA_PDNA_2023_P002_01     -> PASS
[08/20] (DOCUMENT  ) [GQ_05] CHK_DOC_HPSDMA_PDNA_2023_P019_02     -> PASS
[09/20] (STRUCTURED) [GQ_05] EVID_EVENTS_2023_Kullu               -> PASS
[10/20] (DOCUMENT  ) [GQ_16] CHK_DOC_HPSDMA_LR3_2007_2015_P001_01 -> PASS
[11/20] (STRUCTURED) [GQ_05] EVID_RAIN_STAT_Kullu_2023            -> PASS
[12/20] (DOCUMENT  ) [GQ_16] CHK_DOC_HPSDMA_MEMO_2017_P010_01     -> PASS
[13/20] (DOCUMENT  ) [GQ_11] CHK_DOC_GSI_KOTRUPI_2017_P001_01     -> PASS
[14/20] (DOCUMENT  ) [GQ_03] CHK_DOC_GSI_BOH_2021_P002_01         -> PASS
[15/20] (DOCUMENT  ) [GQ_20] CHK_DOC_HPSDMA_MEMO_2024_P027_01     -> PASS
[16/20] (DOCUMENT  ) [GQ_20] CHK_DOC_HPSDMA_MEMO_2023_P030_01     -> PASS
[17/20] (DOCUMENT  ) [GQ_06] CHK_DOC_HPSDMA_MEMO_2023_P001_01     -> PASS
[18/20] (DOCUMENT  ) [GQ_18] CHK_DOC_HPSDMA_MEMO_2023_P019_02     -> PASS
[19/20] (STRUCTURED) [GQ_15] EVID_RAIN_STAT_Kullu_2013            -> PASS
[20/20] (DOCUMENT  ) [GQ_16] CHK_DOC_HPSDMA_PDNA_2023_P035_02     -> PASS
```

- Every sampled document chunk successfully verified `chunk_id`, `document_id`, `source_id`, `page_number`, and source URL against `document_registry.csv` and `source_registry.csv`.
- Every sampled structured result verified `evidence_id`, `evidence_type`, `source_id`, and underlying SQL table aggregations.
- **Metric:** `PROVENANCE_SAMPLE: 20/20 PASS`
- **Verdict:** `PROVENANCE: PASS`

---

## 13. Milestone 1 Immutability Audit

SHA-256 hashes of all 8 core Milestone 1 datasets were computed and verified against `data/master/milestone1_checksums.json`:

| File Path | Baseline SHA-256 Hash | Current Computed Hash | Match Status |
| :--- | :--- | :--- | :--- |
| `data/processed/rainfall/imd_gridded_daily_rainfall.csv` | `d64617b1cc52642dcdefad3b5f043aaa...` | `d64617b1cc52642dcdefad3b5f043aaa...` | **MATCH** |
| `data/processed/rainfall/district_daily_rainfall.csv` | `2bfc4eb1e300cdd49ac8eedd19972da6...` | `2bfc4eb1e300cdd49ac8eedd19972da6...` | **MATCH** |
| `data/processed/rainfall/station_district_rainfall.csv` | `d45a98becd585682d340174e3ca769da...` | `d45a98becd585682d340174e3ca769da...` | **MATCH** |
| `data/processed/rainfall/telemetry_rainfall.csv` | `4b6c041828c97d08d71f9579cbd7c61a...` | `4b6c041828c97d08d71f9579cbd7c61a...` | **MATCH** |
| `data/processed/cloudburst/cloudburst_events.csv` | `e5bc65e744e31851326df9f5ee7e8bf4...` | `e5bc65e744e31851326df9f5ee7e8bf4...` | **MATCH** |
| `data/processed/flash_flood/flash_flood_events.csv` | `e6e5200fd952b66cfab63f3a2a5b0ed0...` | `e6e5200fd952b66cfab63f3a2a5b0ed0...` | **MATCH** |
| `data/processed/combined/extreme_weather_events.csv` | `17e514aeb457f205c063177c66f33bc5...` | `17e514aeb457f205c063177c66f33bc5...` | **MATCH** |
| `reports/source_registry.csv` | `4ee9b464a5f758b4a311fad5f9b3b5f4...` | `4ee9b464a5f758b4a311fad5f9b3b5f4...` | **MATCH** |

- **Files Checked:** Exactly 8 files.
- **Integrity Status:** 100% strictly identical to baseline.
- **Verdict:** `MILESTONE_1_INTEGRITY: PASS`

---

## 14. Scientific Sanity Check of the Perfect Scores

The reported scores of **100.0% Routing Accuracy**, **100.0% Hit@1**, **100.0% Hit@3**, and **100.0% Hit@5** were forensically evaluated:

1. **Structured Queries Conflated with Information Retrieval Hit@k:**
   - In `scripts/validate_retrieval.py` lines 122–152, Hit@1 was evaluated by checking if `top1_src in expected_sources`.
   - Of the 17 evaluable queries, **8 queries were pure SQL calculations** (GQ_01, GQ_02, GQ_04, GQ_08, GQ_09, GQ_10, GQ_17, GQ_19). In each case, `retrieved_documents = []`. Because the Python SQL wrapper returns `source_id: "SRC_IMD_GRIDDED_025"` or `"SRC_HPSDMA_LOSS_MEMORANDUMS"`, `top1_src in expected_sources` was trivially evaluated as `True`.
   - SQL queries returning hardcoded database table sources do not represent vector information retrieval hits.
2. **Coarse Relevance Granularity:**
   - Only 6 pure semantic document queries exist in the benchmark (GQ_03, GQ_06, GQ_11, GQ_16, GQ_18, GQ_20).
   - In all 6 document queries, relevance was measured at the coarse **document ID** level (`DOC_HPSDMA_PDNA_2023`, `DOC_GSI_KOTRUPI_2017`), rather than the passage/chunk ID level. Retrieving *any* arbitrary chunk from the 200+ chunk PDNA report scored a perfect Hit@1.
3. **Small Sample Size & Keyword Over-Fitting:**
   - The evaluation set consists of only 25 questions, crafted with exact phrases that trigger deterministic rules (e.g. *"according to GSI"*, *"maximum rainfall"*, *"Jaipur"*, *"tsunami"*).
- **Conclusion:** While the system correctly answered the 25 specific benchmark questions, claiming a general 100% Hit@1/3/5 retrieval quality across arbitrary weather queries is not scientifically defensible.
- **Verdict:** `METRIC_VALIDITY: LIMITED`

---

## 15. Final Audit Classification

### Embedding Integrity
PASS

### Idempotency
PASS

### Metadata Filtering
PASS

### Structured SQL Authority
PASS

### 2026 Coverage
PASS

### Event Provenance
PASS

### Evidence-Type Integrity
PASS

### Negative Query Integrity
FAIL

### Router Integrity
FAIL

### Provenance
PASS

### Milestone 1 Integrity
PASS

### Golden Evaluation Independence
PASS

### Metric Validity
LIMITED

---

## FINAL DECISION

```text
======================================================
NOT_READY — RETRIEVAL_REPAIR_REQUIRED
======================================================
```

### Mandatory Repair Actions Required Before Milestone 3:
1. **Enforce Comprehensive District Bounds in Router:** In `scripts/hybrid_retriever.py`, if a query explicitly mentions a district or geographical entity outside `ALLOWED_DISTRICTS` (e.g., Pune, Delhi, Jaipur, Solan), the router must reject it with `NO_SUPPORTED_EVIDENCE` rather than passing `district = None` to SQLite.
2. **Enforce Entity-Parameter Compatibility in SQL Router:** Prevent queries seeking unsupported parameters (wind speed, solar radiation, avalanche, temperature) from triggering default rainfall or cloudburst SQL lookups simply because a date or "how many" was parsed.
3. **Refactor Hit@k Evaluation:** Separate SQL execution accuracy from FAISS semantic Hit@k in `scripts/validate_retrieval.py`, and evaluate document retrieval against ground-truth chunk-level passages rather than broad document IDs.
