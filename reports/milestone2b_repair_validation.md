# Milestone 2B — Router Safety & Retrieval Evaluation Repair Validation Report

**Project:** Himachal Pradesh Extreme Weather RAG System (2011–2026)  
**Authorized Scope:** Kangra, Mandi, Shimla, Kullu  
**Core Environmental Parameters:** Rainfall, Cloudburst, Flash Flood  
**Audit Finding Being Repaired:** `NOT_READY — RETRIEVAL_REPAIR_REQUIRED` (Forensic Audit Report `reports/milestone2b_forensic_audit.md`)  
**Validation Date:** 2026-09-08  
**Final Status Decision:** `NOT_READY — RETRIEVAL_REPAIR_REQUIRED`  

---

## 1. Executive Summary of Repairs

Following the independent forensic audit of Milestone 2B, three critical architectural defects were identified and resolved without modifying Milestone 1 datasets, embeddings, or the FAISS vector index:

1. **Elimination of Geographic Blacklists in Favor of a Multi-Tier Positive Model:**
   - Removed `DISALLOWED_KNOWN_DISTRICTS` and avoided reliance on fragile regex heuristics (`in|at|for + word`).
   - Implemented a strict 4-state geographic taxonomy: `SUPPORTED_GEOGRAPHY`, `EXPLICIT_UNSUPPORTED_GEOGRAPHY`, `STATE_LEVEL`, and `NO_GEOGRAPHY_SPECIFIED`.
   - Guaranteed the invariant: `explicit unsupported geography != geography not specified`. Any query explicitly naming an out-of-scope geography (e.g. Pune, Delhi, Bilaspur, Atlantis) fails closed immediately with `NO_SUPPORTED_EVIDENCE` and never silently converts to a state-wide or null-district SQL query.
2. **Fail-Closed Parameter Protection & Landslide Scope Isolation:**
   - Added positive parameter classification enforcing the frozen 3-parameter schema (`RAINFALL`, `CLOUDBURST`, `FLASH_FLOOD`). Unsupported variables (`wind speed`, `temperature`, `solar radiation`, `avalanche`, `earthquake`, `snowfall depth`, etc.) fail closed immediately regardless of accompanying dates, districts, or aggregate operators.
   - Enforced strict scope isolation for `LANDSLIDE_IMPACT` (and terms like `debris flow`, `slope failure`, `infrastructure damage`, `road blocked`, `casualties`, `deaths`): classified as DOCUMENT/NARRATIVE evidence only, **never** executing structured SQL rainfall calculations.
3. **Decoupled Evaluation Benchmark with Independent Passage-Level Ground Truth:**
   - Decoupled the previous evaluation into 4 distinct tracks: Track 1 Structured (10 queries), Track 2 Semantic (16 queries), Track 3 Hybrid (10 queries), Track 4 Negative (16 queries), totaling 52 benchmark queries.
   - For Track 2 Semantic evaluation, independently curated `relevant_chunk_ids` directly from `data/master/document_chunks.json` prior to evaluation. Evaluated chunk set intersection (`Hit@1`, `Hit@3`, `Hit@5`) without using document-level relevance as a substitute.
   - Fixed premature FAISS candidate pool truncation by expanding search depth to the full vector pool (`index.ntotal = 812`), ensuring metadata filters have complete visibility over candidate passages.

---

## 2. Router Safety & Adversarial Validation

The standalone adversarial test suite (`scripts/test_router_safety.py`) was executed to mathematically verify the positive geographic model and fail-closed parameter protection across 34 tests.

**Execution Result:** `34 / 34 PASSED (100.0%)`

### Adversarial Geographic Cases (No Blacklists)
| Test Case | Query | Actual Route | Status | Zero Evidence Rows | Result |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Out-of-scope Pune | *"What was the maximum rainfall in Pune in 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |
| Out-of-scope Delhi | *"What was the rainfall in Delhi in August 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |
| Out-of-scope Mumbai | *"How many cloudburst events occurred in Mumbai in 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |
| Out-of-scope Chandigarh | *"What was the flash flood damage in Chandigarh in July 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |
| Out-of-scope Dehradun | *"Describe the extreme rainfall recorded in Dehradun in 2021."* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |
| Out-of-scope Bilaspur (HP) | *"What was the total rainfall in Bilaspur district in 2022?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |
| Out-of-scope Solan (HP) | *"How many flash floods occurred in Solan in 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |
| Invented Location Atlantis | *"What was the peak rainfall in Atlantis in 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |
| Invented Location Xandaria | *"How many cloudbursts were recorded in Xandaria district in 2021?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | Yes (0 / 0) | **PASS** |

