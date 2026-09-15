"""
examples.py
Milestone 4: Curated Demonstration Queries

Provides representative test queries across all supported and unsupported modalities:
1. STRUCTURED: Maximum daily rainfall query (Kangra 2023)
2. STRUCTURED: Comparative district rainfall query (2023 peak)
3. DOCUMENT: Major cloudburst event lookup (Mandi)
4. HYBRID: Combined rainfall metrics + reported disaster impacts (Kullu 2023)
5. DOCUMENT NARRATIVE: PDNA recovery principles synthesis
6. NEGATIVE / REJECTION: Out-of-scope geography (Pune 2023)
"""

from typing import List, Dict

EXAMPLE_QUERIES: List[Dict[str, str]] = [
    {
        "id": "ex_struct_max_rain",
        "category": "STRUCTURED — Max Daily Rainfall",
        "query": "What was the maximum rainfall in Kangra in 2023?",
        "expected_route": "STRUCTURED",
        "description": "Calculates the peak single-day spatial rainfall from IMD gridded dataset."
    },
    {
        "id": "ex_struct_highest_dist",
        "category": "STRUCTURED — District Comparison",
        "query": "Which district had the highest rainfall in 2023?",
        "expected_route": "STRUCTURED",
        "description": "Compares annual and extreme rainfall across the 4 authorized target districts."
    },
    {
        "id": "ex_doc_cloudburst",
        "category": "DOCUMENT / EVENT — Cloudburst History",
        "query": "What major cloudburst events occurred in Mandi?",
        "expected_route": "DOCUMENT",
        "description": "Searches official disaster memorandums and HPSDMA records for Mandi cloudburst events."
    },
    {
        "id": "ex_hybrid_kullu",
        "category": "HYBRID — Rainfall + Reported Impacts",
        "query": "Was the July 2023 Kullu disaster associated with extreme rainfall, and what impacts were reported?",
        "expected_route": "HYBRID",
        "description": "Fuses quantitative July 2023 Kullu rainfall with official PDNA impact reports."
    },
    {
        "id": "ex_doc_pdna",
        "category": "DOCUMENT NARRATIVE — PDNA Recovery",
        "query": "What overall recovery and reconstruction principles does the PDNA recommend for building back better?",
        "expected_route": "DOCUMENT",
        "description": "Synthesizes multi-chunk policy guidance from the 2023 Post-Disaster Needs Assessment."
    },
    {
        "id": "ex_negative_pune",
        "category": "NEGATIVE — Out-of-Scope Geography",
        "query": "What was the rainfall in Pune in 2023?",
        "expected_route": "NEGATIVE_REJECTED",
        "description": "Demonstrates deterministic refusal for queries outside the 4 authorized HP districts."
    }
]


def get_example_queries() -> List[Dict[str, str]]:
    """Returns the list of curated demonstration queries."""
    return EXAMPLE_QUERIES
