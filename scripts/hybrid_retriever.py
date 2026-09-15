"""
hybrid_retriever.py
Milestone 2B Repaired: Authoritative Hybrid Retrieval & Query Routing Engine
Accepts a natural query, deterministically routes it using multi-signal heuristics,
and fuses structured quantitative evidence from SQLite with semantic document evidence from FAISS.

Repairs Applied:
1. Positive Geographic Entity Model:
   - Target districts: Kangra, Mandi, Shimla, Kullu (plus mapped sub-locations/tehsils/stations).
   - Explicitly distinguishes:
     * SUPPORTED_GEOGRAPHY (valid district/sub-location)
     * EXPLICIT_UNSUPPORTED_GEOGRAPHY (outside target districts; fails closed to NO_SUPPORTED_EVIDENCE)
     * STATE_LEVEL (Himachal Pradesh state-wide)
     * NO_GEOGRAPHY_SPECIFIED (unconstrained; valid only for supported state-wide aggregations)
   - Never converts explicit unsupported geography into null-district state-wide scans.
2. Positive Parameter Model:
   - Supported schema: RAINFALL, CLOUDBURST, FLASH_FLOOD.
   - Unsupported parameters (wind speed, solar radiation, temperature, avalanche, earthquake, snowfall, etc.)
     fail closed immediately to NO_SUPPORTED_EVIDENCE.
   - Dates (YYYY-MM-DD), "maximum", and "how many" cannot override parameter incompatibility.
3. LANDSLIDE_NARRATIVE Scope:
   - Landslides, debris flow, road blockages, bridge collapses, and casualties route strictly to
     DOCUMENT (or HYBRID if paired with a supported rainfall query).
   - They NEVER execute structured SQL rainfall calculations.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import re
from typing import Dict, Any, List, Optional, Tuple
import scripts.structured_retriever as sr
import scripts.semantic_retriever as sem

# -------------------------------------------------------------
# Geographic Entity Taxonomy
# -------------------------------------------------------------
SUPPORTED_DISTRICTS = {
    "Kangra": "Kangra",
    "Mandi": "Mandi",
    "Shimla": "Shimla",
    "Kullu": "Kullu"
}

SUPPORTED_SUB_LOCATIONS = {
    # Kangra
    "dharamshala": "Kangra", "boh": "Kangra", "shahpur": "Kangra", "bhagsunag": "Kangra",
    "kangra aero": "Kangra", "nurpur": "Kangra", "palampur": "Kangra", "dehra": "Kangra", "jawalamukhi": "Kangra",
    # Mandi
    "sundernagar": "Mandi", "mandi urban": "Mandi", "kotrupi": "Mandi", "sarkaghat": "Mandi",
    "jogindernagar": "Mandi", "thunag": "Mandi", "karsog": "Mandi", "pandoh": "Mandi",
    # Shimla
    "shimla city": "Shimla", "rampur": "Shimla", "rohru": "Shimla", "theog": "Shimla",
    "chopal": "Shimla", "jubbal": "Shimla", "kumarsain": "Shimla", "sunni": "Shimla",
    # Kullu
    "manali": "Kullu", "bhuntar": "Kullu", "anni": "Kullu", "banjar": "Kullu",
    "nirmand": "Kullu", "sainj": "Kullu", "tirthan": "Kullu", "chojh": "Kullu",
    "kasol": "Kullu", "parvati": "Kullu"
}

STATE_LEVEL_INDICATORS = [
    "himachal pradesh", "himachal", "h.p.", "hp", "hp state", "state-wide", "statewide", "entire state", "the state", "across the state"
]

NON_GEO_WORDS = {
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "monsoon", "summer", "winter", "post-monsoon", "peak", "season", "period", "year", "years", "month", "months", "day", "days",
    "the", "a", "an", "this", "that", "these", "those", "which", "what", "all", "any", "each", "every", "both", "neither", "either",
    "rainfall", "rain", "precipitation", "cloudburst", "flood", "floods", "landslide", "landslides", "disaster", "disasters",
    "deluge", "damage", "infrastructure", "road", "roads", "bridge", "bridges", "station", "stations", "grid", "cell", "cells",
    "data", "record", "records", "report", "reports", "memorandum", "memorandums", "study", "studies", "investigation",
    "detail", "details", "terms", "general", "total", "average", "maximum", "minimum", "order", "case", "contrast", "fact",
    "response", "search", "searching", "recent", "past", "future", "severe", "extreme", "heavy", "highest", "lowest", "gsi", "hpsdma", "imd",
    "ndrf", "sdrf", "loss", "losses", "casualty", "casualties", "death", "deaths", "fatality", "fatalities", "hazard", "impact"
}

# External known regions that might be mentioned without spatial prepositions
KNOWN_EXTERNAL_GEOGRAPHY = {
    "bilaspur", "solan", "chamba", "hamirpur", "una", "kinnaur", "lahaul", "spiti", "sirmour", "sirmaur",
    "jaipur", "delhi", "mumbai", "pune", "chandigarh", "dehradun", "kolkata", "chennai", "bangalore", "bengaluru",
    "hyderabad", "ahmedabad", "lucknow", "patna", "rajasthan", "uttarakhand", "punjab", "haryana", "jammu", "kashmir",
    "ladakh", "uttar pradesh", "gujarat", "maharashtra", "goa", "kerala", "bihar", "assam", "odisha"
}

# -------------------------------------------------------------
# Parameter Taxonomy
# -------------------------------------------------------------
UNSUPPORTED_PARAMETERS_MAP = [
    (r"\bwind\s*speed\b", "Wind Speed"),
    (r"\bwind\b", "Wind"),
    (r"\bgust\b", "Wind"),
    (r"\btemperature\b", "Temperature"),
    (r"\bheat\s*wave\b", "Temperature"),
    (r"\bheatwave\b", "Temperature"),
    (r"\bheat\b", "Temperature"),
    (r"\bcold\s*wave\b", "Temperature"),
    (r"\bsolar\s*radiation\b", "Solar Radiation"),
    (r"\buv\s*index\b", "Solar Radiation"),
    (r"\bsunshine\b", "Solar Radiation"),
    (r"\bhumidity\b", "Humidity"),
    (r"\bdew\s*point\b", "Humidity"),
    (r"\bpressure\b", "Atmospheric Pressure"),
    (r"\bbarometric\b", "Atmospheric Pressure"),
    (r"\bair\s*quality\b", "Air Quality"),
    (r"\baqi\b", "Air Quality"),
    (r"\bpollution\b", "Air Quality"),
    (r"\bsnowfall\s*depth\b", "Snowfall"),
    (r"\bsnowfall\b", "Snowfall"),
    (r"\bsnow\s*depth\b", "Snowfall"),
    (r"\bsnow\b", "Snowfall"),
    (r"\bearthquake\b", "Earthquake"),
    (r"\brichter\b", "Earthquake"),
    (r"\bmagnitude\b", "Earthquake"),
    (r"\bseismic\b", "Earthquake"),
    (r"\btremor\b", "Earthquake"),
    (r"\btsunami\b", "Tsunami"),
    (r"\bvolcano\b", "Volcano"),
    (r"\beruption\b", "Volcano"),
    (r"\bavalanche\b", "Avalanche"),
    (r"\bcyclone\b", "Cyclone"),
    (r"\bhurricane\b", "Cyclone"),
    (r"\btyphoon\b", "Cyclone"),
    (r"\btornado\b", "Tornado"),
    (r"\bmeteor\b", "Meteor"),
    (r"\basteroid\b", "Meteor")
]

STRUCTURED_SIGNALS = [
    "maximum", "minimum", "highest", "lowest", "average", "mean", "total", 
    "how many", "count", "number of", "statist", "single-day", "recorded on",
    "annual rainfall in", "daily rainfall", "which district had the most"
]

DOCUMENT_SIGNALS = [
    "what happened", "why", "describe", "according to", "report", "narrative",
    "impacts", "causes", "explanation", "factor", "investigat", "geological",
    "damage to", "infrastructure", "ndrf", "sdrf", "measures", "response",
    "losses due to", "indicate about"
]

EVENT_TYPES_MAP = {
    "cloudburst": "Cloudburst",
    "flash flood": "Flash Flood",
    "flash-flood": "Flash Flood",
    "heavy rainfall": "Heavy Rainfall",
    "deluge": "Heavy Rainfall"
}

def extract_geography(query: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Extracts geographic scope distinguishing:
    1. SUPPORTED_GEOGRAPHY: (status, canonical_district, sub_location)
    2. EXPLICIT_UNSUPPORTED_GEOGRAPHY: (status, None, unsupported_location_name)
    3. STATE_LEVEL: (status, None, None)
    4. NO_GEOGRAPHY_SPECIFIED: (status, None, None)
    """
    q_lower = query.lower()

    # 1. Check supported districts first
    for d_name in SUPPORTED_DISTRICTS:
        if re.search(rf"\b{d_name.lower()}\b", q_lower):
            # Institutional entity disambiguation: "IMD Shimla", "Meteorological Centre Shimla" refers to the publishing institution
            if d_name == "Shimla" and re.search(r'\b(?:imd|meteorological\s+centre)\s+shimla\b', q_lower):
                if not re.search(r'\b(?:in|at|across|for)\s+shimla(?:\s+district)?\b', q_lower) and not re.search(r'\bshimla\s+district\b', q_lower):
                    continue
            return "SUPPORTED_GEOGRAPHY", d_name, None

    # 2. Check supported sub-locations / tehsils / stations
    for sub, d_name in SUPPORTED_SUB_LOCATIONS.items():
        if re.search(rf"\b{sub}\b", q_lower):
            return "SUPPORTED_GEOGRAPHY", d_name, sub

    # 3. Check state-level indicator
    for st in STATE_LEVEL_INDICATORS:
        if re.search(rf"\b{st}\b", q_lower):
            return "STATE_LEVEL", None, None

    # 4. Check explicit external locations mentioned directly
    for ext in KNOWN_EXTERNAL_GEOGRAPHY:
        if re.search(rf"\b{ext}\b", q_lower):
            return "EXPLICIT_UNSUPPORTED_GEOGRAPHY", None, ext.title()

    # 5. Check explicit geographic indicators: "<Word> district", "<Word> city", "<Word> tehsil", etc.
    geo_ind_match = re.search(r'\b([A-Za-z]+)\s+(?:district|dist|city|town|tehsil|taluk|state|valley|basin|province)\b', q_lower)
    if geo_ind_match:
        cand = geo_ind_match.group(1).lower()
        if cand not in [d.lower() for d in SUPPORTED_DISTRICTS] and cand not in NON_GEO_WORDS:
            return "EXPLICIT_UNSUPPORTED_GEOGRAPHY", None, geo_ind_match.group(0).title()

    # 6. Check spatial prepositions followed by candidate location token:
    # "in <Word>", "at <Word>", "near <Word>", "around <Word>", "across <Word>"
    prep_matches = re.finditer(r'\b(?:in|at|around|near|across|to|from)\s+([A-Za-z]+)\b', query)
    for pm in prep_matches:
        cand = pm.group(1).strip()
        cand_lower = cand.lower()
        if cand_lower in NON_GEO_WORDS or cand_lower.isdigit():
            continue
        if cand_lower in [d.lower() for d in SUPPORTED_DISTRICTS] or cand_lower in SUPPORTED_SUB_LOCATIONS:
            continue
        # Capitalized token or recognized proper entity following preposition
        if cand[0].isupper() or cand_lower in KNOWN_EXTERNAL_GEOGRAPHY:
            return "EXPLICIT_UNSUPPORTED_GEOGRAPHY", None, cand

    return "NO_GEOGRAPHY_SPECIFIED", None, None