### Parameter Adversarial & Collision Cases
| Test Case | Query | Actual Route | Status | Result |
| :--- | :--- | :--- | :--- | :---: |
| Unsupported Wind Speed | *"What was the wind speed in Shimla in July 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Unsupported Temperature | *"What was the maximum temperature recorded in Mandi in 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Unsupported Solar Radiation | *"What was the solar radiation in Kangra in July 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Unsupported Avalanche | *"How many avalanche accidents occurred in Kullu in 2022?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Unsupported Earthquake | *"What was the earthquake magnitude in Kangra on 2023-07-09?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Unsupported Snowfall Depth | *"What was the snowfall depth in Manali in January 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Param + Valid Date Collision | *"What was the wind speed in Shimla on 2023-07-09?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Param + Valid District Collision | *"What was the solar radiation in Kangra in August 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Param + "Maximum" Operator | *"What was the maximum temperature in Mandi in 2023?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |
| Param + "How Many" Operator | *"How many avalanche casualties were recorded in Kullu in 2022?"* | `NEGATIVE_REJECTED` | `NO_SUPPORTED_EVIDENCE` | **PASS** |

### Geographic State Distinction Regression (Correction 1)
- **Case 1 (Supported Geography):** *"What was the maximum rainfall in Kangra in 2023?"* $\to$ Routes to `STRUCTURED` with `district=Kangra`. **PASSED**
- **Case 2 (No Geography Specified):** *"What was the maximum rainfall in 2023?"* $\to$ Routes to `STRUCTURED` with `district=None` (permitted state-wide scope). **PASSED**
- **Case 3 (Explicit Unsupported Geography):** *"What was the maximum rainfall in Pune in 2023?"* $\to$ Routes to `NEGATIVE_REJECTED` with `NO_SUPPORTED_EVIDENCE`. Confirmed that Pune did **NOT** fall back to state-wide or null-district SQL execution. **PASSED**

### Landslide Scope Isolation (Correction 2)
- Query: *"How did landslides affect roads in Mandi in 2023?"*
- Route: `DOCUMENT`
- Status: `OK`
- Structured Evidence Rows: **0 rows executed** (no SQL rainfall calculations triggered).
- Document Evidence Chunks: **5 chunks retrieved** (HPSDMA PDNA / Memorandum transport sector damage passages). **PASSED**

---

## 3. Comprehensive Decoupled Benchmark Results

The repaired system was evaluated against the full 52-question benchmark (`evaluation/golden_questions.json`) using `scripts/validate_retrieval.py`.

```text
=================================================================
   EVALUATION COMPLETE — VERDICT: NOT_READY — RETRIEVAL_REPAIR_REQUIRED
   Routing Accuracy:       100.0% (Target >= 95.0%) -> [PASSED]
   Structured Accuracy:    100.0% (Target >= 95.0%) -> [PASSED]
   Semantic Hit@1:         68.75% (Target >= 70.0%) -> [FAILED]
   Semantic Hit@3:         87.5%  (Target >= 80.0%) -> [PASSED]
   Semantic Hit@5:         93.75% (Target >= 85.0%) -> [PASSED]
   Document Source Hit@1:  87.5%  (Target >= 90.0%) -> [FAILED]
   Hybrid Fusion:          100.0% (Target >= 90.0%) -> [PASSED]
   Negative Accuracy:      100.0% (Target 100.0%)   -> [PASSED]
   Provenance Rate:        100.0% (Target 100.0%)   -> [PASSED]
   Milestone 1 Baseline:   100% Immutable           -> [PASSED]
=================================================================
```

### Executive Performance Summary Table

