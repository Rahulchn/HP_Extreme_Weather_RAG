"""
test_router_safety.py
Milestone 2B: Standalone Adversarial Test Suite for Query Router Safety & Parameter Protection

Validates:
1. Geographic Adversarial Cases:
   - Pune, Delhi, Mumbai, Chandigarh, Dehradun, Bilaspur, Solan, and an arbitrary invented district name.
   - Expected: NO_SUPPORTED_EVIDENCE (NEGATIVE_REJECTED).
2. Parameter Adversarial Cases:
   - wind speed, temperature, solar radiation, avalanche, earthquake magnitude, snowfall depth.
   - Expected: NO_SUPPORTED_EVIDENCE (NEGATIVE_REJECTED).
3. Entity-Parameter Collision Cases:
   - unsupported parameter + valid date (e.g. wind speed in Shimla on 2023-07-09).
   - unsupported parameter + valid district (e.g. solar radiation in Kangra).
   - unsupported parameter + "maximum" (e.g. maximum temperature in Mandi).
   - unsupported parameter + "how many" (e.g. how many avalanche accidents in Kullu).
   - unsupported parameter + event terminology (e.g. earthquake disaster in Kangra).
   - Expected: NO_SUPPORTED_EVIDENCE (NEGATIVE_REJECTED).
4. Geographic State Distinction Cases (Correction 1):
   - Case 1 (Supported): Kangra max rainfall -> returns Kangra.
   - Case 2 (No geography specified): 2023 max rainfall -> allowed state scope.
   - Case 3 (Explicit unsupported): Pune max rainfall -> NO_SUPPORTED_EVIDENCE (never converts to Case 2).
5. Landslide Scope Safety (Correction 2):
   - Landslides and infrastructure impact route strictly to DOCUMENT and NEVER execute structured SQL rainfall queries.
6. Valid Controls:
   - Supported rainfall, flash flood, cloudburst, GSI, PDNA, and 2026 queries route normally.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import scripts.hybrid_retriever as hr

def run_adversarial_suite():
    print("=================================================================")
    print("   MILESTONE 2B: ADVERSARIAL ROUTER SAFETY TEST SUITE")
    print("=================================================================\n")

    total_tests = 0
    passed_tests = 0
    failures = []

    # -------------------------------------------------------------
    # 1. Geographic Adversarial Cases
    # -------------------------------------------------------------
    geo_cases = [
        ("Out-of-scope Pune", "What was the maximum rainfall in Pune in 2023?"),
        ("Out-of-scope Delhi", "What was the rainfall in Delhi in August 2023?"),
        ("Out-of-scope Mumbai", "How many cloudburst events occurred in Mumbai in 2023?"),
        ("Out-of-scope Chandigarh", "What was the flash flood damage in Chandigarh in July 2023?"),
        ("Out-of-scope Dehradun", "Describe the extreme rainfall recorded in Dehradun in 2021."),
        ("Out-of-scope Bilaspur", "What was the total rainfall in Bilaspur district in 2022?"),
        ("Out-of-scope Solan", "How many flash floods occurred in Solan in 2023?"),
        ("Invented district Atlantis", "What was the peak rainfall in Atlantis in 2023?"),
        ("Invented district Xandaria", "How many cloudbursts were recorded in Xandaria district in 2021?")
    ]

    print("--- 1. Geographic Adversarial Cases ---")
    for name, query in geo_cases:
        total_tests += 1
        res = hr.retrieve(query)
        is_pass = (res["route"] == "NEGATIVE_REJECTED" and res["status"] == "NO_SUPPORTED_EVIDENCE" 
                   and len(res["structured_evidence"]) == 0 and len(res["document_evidence"]) == 0)
        if is_pass:
            passed_tests += 1
            print(f"  [PASS] {name:<28} -> NEGATIVE_REJECTED | NO_SUPPORTED_EVIDENCE")
        else:
            failures.append((name, query, f"Expected NEGATIVE_REJECTED, got {res['route']} ({res['status']})"))
            print(f"  [FAIL] {name:<28} -> {res['route']} ({res['status']})")

    # -------------------------------------------------------------
    # 2. Parameter Adversarial Cases
    # -------------------------------------------------------------
    param_cases = [
        ("Unsupported Wind Speed", "What was the wind speed in Shimla in July 2023?"),
        ("Unsupported Temperature", "What was the maximum temperature recorded in Mandi in 2023?"),
        ("Unsupported Solar Radiation", "What was the solar radiation in Kangra in July 2023?"),
        ("Unsupported Avalanche", "How many avalanche accidents occurred in Kullu in 2022?"),
        ("Unsupported Earthquake", "What was the earthquake magnitude in Kangra on 2023-07-09?"),
        ("Unsupported Snowfall Depth", "What was the snowfall depth in Manali in January 2023?"),
        ("Unsupported Heat Wave", "Describe the catastrophic heatwave in Shimla in 2023."),
        ("Unsupported Relative Humidity", "What was the average relative humidity in Mandi in 2022?")
    ]

    print("\n--- 2. Parameter Adversarial Cases ---")
    for name, query in param_cases:
        total_tests += 1
        res = hr.retrieve(query)
        is_pass = (res["route"] == "NEGATIVE_REJECTED" and res["status"] == "NO_SUPPORTED_EVIDENCE"
                   and len(res["structured_evidence"]) == 0 and len(res["document_evidence"]) == 0)
        if is_pass:
            passed_tests += 1
            print(f"  [PASS] {name:<28} -> NEGATIVE_REJECTED | NO_SUPPORTED_EVIDENCE")
        else:
            failures.append((name, query, f"Expected NEGATIVE_REJECTED, got {res['route']} ({res['status']})"))
            print(f"  [FAIL] {name:<28} -> {res['route']} ({res['status']})")

    # -------------------------------------------------------------
    # 3. Collision Cases (Unsupported Parameter + Valid Entity / Date / Operator)
    # -------------------------------------------------------------
    collision_cases = [
        ("Param + Valid Date", "What was the wind speed in Shimla on 2023-07-09?"),
        ("Param + Valid District", "What was the solar radiation in Kangra in August 2023?"),
        ("Param + 'Maximum' operator", "What was the maximum temperature in Mandi in 2023?"),
        ("Param + 'How many' operator", "How many avalanche casualties were recorded in Kullu in 2022?"),
        ("Param + Disaster keyword", "Describe the earthquake devastation in Kangra on 2023-07-09.")
    ]

    print("\n--- 3. Entity-Parameter Collision Cases ---")
    for name, query in collision_cases:
        total_tests += 1
        res = hr.retrieve(query)
        is_pass = (res["route"] == "NEGATIVE_REJECTED" and res["status"] == "NO_SUPPORTED_EVIDENCE"
                   and len(res["structured_evidence"]) == 0 and len(res["document_evidence"]) == 0)
        if is_pass:
            passed_tests += 1
            print(f"  [PASS] {name:<28} -> NEGATIVE_REJECTED | NO_SUPPORTED_EVIDENCE")
        else:
            failures.append((name, query, f"Expected NEGATIVE_REJECTED, got {res['route']} ({res['status']})"))
            print(f"  [FAIL] {name:<28} -> {res['route']} ({res['status']})")

    # -------------------------------------------------------------
    # 4. Geographic State Distinction Regression (Correction 1)
    # -------------------------------------------------------------
    print("\n--- 4. Geographic State Distinction Regression ---")
    # Case 1: Valid constrained query (Kangra)
    total_tests += 1
    c1 = hr.retrieve("What was the maximum rainfall in Kangra in 2023?")
    c1_pass = (c1["route"] == "STRUCTURED" and c1["status"] == "OK" and c1["detected_entities"]["district"] == "Kangra")
    if c1_pass:
        passed_tests += 1
        print("  [PASS] Case 1 (Supported Kangra)    -> STRUCTURED | district=Kangra")
    else:
        failures.append(("Case 1", "Kangra max rainfall", f"Expected STRUCTURED Kangra, got {c1['route']}"))
        print(f"  [FAIL] Case 1 (Supported Kangra)    -> {c1['route']}")

    # Case 2: No district specified (State-wide aggregation valid)
    total_tests += 1
    c2 = hr.retrieve("What was the maximum rainfall in 2023?")
    c2_pass = (c2["route"] == "STRUCTURED" and c2["status"] == "OK" and c2["detected_entities"]["district"] is None)
    if c2_pass:
        passed_tests += 1
        print("  [PASS] Case 2 (No geography spec)  -> STRUCTURED | district=None (State-wide)")
    else:
        failures.append(("Case 2", "2023 max rainfall", f"Expected STRUCTURED, got {c2['route']}"))
        print(f"  [FAIL] Case 2 (No geography spec)  -> {c2['route']}")

    # Case 3: Explicit unsupported geography (Pune) MUST NOT convert to Case 2
    total_tests += 1
    c3 = hr.retrieve("What was the maximum rainfall in Pune in 2023?")
    c3_pass = (c3["route"] == "NEGATIVE_REJECTED" and c3["status"] == "NO_SUPPORTED_EVIDENCE" 
               and len(c3["structured_evidence"]) == 0)
    if c3_pass:
        passed_tests += 1
        print("  [PASS] Case 3 (Unsupported Pune)   -> NEGATIVE_REJECTED (Did NOT fall back to Case 2)")
    else:
        failures.append(("Case 3", "Pune max rainfall", f"FAILED: Pune fell back to {c3['route']}!"))
        print(f"  [FAIL] Case 3 (Unsupported Pune)   -> FAILED: Fell back to {c3['route']}!")

    # -------------------------------------------------------------
    # 5. Landslide Scope Safety (Correction 2)
    # -------------------------------------------------------------
    print("\n--- 5. Landslide Scope Safety ---")
    total_tests += 1
    ls_q = "How did landslides affect roads in Mandi in 2023?"
    ls_res = hr.retrieve(ls_q)
    ls_pass = (ls_res["route"] == "DOCUMENT" and ls_res["status"] == "OK" 
               and len(ls_res["structured_evidence"]) == 0 and len(ls_res["document_evidence"]) > 0)
    if ls_pass:
        passed_tests += 1
        print("  [PASS] Landslide Narrative Scope    -> DOCUMENT | 0 SQL Structured rows executed")
    else:
        failures.append(("Landslide Scope", ls_q, f"Expected DOCUMENT with 0 structured rows, got {ls_res['route']} with {len(ls_res['structured_evidence'])} rows"))
        print(f"  [FAIL] Landslide Narrative Scope    -> {ls_res['route']} ({len(ls_res['structured_evidence'])} struct rows)")

    # -------------------------------------------------------------
    # 6. Valid Controls
    # -------------------------------------------------------------
    valid_cases = [
        ("Valid Max Rain Kangra", "What was the maximum rainfall in Kangra in 2023?", "STRUCTURED"),
        ("Valid Date Rain Shimla", "What was the rainfall in Shimla on 2023-07-09?", "STRUCTURED"),
        ("Valid Flash Flood Kullu", "How many documented flash floods occurred in Kullu between 2011 and 2025?", "STRUCTURED"),
        ("Valid Cloudburst Summary", "Which district had the most documented cloudburst events?", "STRUCTURED"),
        ("Valid Kotrupi GSI", "What geological factors triggered the 2017 Kotrupi Mandi disaster according to GSI?", "DOCUMENT"),
        ("Valid PDNA Damage", "What does HPSDMA report about infrastructure damage during the 2023 monsoon?", "DOCUMENT"),
        ("Valid Hybrid Kullu 2023", "Was the July 2023 Kullu disaster associated with extreme rainfall?", "HYBRID"),
        ("Valid 2026 Telemetry Status", "What information is currently available for 2026?", "HYBRID")
    ]

    print("\n--- 6. Valid Controls ---")
    for name, query, exp_route in valid_cases:
        total_tests += 1
        res = hr.retrieve(query)
        is_pass = (res["route"] == exp_route and res["status"] in ("OK", "ZERO_RAINFALL", "ZERO_DOCUMENTED_EVENTS"))
        if is_pass:
            passed_tests += 1
            print(f"  [PASS] {name:<28} -> {res['route']} | Status: {res['status']}")
        else:
            failures.append((name, query, f"Expected {exp_route}, got {res['route']} ({res['status']})"))
            print(f"  [FAIL] {name:<28} -> Expected {exp_route}, got {res['route']}")

    print("\n=================================================================")
    print(f"   SUITE RESULTS: {passed_tests}/{total_tests} PASSED ({passed_tests/total_tests*100:.1f}%)")
    print("=================================================================")

    if failures:
        print("\nFailures Encountered:")
        for f in failures:
            print(f" - {f[0]}: {f[2]}")
        return False
    return True

if __name__ == "__main__":
    success = run_adversarial_suite()
    sys.exit(0 if success else 1)