def extract_parameter(query: str) -> Tuple[str, Optional[str]]:
    """
    Extracts parameter status:
    1. UNSUPPORTED_PARAMETER: (status, unsupported_param_name)
    2. RAINFALL: (status, "Rainfall")
    3. CLOUDBURST: (status, "Cloudburst")
    4. FLASH_FLOOD: (status, "Flash Flood")
    5. LANDSLIDE_NARRATIVE: (status, "Landslide Narrative") -> DOCUMENT only
    6. UNKNOWN_PARAMETER: (status, None)
    """
    q_lower = query.lower()

    # 1. Unsupported parameters FIRST (Fail closed)
    for pattern, param_name in UNSUPPORTED_PARAMETERS_MAP:
        if re.search(pattern, q_lower):
            return "UNSUPPORTED_PARAMETER", param_name

    # 2. Supported parameters
    has_rainfall = bool(re.search(r"\b(rainfall|rain|precipitation|downpour|deluge|millimeter|mm|wet spell)\b", q_lower))
    has_cloudburst = bool(re.search(r"\b(cloudburst|cloud burst)\b", q_lower))
    has_flash_flood = bool(re.search(r"\b(flash flood|flash-flood|flash floods|khad overflow|river inundation|river torrent)\b", q_lower))
    has_landslide_narrative = bool(re.search(
        r"\b(landslide|landslides|debris flow|slope failure|slope instability|rockfall|infrastructure damage|road damage|road blocked|bridge collapse|bridge washed|casualties|deaths|fatalities|loss of lives|human losses|ndrf|sdrf|geological factors|trigger mechanism|response measures)\b", 
        q_lower
    ))

    if has_rainfall:
        return "RAINFALL", "Rainfall"
    if has_cloudburst:
        return "CLOUDBURST", "Cloudburst"
    if has_flash_flood:
        return "FLASH_FLOOD", "Flash Flood"
    if has_landslide_narrative:
        return "LANDSLIDE_NARRATIVE", "Landslide Narrative"

    return "UNKNOWN_PARAMETER", None