| Evaluation Track | Metric Name | Target | Measured Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Routing Safety** | `OVERALL_ROUTING_ACCURACY` | $\ge 95.0\%$ | **100.0%** (52/52) | **PASSED** |
| **Track 1: Structured** | `STRUCTURED_QUERY_ACCURACY` | $\ge 95.0\%$ | **100.0%** (10/10) | **PASSED** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@1` | $\ge 70.0\%$ | **68.75%** (11/16) | **FAILED** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@3` | $\ge 80.0\%$ | **87.50%** (14/16) | **PASSED** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@5` | $\ge 85.0\%$ | **93.75%** (15/16) | **PASSED** |
| **Track 2: Supplemental** | `DOCUMENT_SOURCE_HIT@1` | $\ge 90.0\%$ | **87.50%** (14/16) | **FAILED** |
| **Track 3: Hybrid** | `HYBRID_FUSION_ACCURACY` | $\ge 90.0\%$ | **100.0%** (10/10) | **PASSED** |
| **Track 3: Hybrid Branches** | Structured / Document Branches | $100\%$ | **100.0% / 100.0%** | **PASSED** |
| **Track 4: Negative** | `NEGATIVE_QUERY_ACCURACY` | $100.0\%$ | **100.0%** (16/16) | **PASSED** |
| **Provenance** | `PROVENANCE_COMPLETENESS` | $100.0\%$ | **100.0%** (52/52) | **PASSED** |
| **Milestone 1 Baseline** | `MILESTONE_1_INTEGRITY` | $100\%$ Immutable | **VERIFIED UNCHANGED** | **PASSED** |

### Track 1: Structured Query Evaluation (`STRUCTURED_QUERY_ACCURACY`)
- **Queries Evaluated:** 10
- **Target Operations:** `get_max_rainfall`, `get_rainfall_by_date`, `get_rainfall_statistics`, `get_events_by_type`, `get_events_by_year`, `get_cloudburst_summary`, `get_telemetry_2026`.
- **Accuracy:** **100.0% (10/10)**
- **Verification Criteria:** Operation invocation, district extraction, year/date range, numerical value/count correctness, data state verification (`OK`, `ZERO_RAINFALL`, `ZERO_DOCUMENTED_EVENTS`, `INSUFFICIENT_FOR_FULL_YEAR`).

### Track 2: Semantic Document Evaluation (Passage-Level Hit@K)
- **Queries Evaluated:** 16
- **Ground Truth Methodology:** Independently curated `relevant_chunk_ids` directly from `data/master/document_chunks.json` prior to evaluation. Evaluated as:
  $$\text{Hit@K} = 1 \iff \{\text{retrieved\_chunks}[:K]\} \cap \{\text{relevant\_chunk\_ids}\} \neq \emptyset$$
- **Measured Metrics & Status:**
  - **`SEMANTIC_PASSAGE_HIT@1`:** **68.75%** (11/16) [Target $\ge 70.0\%$] $\to$ **FAILED** (Measured value is below declared target)
  - **`SEMANTIC_PASSAGE_HIT@3`:** **87.50%** (14/16) [Target $\ge 80.0\%$] $\to$ **PASSED** (Exceeds declared target)
  - **`SEMANTIC_PASSAGE_HIT@5`:** **93.75%** (15/16) [Target $\ge 85.0\%$] $\to$ **PASSED** (Exceeds declared target)
  - **`DOCUMENT_SOURCE_HIT@1` (Supplemental):** **87.50%** (14/16) [Target $\ge 90.0\%$] $\to$ **FAILED** (Measured value is below declared target)

### Track 3: Hybrid Dual-Engine Evaluation (`HYBRID_FUSION_ACCURACY`)
- **Queries Evaluated:** 10
- **Branches Evaluated Independently:**
  - `HYBRID_STRUCTURED_BRANCH_CORRECT`: **100.0%** (10/10)
  - `HYBRID_DOCUMENT_BRANCH_CORRECT`: **100.0%** (10/10)
  - `HYBRID_FUSION_CORRECT`: **100.0%** (10/10) — *Exceeds 90% target*
- **Operations:** Dual-engine execution connecting SQLite rainfall observations/frequencies with GSI geotechnical and HPSDMA damage memorandums.

### Track 4: Negative Adversarial Evaluation (`NEGATIVE_QUERY_ACCURACY`)
- **Queries Evaluated:** 16
- **Accuracy:** **100.0% (16/16)**
- **Verification Criteria:** Immediate routing to `NEGATIVE_REJECTED`, status `NO_SUPPORTED_EVIDENCE`, 0 structured rows, 0 document chunks, and non-empty project-scope warnings explaining why the entity or parameter is unsupported.

---

## 4. Latency Profiles

Retrieval latencies were measured across all 52 benchmark executions:
- **Structured SQLite Retrieval:** `3.19 ms` average
- **Semantic FAISS Retrieval:** `627.8 ms` average (including BGE embedding generation)
- **Hybrid Dual-Engine Retrieval:** `89.35 ms` average
- **Early Rejection Guard:** `0.23 ms` average (deterministic sub-millisecond fail-closed rejection)

---

## 5. Provenance & 2026 Safeguards

### Provenance Completeness
- Verified across all 52 queries (`52/52 = 100.0%`).
- Every retrieved structured row and document chunk provides `evidence_type` (`OBSERVED`, `CALCULATED`, `REPORTED`) and a valid `source_id` resolvable in `reports/source_registry.csv`.

### 2026 Safeguards
- Annual inquiries for 2026 return `INSUFFICIENT_FOR_FULL_YEAR` with clear diagnostic warnings: `"2026 data is PARTIAL. Telemetry reflects recent AWS observations."`
- Telemetry lookups return `TELEMETRY_OBSERVATION` with `SRC_IMD_SHIMLA_TELEMETRY_2026`.

---

## 6. Milestone 1 Baseline Integrity Verification

Cryptographic SHA-256 hashes of all 8 Milestone 1 baseline datasets were verified against `reports/milestone1_repair_report.md`:

| Dataset Path | Expected Hash | Measured Hash | Integrity Status |
| :--- | :--- | :--- | :---: |
| `data/processed/rainfall/imd_gridded_daily_rainfall.csv` | `d64617b1cc52...` | `d64617b1cc52...` | **PASS (Match)** |
| `data/processed/rainfall/district_daily_rainfall.csv` | `2bfc4eb1e300...` | `2bfc4eb1e300...` | **PASS (Match)** |
| `data/processed/rainfall/station_district_rainfall.csv` | `d45a98becd58...` | `d45a98becd58...` | **PASS (Match)** |
| `data/processed/rainfall/telemetry_rainfall.csv` | `4b6c041828c9...` | `4b6c041828c9...` | **PASS (Match)** |
| `data/processed/cloudburst/cloudburst_events.csv` | `e5bc65e744e3...` | `e5bc65e744e3...` | **PASS (Match)** |
| `data/processed/flash_flood/flash_flood_events.csv` | `e6e5200fd952...` | `e6e5200fd952...` | **PASS (Match)** |
| `data/processed/combined/extreme_weather_events.csv` | `17e514aeb457...` | `17e514aeb457...` | **PASS (Match)** |
| `reports/source_registry.csv` | `4ee9b464a5f7...` | `4ee9b464a5f7...` | **PASS (Match)** |

**Milestone 1 Immutability:** 100% verified. No Milestone 1 data or logic was modified during this repair.

---

## 7. Final Readiness Decision

Under the declared threshold evaluation gates, Milestone 2B cannot be certified as ready:
- Multi-tier geographic entity detection without blacklists: **PASSED (100% rejection of unsupported geographies)**
- Strict scope isolation of `LANDSLIDE_IMPACT` (0 SQL rainfall queries): **PASSED**
- Fail-closed unsupported parameter protection: **PASSED (100% rejection of unsupported variables)**
- Hybrid fusion accuracy: **PASSED (100.0%)**
- Negative query accuracy: **PASSED (100.0%)**
- Provenance completeness: **PASSED (100.0%)**
- Milestone 1 baseline immutability: **PASSED (100% verified)**
- Semantic Hit@3 (87.50%) and Hit@5 (93.75%): **PASSED**
- **Semantic Passage Hit@1:** **68.75%** vs declared target $\ge 70.0\%$ $\to$ **FAILED**
- **Document Source Hit@1:** **87.50%** vs declared target $\ge 90.0\%$ $\to$ **FAILED**

Because mandatory readiness thresholds have not been met, Milestone 3 must NOT be started. The system status remains:

```text
======================================================
FINAL STATUS: NOT_READY — RETRIEVAL_REPAIR_REQUIRED
======================================================
```
