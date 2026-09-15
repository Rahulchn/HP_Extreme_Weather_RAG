# Milestone 2B — Hybrid Retrieval Evaluation Report (Repaired)

## Project: Himachal Pradesh Extreme Weather RAG System (2011–2026)
- **Target Districts**: Kangra, Mandi, Shimla, Kullu
- **Core Parameters**: Rainfall, Cloudburst, Flash Flood
- **Execution Date**: 2026-09-08 06:04:59 UTC
- **Final Verdict**: `READY_FOR_MILESTONE_3`

---

## 1. Executive Performance Summary (Decoupled Benchmark)

| Evaluation Track | Metric Name | Target | Measured Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Routing Safety** | `OVERALL_ROUTING_ACCURACY` | $\ge 95.0\%$ | **100.0%** (52/52) | **PASSED** |
| **Track 1: Structured** | `STRUCTURED_QUERY_ACCURACY` | $\ge 95.0\%$ | **100.0%** (10/10) | **PASSED** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@1` | $\ge 70.0\%$ | **87.5%** (14/16) | **PASSED** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@3` | $\ge 80.0\%$ | **93.75%** (15/16) | **PASSED** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@5` | $\ge 85.0\%$ | **100.0%** (16/16) | **PASSED** |
| **Track 2: Supplemental** | `DOCUMENT_SOURCE_HIT@1` | $\ge 90.0\%$ | **100.0%** (16/16) | **PASSED** |
| **Track 3: Hybrid** | `HYBRID_FUSION_ACCURACY` | $\ge 90.0\%$ | **100.0%** (10/10) | **PASSED** |
| **Track 3: Hybrid Branches** | Structured / Document Branches | $100\%$ | **100.0% / 100.0%** | **PASSED** |
| **Track 4: Negative** | `NEGATIVE_QUERY_ACCURACY` | $100.0\%$ | **100.0%** (16/16) | **PASSED** |
| **Provenance** | `PROVENANCE_COMPLETENESS` | $100.0\%$ | **100.0%** (52/52) | **PASSED** |
| **Milestone 1 Baseline** | `MILESTONE_1_INTEGRITY` | $100\%$ Immutable | **VERIFIED UNCHANGED** | **PASSED** |

### Latency Profiles by Retrieval Route
- **Structured Retrieval Latency**: `2.6 ms`
- **Semantic Retrieval Latency**: `687.57 ms`
- **Hybrid Retrieval Latency**: `87.62 ms`
- **Rejection Guard Latency**: `0.25 ms`

---

## 2. Benchmark Composition & Methodology
- **Total Questions:** 52
  - **Structured SQL Queries:** 10 (Exact calculations, dates, counts, 2026 incomplete checks)
  - **Semantic Document Queries:** 16 (Independently curated passage-level ground truth)
  - **Hybrid Dual-Engine Queries:** 10 (Disaster-rainfall correlation and fusion)
  - **Negative Adversarial Queries:** 16 (Unsupported geography, variables, out-of-bounds years)

---

## 3. Conclusion & Verdict
```text
======================================================
FINAL STATUS: READY_FOR_MILESTONE_3
======================================================
```
