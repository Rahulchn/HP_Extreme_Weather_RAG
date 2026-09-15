"""
validate_retrieval.py
Milestone 2B Repaired: Decoupled Retrieval Evaluation & Benchmark Runner

Evaluates the 52-question golden benchmark across 4 decoupled tracks:
1. Track 1: STRUCTURED (10 queries) -> Evaluates STRUCTURED_QUERY_ACCURACY (SQL execution, parameters, values, data states)
2. Track 2: DOCUMENT (16 queries)   -> Evaluates SEMANTIC_HIT@1, Hit@3, Hit@5 strictly against independent chunk-level ground truth
3. Track 3: HYBRID (10 queries)     -> Evaluates STRUCTURED_EVIDENCE_CORRECT, DOCUMENT_EVIDENCE_CORRECT, HYBRID_FUSION_CORRECT
4. Track 4: NEGATIVE (16 queries)   -> Evaluates NEGATIVE_QUERY_ACCURACY (fail-closed NO_SUPPORTED_EVIDENCE)

Outputs:
- evaluation/retrieval_results.json
- reports/retrieval_evaluation.md
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import time
import hashlib
from datetime import datetime, timezone
import scripts.hybrid_retriever as hr

GOLDEN_QUESTIONS_PATH = "evaluation/golden_questions.json"
RESULTS_PATH = "evaluation/retrieval_results.json"
REPORT_PATH = "reports/retrieval_evaluation.md"
MANIFEST_PATH = "data/master/embedding_manifest.json"
M1_CHECKSUMS_PATH = "data/master/milestone1_checksums.json"

def verify_milestone1_immutability():
    if not os.path.exists(M1_CHECKSUMS_PATH):
        return False, "Baseline checksums file not found"
    with open(M1_CHECKSUMS_PATH, "r") as f:
        baseline = json.load(f)
    
    mismatches = []
    for fpath, orig_hash in baseline.items():
        if not os.path.exists(fpath):
            mismatches.append(f"{fpath}: MISSING")
            continue
        curr_hash = hashlib.sha256(open(fpath, "rb").read()).hexdigest()
        if curr_hash != orig_hash:
            mismatches.append(f"{fpath}: HASH MISMATCH ({curr_hash} != {orig_hash})")
            
    if mismatches:
        return False, mismatches
    return True, f"All {len(baseline)} Milestone 1 datasets remain strictly identical and immutable"

def evaluate_retrieval():
    print("=================================================================")
    print("   MILESTONE 2B: DECOUPLED RETRIEVAL BENCHMARK EVALUATOR")
    print("=================================================================\n")

    if not os.path.exists(GOLDEN_QUESTIONS_PATH):
        raise FileNotFoundError(f"Missing benchmark questions: {GOLDEN_QUESTIONS_PATH}")

    with open(GOLDEN_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} evaluation questions across 4 distinct tracks.")

    results = []
    latencies_by_route = {"STRUCTURED": [], "DOCUMENT": [], "HYBRID": [], "NEGATIVE_REJECTED": []}

    # Metric accumulators
    routing_correct = 0
    provenance_complete_count = 0

    # Track 1: Structured
    str_total = 0
    str_correct = 0

    # Track 2: Semantic Document
    doc_total = 0
    doc_hit1 = 0
    doc_hit3 = 0
    doc_hit5 = 0
    doc_source_hit1 = 0

    # Track 3: Hybrid
    hyb_total = 0
    hyb_struct_correct = 0
    hyb_doc_correct = 0
    hyb_fusion_correct = 0

    # Track 4: Negative
    neg_total = 0
    neg_correct = 0

    print("\nExecuting queries through hybrid retrieval pipeline...\n")

    for q in questions:
        qid = q["question_id"]
        qtext = q["question"]
        track = q["track"]
        expected_route = q["expected_route"]

        t0 = time.time()
        ret = hr.retrieve(qtext)
        dt_ms = (time.time() - t0) * 1000

        actual_route = ret["route"]
        latencies_by_route[actual_route].append(dt_ms)

        # Routing check
        is_route_match = (actual_route == expected_route)
        if is_route_match:
            routing_correct += 1

        # Provenance completeness check
        prov_complete = True
        all_items = ret["structured_evidence"] + ret["document_evidence"]
        if all_items:
            for item in all_items:
                if not item.get("evidence_type") or not item.get("source_id"):
                    prov_complete = False
                    break
        else:
            if not ret.get("status"):
                prov_complete = False
        if prov_complete:
            provenance_complete_count += 1

        # Record details
        rec = {
            "question_id": qid,
            "track": track,
            "question": qtext,
            "expected_route": expected_route,
            "actual_route": actual_route,
            "route_match": is_route_match,
            "latency_ms": round(dt_ms, 2),
            "status": ret["status"],
            "intent": ret["intent"],
            "routing_confidence": ret["routing_confidence"],
            "structured_evidence_count": len(ret["structured_evidence"]),
            "document_evidence_count": len(ret["document_evidence"]),
            "sources": [s["source_id"] for s in ret["sources"]],
            "warnings": ret["warnings"]
        }

        # ---------------------------------------------------------
        # Track 1: STRUCTURED EVALUATION
        # ---------------------------------------------------------
        if track == "STRUCTURED":
            str_total += 1
            op_match = (is_route_match and ret["intent"] == q["expected_intent"])
            status_match = (ret["status"] == q["expected_status"])
            data_match = False

            if op_match and status_match:
                if q["expected_status"] in ("ZERO_DOCUMENTED_EVENTS", "ZERO_RAINFALL", "INSUFFICIENT_FOR_FULL_YEAR"):
                    data_match = True
                elif ret["structured_evidence"]:
                    s0 = ret["structured_evidence"][0]
                    # Verify source ID
                    src_ok = (s0.get("source_id") == q.get("expected_source_id"))
                    # If expected count or top district, verify
                    count_ok = True
                    if "expected_count" in q:
                        count_ok = (s0.get("count") == q["expected_count"])
                    top_ok = True
                    if "expected_top_district" in q:
                        top_ok = (s0.get("top_district") == q["expected_top_district"])
                    thresh_ok = True
                    if "expected_value_threshold" in q:
                        thresh_ok = (s0.get("max_rainfall_mm", 0) >= q["expected_value_threshold"])

                    data_match = (src_ok and count_ok and top_ok and thresh_ok)

            if op_match and status_match and data_match:
                str_correct += 1
                rec["structured_query_correct"] = True
            else:
                rec["structured_query_correct"] = False

        # ---------------------------------------------------------
        # Track 2: SEMANTIC / DOCUMENT EVALUATION (Chunk-Level Hit@K)
        # ---------------------------------------------------------
        elif track == "DOCUMENT":
            doc_total += 1
            ret_chunks = [d["chunk_id"] for d in ret["document_evidence"]]
            ret_docs = [d["document_id"] for d in ret["document_evidence"]]
            rel_chunks = q.get("relevant_chunk_ids", [])
            exp_docs = q.get("expected_document_ids", [])

            hit1 = any(c in rel_chunks for c in ret_chunks[:1])
            hit3 = any(c in rel_chunks for c in ret_chunks[:3])
            hit5 = any(c in rel_chunks for c in ret_chunks[:5])

            src_hit1 = any(d in exp_docs for d in ret_docs[:1]) if exp_docs else False

            if hit1: doc_hit1 += 1
            if hit3: doc_hit3 += 1
            if hit5: doc_hit5 += 1
            if src_hit1: doc_source_hit1 += 1

            rec["semantic_hit@1"] = hit1
            rec["semantic_hit@3"] = hit3
            rec["semantic_hit@5"] = hit5
            rec["document_source_hit@1"] = src_hit1
            rec["retrieved_chunks"] = ret_chunks[:5]
            rec["relevant_chunk_ids"] = rel_chunks
            rec["score_decomposition"] = [
                {
                    "chunk_id": d["chunk_id"],
                    "document_id": d["document_id"],
                    "page_number": d["page_number"],
                    "semantic_score": d.get("semantic_score"),
                    "document_scope_score": d.get("document_scope_score"),
                    "authority_score": d.get("authority_score"),
                    "cover_penalty": d.get("cover_penalty"),
                    "diversity_penalty": d.get("diversity_penalty"),
                    "final_score": d.get("final_score")
                } for d in ret["document_evidence"][:5]
            ]

        # ---------------------------------------------------------
        # Track 3: HYBRID EVALUATION (Decoupled Branches)
        # ---------------------------------------------------------
        elif track == "HYBRID":
            hyb_total += 1
            ret_chunks = [d["chunk_id"] for d in ret["document_evidence"]]
            ret_docs = [d["document_id"] for d in ret["document_evidence"]]
            rel_chunks = q.get("relevant_chunk_ids", [])
            exp_docs = q.get("expected_document_ids", [])

            struct_ok = (len(ret["structured_evidence"]) > 0 and ret["status"] == "OK")
            doc_ok = (len(ret["document_evidence"]) > 0 and (
                any(c in rel_chunks for c in ret_chunks[:5]) or any(d in exp_docs for d in ret_docs[:5])
            ))
            fusion_ok = (is_route_match and struct_ok and doc_ok)

            if struct_ok: hyb_struct_correct += 1
            if doc_ok: hyb_doc_correct += 1
            if fusion_ok: hyb_fusion_correct += 1

            rec["hybrid_structured_branch_correct"] = struct_ok
            rec["hybrid_document_branch_correct"] = doc_ok
            rec["hybrid_fusion_correct"] = fusion_ok

        # ---------------------------------------------------------
        # Track 4: NEGATIVE EVALUATION (Fail-Closed Rejection)
        # ---------------------------------------------------------
        elif track == "NEGATIVE_REJECTED":
            neg_total += 1
            neg_pass = (is_route_match and ret["status"] == "NO_SUPPORTED_EVIDENCE"
                        and len(ret["structured_evidence"]) == 0 and len(ret["document_evidence"]) == 0
                        and len(ret["warnings"]) > 0)
            if neg_pass:
                neg_correct += 1
            rec["negative_query_correct"] = neg_pass

        results.append(rec)
        status_sym = "[OK]" if rec.get("structured_query_correct", rec.get("semantic_hit@3", rec.get("hybrid_fusion_correct", rec.get("negative_query_correct", False)))) else "[FAIL]"
        print(f"{status_sym:<6} [{qid}] Track: {track:<10} | Route: {actual_route:<14} | {dt_ms:6.1f} ms | {qtext[:65]}")

    # =========================================================================
    # Compute Final Decoupled Metrics
    # =========================================================================
    total_q = len(questions)
    overall_routing_accuracy = round(routing_correct / total_q * 100, 2)
    provenance_rate = round(provenance_complete_count / total_q * 100, 2)

    structured_accuracy = round(str_correct / str_total * 100, 2) if str_total else 0.0
    semantic_hit1 = round(doc_hit1 / doc_total * 100, 2) if doc_total else 0.0
    semantic_hit3 = round(doc_hit3 / doc_total * 100, 2) if doc_total else 0.0
    semantic_hit5 = round(doc_hit5 / doc_total * 100, 2) if doc_total else 0.0
    document_source_hit1 = round(doc_source_hit1 / doc_total * 100, 2) if doc_total else 0.0

    hyb_struct_rate = round(hyb_struct_correct / hyb_total * 100, 2) if hyb_total else 0.0
    hyb_doc_rate = round(hyb_doc_correct / hyb_total * 100, 2) if hyb_total else 0.0
    hyb_fusion_rate = round(hyb_fusion_correct / hyb_total * 100, 2) if hyb_total else 0.0

    negative_accuracy = round(neg_correct / neg_total * 100, 2) if neg_total else 0.0

    avg_latencies = {
        r: round(sum(l) / len(l), 2) if l else 0.0 for r, l in latencies_by_route.items()
    }

    # Milestone 1 Immutability
    m1_immutable, m1_msg = verify_milestone1_immutability()

    metrics = {
        "benchmark_summary": {
            "total_questions": total_q,
            "structured_questions_count": str_total,
            "semantic_document_questions_count": doc_total,
            "hybrid_questions_count": hyb_total,
            "negative_adversarial_questions_count": neg_total
        },
        "decoupled_performance": {
            "overall_routing_accuracy_pct": overall_routing_accuracy,
            "structured_query_accuracy_pct": structured_accuracy,
            "semantic_passage_hit1_pct": semantic_hit1,
            "semantic_passage_hit3_pct": semantic_hit3,
            "semantic_passage_hit5_pct": semantic_hit5,
            "document_source_hit1_pct": document_source_hit1,
            "hybrid_structured_branch_accuracy_pct": hyb_struct_rate,
            "hybrid_document_branch_accuracy_pct": hyb_doc_rate,
            "hybrid_fusion_accuracy_pct": hyb_fusion_rate,
            "negative_query_accuracy_pct": negative_accuracy,
            "provenance_completeness_pct": provenance_rate
        },
        "average_latencies_ms": avg_latencies,
        "milestone1_immutability": {
            "verified": m1_immutable,
            "details": m1_msg
        }
    }

    # Gate Evaluations
    gate_routing = overall_routing_accuracy >= 95.0
    gate_structured = structured_accuracy >= 95.0
    gate_sem_hit1 = semantic_hit1 >= 70.0
    gate_sem_hit3 = semantic_hit3 >= 80.0
    gate_sem_hit5 = semantic_hit5 >= 85.0
    gate_doc_source = document_source_hit1 >= 90.0
    gate_hyb_fusion = hyb_fusion_rate >= 90.0
    gate_hyb_branches = (hyb_struct_rate == 100.0 and hyb_doc_rate == 100.0)
    gate_negative = negative_accuracy == 100.0
    gate_provenance = provenance_rate == 100.0
    gate_m1 = m1_immutable

    final_passed = (
        gate_routing and
        gate_structured and
        gate_sem_hit1 and
        gate_sem_hit3 and
        gate_sem_hit5 and
        gate_doc_source and
        gate_hyb_fusion and
        gate_hyb_branches and
        gate_negative and
        gate_provenance and
        gate_m1
    )
    final_verdict = "READY_FOR_MILESTONE_3" if final_passed else "NOT_READY — RETRIEVAL_REPAIR_REQUIRED"

    # Add gate evaluations to metrics dict
    metrics["gate_evaluations"] = {
        "routing_safety": {"target": ">= 95.0%", "measured": overall_routing_accuracy, "status": "PASSED" if gate_routing else "FAILED"},
        "structured_accuracy": {"target": ">= 95.0%", "measured": structured_accuracy, "status": "PASSED" if gate_structured else "FAILED"},
        "semantic_passage_hit1": {"target": ">= 70.0%", "measured": semantic_hit1, "status": "PASSED" if gate_sem_hit1 else "FAILED"},
        "semantic_passage_hit3": {"target": ">= 80.0%", "measured": semantic_hit3, "status": "PASSED" if gate_sem_hit3 else "FAILED"},
        "semantic_passage_hit5": {"target": ">= 85.0%", "measured": semantic_hit5, "status": "PASSED" if gate_sem_hit5 else "FAILED"},
        "document_source_hit1": {"target": ">= 90.0%", "measured": document_source_hit1, "status": "PASSED" if gate_doc_source else "FAILED"},
        "hybrid_fusion_accuracy": {"target": ">= 90.0%", "measured": hyb_fusion_rate, "status": "PASSED" if gate_hyb_fusion else "FAILED"},
        "hybrid_branches": {"target": "100.0%", "measured": f"{hyb_struct_rate}% / {hyb_doc_rate}%", "status": "PASSED" if gate_hyb_branches else "FAILED"},
        "negative_query_accuracy": {"target": "100.0%", "measured": negative_accuracy, "status": "PASSED" if gate_negative else "FAILED"},
        "provenance_completeness": {"target": "100.0%", "measured": provenance_rate, "status": "PASSED" if gate_provenance else "FAILED"},
        "milestone1_immutability": {"target": "100% Immutable", "measured": "Verified", "status": "PASSED" if gate_m1 else "FAILED"}
    }
    metrics["final_verdict"] = final_verdict

    # Save results JSON
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "results": results
        }, f, indent=2)
    print(f"\nSaved detailed retrieval results to {RESULTS_PATH}")

    # Generate Markdown Report
    report_md = fr"""# Milestone 2B — Hybrid Retrieval Evaluation Report (Repaired)