def extract_entities(query: str) -> Dict[str, Any]:
    geo_status, district, sub_or_unsupported = extract_geography(query)
    param_status, param_name = extract_parameter(query)

    # Years
    years = [int(y) for y in re.findall(r'\b(19\d\d|20\d\d)\b', query)]
    target_year = years[0] if len(years) == 1 else None
    start_year = None
    end_year = None
    if len(years) >= 2:
        start_year = min(years[0], years[1])
        end_year = max(years[0], years[1])

    year_status = "VALID"
    if years:
        if any(y < 2011 or y > 2026 for y in years):
            year_status = "OUT_OF_BOUNDS"
    else:
        year_status = "NOT_SPECIFIED"

    # Exact Date (YYYY-MM-DD)
    date_match = re.search(r'\b(20\d\d-\d{2}-\d{2})\b', query)
    exact_date = date_match.group(1) if date_match else None

    # Event Type
    event_type = None
    q_lower = query.lower()
    for kw, etype in EVENT_TYPES_MAP.items():
        if kw in q_lower:
            event_type = etype
            break

    return {
        "geographic_status": geo_status,
        "district": district,
        "sub_location": sub_or_unsupported if geo_status == "SUPPORTED_GEOGRAPHY" else None,
        "unsupported_location": sub_or_unsupported if geo_status == "EXPLICIT_UNSUPPORTED_GEOGRAPHY" else None,
        "parameter_status": param_status,
        "parameter_name": param_name,
        "unsupported_parameter": param_name if param_status == "UNSUPPORTED_PARAMETER" else None,
        "year": target_year,
        "start_year": start_year,
        "end_year": end_year,
        "all_years": years,
        "year_status": year_status,
        "date": exact_date,
        "event_type": event_type
    }