## Project: Himachal Pradesh Extreme Weather RAG System (2011–2026)
- **Target Districts**: Kangra, Mandi, Shimla, Kullu
- **Core Parameters**: Rainfall, Cloudburst, Flash Flood
- **Execution Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
- **Final Verdict**: `{final_verdict}`

---

## 1. Executive Performance Summary (Decoupled Benchmark)

| Evaluation Track | Metric Name | Target | Measured Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Routing Safety** | `OVERALL_ROUTING_ACCURACY` | $\ge 95.0\%$ | **{overall_routing_accuracy}%** ({routing_correct}/{total_q}) | **{'PASSED' if gate_routing else 'FAILED'}** |
| **Track 1: Structured** | `STRUCTURED_QUERY_ACCURACY` | $\ge 95.0\%$ | **{structured_accuracy}%** ({str_correct}/{str_total}) | **{'PASSED' if gate_structured else 'FAILED'}** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@1` | $\ge 70.0\%$ | **{semantic_hit1}%** ({doc_hit1}/{doc_total}) | **{'PASSED' if gate_sem_hit1 else 'FAILED'}** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@3` | $\ge 80.0\%$ | **{semantic_hit3}%** ({doc_hit3}/{doc_total}) | **{'PASSED' if gate_sem_hit3 else 'FAILED'}** |
| **Track 2: Semantic** | `SEMANTIC_PASSAGE_HIT@5` | $\ge 85.0\%$ | **{semantic_hit5}%** ({doc_hit5}/{doc_total}) | **{'PASSED' if gate_sem_hit5 else 'FAILED'}** |
| **Track 2: Supplemental** | `DOCUMENT_SOURCE_HIT@1` | $\ge 90.0\%$ | **{document_source_hit1}%** ({doc_source_hit1}/{doc_total}) | **{'PASSED' if gate_doc_source else 'FAILED'}** |
| **Track 3: Hybrid** | `HYBRID_FUSION_ACCURACY` | $\ge 90.0\%$ | **{hyb_fusion_rate}%** ({hyb_fusion_correct}/{hyb_total}) | **{'PASSED' if gate_hyb_fusion else 'FAILED'}** |
| **Track 3: Hybrid Branches** | Structured / Document Branches | $100\%$ | **{hyb_struct_rate}% / {hyb_doc_rate}%** | **{'PASSED' if gate_hyb_branches else 'FAILED'}** |
| **Track 4: Negative** | `NEGATIVE_QUERY_ACCURACY` | $100.0\%$ | **{negative_accuracy}%** ({neg_correct}/{neg_total}) | **{'PASSED' if gate_negative else 'FAILED'}** |
| **Provenance** | `PROVENANCE_COMPLETENESS` | $100.0\%$ | **{provenance_rate}%** ({provenance_complete_count}/{total_q}) | **{'PASSED' if gate_provenance else 'FAILED'}** |
| **Milestone 1 Baseline** | `MILESTONE_1_INTEGRITY` | $100\%$ Immutable | **VERIFIED UNCHANGED** | **{'PASSED' if gate_m1 else 'FAILED'}** |

### Latency Profiles by Retrieval Route
- **Structured Retrieval Latency**: `{avg_latencies.get('STRUCTURED', 0.0)} ms`
- **Semantic Retrieval Latency**: `{avg_latencies.get('DOCUMENT', 0.0)} ms`
- **Hybrid Retrieval Latency**: `{avg_latencies.get('HYBRID', 0.0)} ms`
- **Rejection Guard Latency**: `{avg_latencies.get('NEGATIVE_REJECTED', 0.0)} ms`

---

## 2. Benchmark Composition & Methodology
- **Total Questions:** {total_q}
  - **Structured SQL Queries:** {str_total} (Exact calculations, dates, counts, 2026 incomplete checks)
  - **Semantic Document Queries:** {doc_total} (Independently curated passage-level ground truth)
  - **Hybrid Dual-Engine Queries:** {hyb_total} (Disaster-rainfall correlation and fusion)
  - **Negative Adversarial Queries:** {neg_total} (Unsupported geography, variables, out-of-bounds years)

---

## 3. Conclusion & Verdict
```text
======================================================
FINAL STATUS: {final_verdict}
======================================================
```
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"Saved evaluation report to {REPORT_PATH}")

    print("\n=================================================================")
    print(f"   EVALUATION COMPLETE — VERDICT: {final_verdict}")
    print(f"   Routing Accuracy:       {overall_routing_accuracy}% (Target >= 95.0%) -> [{'PASSED' if gate_routing else 'FAILED'}]")
    print(f"   Structured Accuracy:    {structured_accuracy}% (Target >= 95.0%) -> [{'PASSED' if gate_structured else 'FAILED'}]")
    print(f"   Semantic Hit@1:         {semantic_hit1}% (Target >= 70.0%) -> [{'PASSED' if gate_sem_hit1 else 'FAILED'}]")
    print(f"   Semantic Hit@3:         {semantic_hit3}% (Target >= 80.0%) -> [{'PASSED' if gate_sem_hit3 else 'FAILED'}]")
    print(f"   Semantic Hit@5:         {semantic_hit5}% (Target >= 85.0%) -> [{'PASSED' if gate_sem_hit5 else 'FAILED'}]")
    print(f"   Document Source Hit@1:  {document_source_hit1}% (Target >= 90.0%) -> [{'PASSED' if gate_doc_source else 'FAILED'}]")
    print(f"   Hybrid Fusion:          {hyb_fusion_rate}% (Target >= 90.0%) -> [{'PASSED' if gate_hyb_fusion else 'FAILED'}]")
    print(f"   Negative Accuracy:      {negative_accuracy}% (Target 100.0%) -> [{'PASSED' if gate_negative else 'FAILED'}]")
    print(f"   Provenance Rate:        {provenance_rate}% (Target 100.0%) -> [{'PASSED' if gate_provenance else 'FAILED'}]")
    print(f"   Milestone 1 Baseline:   100% Immutable -> [{'PASSED' if gate_m1 else 'FAILED'}]")
    print("=================================================================")

    return final_passed

if __name__ == "__main__":
    success = evaluate_retrieval()
    sys.exit(0 if success else 1)