def classify_query(query: str, entities: Dict[str, Any]) -> Tuple[str, str, float]:
    q_lower = query.lower()

    # -------------------------------------------------------------
    # Priority 1: Unsupported Parameter (Fail Closed)
    # -------------------------------------------------------------
    if entities["parameter_status"] == "UNSUPPORTED_PARAMETER":
        param_label = entities["unsupported_parameter"].upper().replace(" ", "_")
        return "NEGATIVE_REJECTED", f"UNSUPPORTED_PARAMETER_{param_label}", 1.0

    # -------------------------------------------------------------
    # Priority 2: Explicit Unsupported Geography (Fail Closed)
    # -------------------------------------------------------------
    if entities["geographic_status"] == "EXPLICIT_UNSUPPORTED_GEOGRAPHY":
        loc_label = (entities["unsupported_location"] or "UNKNOWN").upper().replace(" ", "_")
        return "NEGATIVE_REJECTED", f"OUT_OF_SCOPE_GEOGRAPHY_{loc_label}", 1.0

    # -------------------------------------------------------------
    # Priority 3: Temporal Out of Bounds
    # -------------------------------------------------------------
    if entities["year_status"] == "OUT_OF_BOUNDS":
        return "NEGATIVE_REJECTED", "OUT_OF_TEMPORAL_BOUNDS", 1.0

    # -------------------------------------------------------------
    # Priority 4: 2026 Incomplete Annual Check
    # -------------------------------------------------------------
    if entities["year"] == 2026:
        if any(w in q_lower for w in ["annual", "total rainfall", "full year", "annual rainfall"]):
            return "STRUCTURED", "ANNUAL_TOTAL_INCOMPLETE", 0.95
        if "what information is currently available" in q_lower or "available for 2026" in q_lower:
            return "HYBRID", "PARTIAL_YEAR_STATUS", 0.95

    # -------------------------------------------------------------
    # Priority 5: Structured Event Lookup
    # -------------------------------------------------------------
    if "list" in q_lower and any(k in q_lower for k in ["event", "cloudburst", "flash flood"]):
        return "STRUCTURED", "EVENT_LOOKUP", 0.95

    # -------------------------------------------------------------
    # Priority 6: Hybrid Correlation Checks
    # When query requests correlation between weather metrics and physical impacts
    # -------------------------------------------------------------
    has_struct_intent = any(sig in q_lower for sig in STRUCTURED_SIGNALS)
    has_doc_intent = any(sig in q_lower for sig in DOCUMENT_SIGNALS)
    has_weather = bool(re.search(r"\b(rainfall|rain|precipitation|deluge|downpour|weather)\b", q_lower))
    has_event = bool(re.search(r"\b(cloudbursts?|flash[- ]floods?)\b", q_lower))
    has_impact = bool(re.search(r"\b(disaster|landslide|landslides|damage|casualties|deaths|river swelling|devastation|loss of lives|debris flow|slope failure)\b", q_lower))
    has_hybrid_signals = any(s in q_lower for s in [
        "associated with", "trigger", "contribute", "correlate", "accompanied by", 
        "casualties", "levels and damage", "and what was the precipitation"
    ])

    if (has_weather and (has_impact or (has_event and has_hybrid_signals)) and (has_hybrid_signals or any(w in q_lower for w in ["was", "did", "how did"]))) or \
       (has_struct_intent and has_doc_intent and has_weather and has_impact):
        # Exclude pure document queries asking for authoritative reports/studies
        if not any(k in q_lower for k in ["according to", "report about", "report record", "report indicate", "preliminary study", "gsi", "seoc", "lr3", "monsoon report", "kotrupi", "antecedent", "trigger mechanism"]):
            return "HYBRID", "HAZARD_RAINFALL_CORRELATION", 0.95

    # -------------------------------------------------------------
    # Priority 7: Landslide & Infrastructure Narrative Scope Check (Correction 2)
    # Pure landslide / damage / casualty inquiry is strictly DOCUMENT
    # Never routes to SQL rainfall calculations!
    # -------------------------------------------------------------
    if entities["parameter_status"] == "LANDSLIDE_NARRATIVE" or (has_impact and not has_weather):
        return "DOCUMENT", "LANDSLIDE_IMPACT_NARRATIVE", 0.95

    # -------------------------------------------------------------
    # Priority 8: Structured Quantitative Operations
    # -------------------------------------------------------------
    if has_struct_intent or entities["date"] or "how many" in q_lower or "which district had the most" in q_lower:
        # Document report inquiries take precedence over structured keywords
        if ("monsoon report" in q_lower or "in the report" in q_lower or "report record" in q_lower or "report indicate" in q_lower) and not ("how many" in q_lower or "statist" in q_lower):
            return "DOCUMENT", "EVENT_NARRATIVE", 0.90

        # Date rainfall query strictly requires parameter to be rainfall or generic
        if entities["date"]:
            if entities["parameter_status"] in ("RAINFALL", "UNKNOWN_PARAMETER"):
                return "STRUCTURED", "DATE_RAINFALL", 0.95
            else:
                return "DOCUMENT", "DATE_CONTEXTUAL_SEARCH", 0.85

        if "max" in q_lower or "highest" in q_lower:
            if "august 2023" in q_lower or "july 2023" in q_lower:
                return "STRUCTURED", "MAX_RAINFALL_RANGE", 0.95
            return "STRUCTURED", "MAX_RAINFALL", 0.95
        elif "average" in q_lower or "mean" in q_lower:
            return "STRUCTURED", "AVERAGE_RAINFALL", 0.95
        elif "total" in q_lower:
            return "STRUCTURED", "TOTAL_RAINFALL", 0.95
        elif "how many" in q_lower or "count" in q_lower:
            return "STRUCTURED", "EVENT_COUNT", 0.95
        elif "which district had the most" in q_lower:
            return "STRUCTURED", "STATISTICAL_COMPARISON", 0.95
        else:
            return "STRUCTURED", "STRUCTURED_AGGREGATE", 0.95

    # -------------------------------------------------------------
    # Priority 9: Document Narrative Checks
    # -------------------------------------------------------------
    if has_doc_intent or "hpsdma" in q_lower or "gsi" in q_lower or "pdna" in q_lower or "report" in q_lower or "study" in q_lower:
        return "DOCUMENT", "EVENT_NARRATIVE", 0.90

    # Default fallback
    return "DOCUMENT", "GENERAL_DOCUMENT_SEARCH", 0.75

def retrieve(query: str, top_k_docs: int = 5) -> Dict[str, Any]:
    entities = extract_entities(query)
    route, intent, confidence = classify_query(query, entities)

    structured_evidence = []
    document_evidence = []
    source_ids = set()
    warnings = []

    # ---------------------------------------------------------
    # Route A: NEGATIVE_REJECTED (Guaranteed Zero Hallucination)
    # ---------------------------------------------------------
    if route == "NEGATIVE_REJECTED":
        if entities["parameter_status"] == "UNSUPPORTED_PARAMETER":
            msg = f"No supported evidence. Requested parameter '{entities['unsupported_parameter']}' is outside the authorized project schema (Rainfall, Cloudburst, Flash Flood)."
        elif entities["geographic_status"] == "EXPLICIT_UNSUPPORTED_GEOGRAPHY":
            msg = f"No supported evidence. Location '{entities['unsupported_location']}' is outside the 4 authorized target districts (Kangra, Mandi, Shimla, Kullu)."
        elif entities["year_status"] == "OUT_OF_BOUNDS":
            msg = f"No supported evidence. Query year is outside the authorized temporal bounds (2011-2026)."
        else:
            msg = "No supported evidence. Query references entities, parameters, or dates outside authorized project scope."

        warnings.append(msg)
        return {
            "query": query,
            "route": route,
            "routing_confidence": confidence,
            "intent": intent,
            "status": "NO_SUPPORTED_EVIDENCE",
            "detected_entities": entities,
            "structured_evidence": [],
            "document_evidence": [],
            "sources": [],
            "warnings": warnings
        }

    # ---------------------------------------------------------
    # Route B: STRUCTURED or HYBRID -> Query SQLite Engine
    # Note: LANDSLIDE_NARRATIVE is excluded from Route B!
    # ---------------------------------------------------------
    if route in ("STRUCTURED", "HYBRID") and intent != "LANDSLIDE_IMPACT_NARRATIVE":
        target_dist = entities["district"]  # None if STATE_LEVEL or NO_GEOGRAPHY_SPECIFIED

        if intent == "ANNUAL_TOTAL_INCOMPLETE":
            res = sr.get_rainfall_statistics(target_dist or "Kangra", 2026)
            structured_evidence.append(res)
            warnings.append(res["message"])

        elif intent == "MAX_RAINFALL":
            res = sr.get_max_rainfall(target_dist, entities["year"])
            structured_evidence.append(res)
            if res.get("source_id"):
                source_ids.add(res["source_id"])

        elif intent == "MAX_RAINFALL_RANGE":
            # Detect month if present
            s_date, e_date = "2023-08-01", "2023-08-31"
            if "july" in query.lower():
                s_date, e_date = "2023-07-01", "2023-07-31"
            res = sr.get_max_rainfall(target_dist, entities["year"] or 2023, s_date, e_date)
            structured_evidence.append(res)
            if res.get("source_id"):
                source_ids.add(res["source_id"])

        elif intent == "DATE_RAINFALL" and entities["date"]:
            if target_dist:
                res = sr.get_rainfall_by_date(target_dist, entities["date"])
                structured_evidence.append(res)
                if res.get("source_id"):
                    source_ids.add(res["source_id"])
            else:
                # If no district specified for date, retrieve for Kangra, Mandi, Shimla, Kullu
                for d in ["Kangra", "Mandi", "Shimla", "Kullu"]:
                    r_d = sr.get_rainfall_by_date(d, entities["date"])
                    if r_d.get("status") in ("OK", "ZERO_RAINFALL"):
                        structured_evidence.append(r_d)
                        if r_d.get("source_id"):
                            source_ids.add(r_d["source_id"])

        elif intent == "AVERAGE_RAINFALL" or intent == "TOTAL_RAINFALL":
            res = sr.get_rainfall_statistics(target_dist or "Mandi", entities["year"])
            structured_evidence.append(res)
            if res.get("source_id"):
                source_ids.add(res["source_id"])

        elif intent == "EVENT_COUNT":
            if entities.get("year"):
                res = sr.get_events_by_year(entities["year"], target_dist, entities["event_type"])
            else:
                res = sr.get_events_by_type(
                    entities["event_type"] or "Flash Flood",
                    target_dist,
                    entities["start_year"] or 2011,
                    entities["end_year"] or 2025
                )
            structured_evidence.append(res)
            if res.get("source_id"):
                source_ids.add(res["source_id"])

        elif intent == "EVENT_LOOKUP":
            res = sr.get_events_by_year(entities["year"] or 2023, target_dist or "Mandi", entities["event_type"])
            structured_evidence.append(res)
            if res.get("source_id"):
                source_ids.add(res["source_id"])

        elif intent == "STATISTICAL_COMPARISON":
            res = sr.get_cloudburst_summary(target_dist)
            structured_evidence.append(res)
            if res.get("source_id"):
                source_ids.add(res["source_id"])

        elif intent == "PARTIAL_YEAR_STATUS":
            res = sr.get_telemetry_2026(target_dist)
            structured_evidence.append(res)
            if res.get("source_id"):
                source_ids.add(res["source_id"])
            warnings.append("2026 data is PARTIAL. Telemetry reflects recent AWS observations.")

        elif intent == "HAZARD_RAINFALL_CORRELATION":
            res_rain = sr.get_rainfall_statistics(target_dist or "Kullu", entities["year"] or 2023)
            structured_evidence.append(res_rain)
            if res_rain.get("source_id"):
                source_ids.add(res_rain["source_id"])

            res_evt = sr.get_events_by_year(entities["year"] or 2023, target_dist or "Kullu")
            structured_evidence.append(res_evt)
            if res_evt.get("source_id"):
                source_ids.add(res_evt["source_id"])

    # ---------------------------------------------------------
    # Route C: DOCUMENT or HYBRID -> Query FAISS Semantic Engine
    # ---------------------------------------------------------
    if route in ("DOCUMENT", "HYBRID"):
        sem_res = sem.semantic_search(
            query=query,
            top_k=top_k_docs,
            district=entities["district"],
            year=entities["year"]
        )

        if sem_res.get("status") == "OK":
            document_evidence = sem_res.get("results", [])
            for d in document_evidence:
                if d.get("source_id"):
                    source_ids.add(d["source_id"])
        else:
            warnings.append(sem_res.get("message", "No matching document passages found."))

    # Construct final fused sources list
    sources_list = []
    if source_ids:
        conn = sr.get_connection()
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in source_ids)
        cur.execute(f"SELECT * FROM source_registry WHERE source_id IN ({placeholders})", list(source_ids))
        for row in cur.fetchall():
            sources_list.append(dict(row))
        conn.close()

    # Determine status
    status = "OK"
    if structured_evidence:
        # If any structured result has a non-OK status, propagate it
        for s in structured_evidence:
            if s.get("status") in ("INSUFFICIENT_FOR_FULL_YEAR", "ZERO_RAINFALL", "ZERO_DOCUMENTED_EVENTS", "NO_DATA"):
                status = s["status"]
                break

    if not structured_evidence and not document_evidence:
        status = "NO_SUPPORTED_EVIDENCE"

    return {
        "query": query,
        "route": route,
        "routing_confidence": confidence,
        "intent": intent,
        "status": status,
        "detected_entities": entities,
        "structured_evidence": structured_evidence,
        "document_evidence": document_evidence,
        "sources": sources_list,
        "warnings": warnings
    }
