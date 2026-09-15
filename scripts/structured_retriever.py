"""
structured_retriever.py
Milestone 2B: Authoritative Structured Retrieval Engine
Queries data/master/hp_extreme_weather.db using controlled, parameterized SQL functions.
Never generates unrestricted SQL from user text.

Supported Entities & Validation:
- Districts: Kangra, Mandi, Shimla, Kullu
- Years: 2011 through 2026 (2026 is strictly PARTIAL)
- Event Types: Cloudburst, Flash Flood, Heavy Rainfall, Landslide

Data States:
- ZERO_RAINFALL: Valid observation recorded as 0.0 mm
- ZERO_DOCUMENTED_EVENTS: Verified period/district with 0 events
- NO_DATA: No observation exists for the specified query parameters
- INSUFFICIENT_FOR_FULL_YEAR: Incomplete temporal coverage (e.g., 2026 full-year aggregations)
- NO_SUPPORTED_EVIDENCE: Out of bounds district, future year, or unverified entity

Evidence Contract:
Every result returns structured records with:
- evidence_id
- evidence_type: OBSERVED or CALCULATED
- source_id
- status: OK, ZERO_RAINFALL, ZERO_DOCUMENTED_EVENTS, NO_DATA, INSUFFICIENT_FOR_FULL_YEAR, NO_SUPPORTED_EVIDENCE
- value / content
- provenance
"""

import os
import sqlite3
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

DB_PATH = "data/master/hp_extreme_weather.db"
ALLOWED_DISTRICTS = {"Kangra", "Mandi", "Shimla", "Kullu"}
VALID_YEAR_MIN = 2011
VALID_YEAR_MAX = 2026
PARTIAL_YEAR = 2026

ALLOWED_EVENT_TYPES = {
    "cloudburst": "Cloudburst",
    "flash flood": "Flash Flood",
    "flash_flood": "Flash Flood",
    "heavy rainfall": "Heavy Rainfall",
    "heavy_rainfall": "Heavy Rainfall",
    "landslide": "Landslide"
}

def get_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run build_sqlite_db.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def normalize_district(dist: Optional[str]) -> Optional[str]:
    if not dist:
        return None
    dist_clean = dist.strip().title()
    for d in ALLOWED_DISTRICTS:
        if d.lower() == dist_clean.lower():
            return d
    return None

def normalize_event_type(etype: Optional[str]) -> Optional[str]:
    if not etype:
        return None
    clean = etype.strip().lower()
    return ALLOWED_EVENT_TYPES.get(clean, None)

def validate_date(date_str: str) -> bool:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return VALID_YEAR_MIN <= dt.year <= VALID_YEAR_MAX
    except Exception:
        return False

# -------------------------------------------------------------
# 1. get_max_rainfall
# -------------------------------------------------------------
def get_max_rainfall(district: Optional[str] = None, year: Optional[int] = None, 
                     start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    norm_dist = normalize_district(district)
    if district and not norm_dist:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"District '{district}' is outside the 4 authorized target districts (Kangra, Mandi, Shimla, Kullu).",
            "data": None
        }

    if year is not None:
        if year < VALID_YEAR_MIN or year > VALID_YEAR_MAX:
            return {
                "status": "NO_SUPPORTED_EVIDENCE",
                "message": f"Year {year} is out of authorized temporal bounds (2011-2026).",
                "data": None
            }

    conn = get_connection()
    cur = conn.cursor()

    conditions = []
    params = []

    if norm_dist:
        conditions.append("district = ?")
        params.append(norm_dist)
    if year:
        conditions.append("year = ?")
        params.append(year)
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""
        SELECT date, year, district, max_rainfall_mm, mean_rainfall_mm, source_type
        FROM district_daily_rainfall
        {where_clause}
        ORDER BY max_rainfall_mm DESC
        LIMIT 1
    """
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()

    if not row or row["max_rainfall_mm"] is None:
        return {
            "status": "NO_DATA",
            "message": "No rainfall records found for the specified criteria.",
            "data": None
        }

    return {
        "status": "OK",
        "evidence_id": f"EVID_MAX_RAIN_{row['district']}_{row['date']}",
        "evidence_type": "CALCULATED",
        "source_id": "SRC_IMD_GRIDDED_025",
        "district": row["district"],
        "date": row["date"],
        "year": row["year"],
        "max_rainfall_mm": float(row["max_rainfall_mm"]),
        "mean_rainfall_mm": float(row["mean_rainfall_mm"]),
        "aggregation_source": row["source_type"],
        "notes": f"Peak spatial grid cell rainfall in {row['district']} on {row['date']} was {row['max_rainfall_mm']} mm."
    }

# -------------------------------------------------------------
# 2. get_rainfall_by_date
# -------------------------------------------------------------
def get_rainfall_by_date(district: str, date: str) -> Dict[str, Any]:
    norm_dist = normalize_district(district)
    if not norm_dist:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"District '{district}' is outside authorized scope.",
            "data": None
        }

    if not validate_date(date):
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"Date '{date}' is invalid or out of temporal bounds (2011-2026).",
            "data": None
        }

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT date, year, district, mean_rainfall_mm, max_rainfall_mm, min_rainfall_mm, valid_cells_count, source_type
        FROM district_daily_rainfall
        WHERE district = ? AND date = ?
    """, (norm_dist, date))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "status": "NO_DATA",
            "message": f"No rainfall observation recorded for {norm_dist} on {date}.",
            "data": None
        }

    mean_val = float(row["mean_rainfall_mm"])
    max_val = float(row["max_rainfall_mm"])
    
    status = "ZERO_RAINFALL" if max_val == 0.0 else "OK"

    return {
        "status": status,
        "evidence_id": f"EVID_RAIN_OBS_{norm_dist}_{date}",
        "evidence_type": "OBSERVED",
        "source_id": "SRC_IMD_GRIDDED_025",
        "district": norm_dist,
        "date": date,
        "year": row["year"],
        "mean_rainfall_mm": mean_val,
        "max_rainfall_mm": max_val,
        "min_rainfall_mm": float(row["min_rainfall_mm"]),
        "valid_cells_count": row["valid_cells_count"],
        "notes": f"{'Zero rainfall recorded across all grid cells' if status == 'ZERO_RAINFALL' else f'District mean {mean_val} mm, max cell {max_val} mm'} on {date}."
    }

# -------------------------------------------------------------
# 3. get_rainfall_statistics
# -------------------------------------------------------------
def get_rainfall_statistics(district: str, year: Optional[int] = None, 
                            start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    norm_dist = normalize_district(district)
    if not norm_dist:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"District '{district}' is outside authorized scope.",
            "data": None
        }

    # Strict check for 2026 full year
    if year == PARTIAL_YEAR and not (start_date and end_date):
        return {
            "status": "INSUFFICIENT_FOR_FULL_YEAR",
            "evidence_id": f"EVID_INSUFFICIENT_2026_{norm_dist}",
            "evidence_type": "CALCULATED",
            "source_id": "SRC_IMD_GRIDDED_025",
            "message": "Year 2026 is an in-progress partial period. Full-year annual aggregates cannot be calculated without introducing severe scientific distortion. Only telemetry/observations up to current date are available.",
            "data": None,
            "year": 2026,
            "district": norm_dist
        }

    conn = get_connection()
    cur = conn.cursor()

    conditions = ["district = ?"]
    params = [norm_dist]

    if year:
        if year < VALID_YEAR_MIN or year > VALID_YEAR_MAX:
            conn.close()
            return {
                "status": "NO_SUPPORTED_EVIDENCE",
                "message": f"Year {year} is out of temporal bounds (2011-2026).",
                "data": None
            }
        conditions.append("year = ?")
        params.append(year)
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)

    where_clause = " WHERE " + " AND ".join(conditions)
    query = f"""
        SELECT 
            COUNT(*) as days_count,
            ROUND(SUM(mean_rainfall_mm), 2) as total_mean_rainfall_mm,
            ROUND(AVG(mean_rainfall_mm), 2) as average_daily_rainfall_mm,
            ROUND(MAX(max_rainfall_mm), 2) as absolute_peak_cell_mm,
            ROUND(MIN(min_rainfall_mm), 2) as min_cell_mm,
            SUM(CASE WHEN max_rainfall_mm = 0 THEN 1 ELSE 0 END) as zero_rain_days,
            SUM(CASE WHEN max_rainfall_mm >= 50.0 THEN 1 ELSE 0 END) as heavy_rain_days,
            SUM(CASE WHEN max_rainfall_mm >= 100.0 THEN 1 ELSE 0 END) as very_heavy_rain_days
        FROM district_daily_rainfall
        {where_clause}
    """
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()

    if not row or row["days_count"] == 0:
        return {
            "status": "NO_DATA",
            "message": f"No rainfall records found for {norm_dist} with specified criteria.",
            "data": None
        }

    return {
        "status": "OK",
        "evidence_id": f"EVID_RAIN_STAT_{norm_dist}_{year if year else 'RANGE'}",
        "evidence_type": "CALCULATED",
        "source_id": "SRC_IMD_GRIDDED_025",
        "district": norm_dist,
        "year": year,
        "days_count": row["days_count"],
        "total_mean_rainfall_mm": row["total_mean_rainfall_mm"],
        "average_daily_rainfall_mm": row["average_daily_rainfall_mm"],
        "absolute_peak_cell_mm": row["absolute_peak_cell_mm"],
        "min_cell_mm": row["min_cell_mm"],
        "zero_rain_days": row["zero_rain_days"],
        "heavy_rain_days": row["heavy_rain_days"],
        "very_heavy_rain_days": row["very_heavy_rain_days"]
    }

# -------------------------------------------------------------
# 4. get_events_by_year
# -------------------------------------------------------------
def get_events_by_year(year: int, district: Optional[str] = None, event_type: Optional[str] = None) -> Dict[str, Any]:
    if year < VALID_YEAR_MIN or year > VALID_YEAR_MAX:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"Year {year} is out of authorized temporal bounds (2011-2026).",
            "events": []
        }

    norm_dist = normalize_district(district) if district else None
    if district and not norm_dist:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"District '{district}' is outside authorized scope.",
            "events": []
        }

    norm_etype = normalize_event_type(event_type) if event_type else None
    if event_type and not norm_etype:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"Event type '{event_type}' is unrecognized. Allowed: Cloudburst, Flash Flood, Heavy Rainfall, Landslide.",
            "events": []
        }

    conn = get_connection()
    cur = conn.cursor()

    conditions = ["year = ?"]
    params = [year]

    if norm_dist:
        conditions.append("district = ?")
        params.append(norm_dist)
    if norm_etype:
        conditions.append("primary_event_type = ?")
        params.append(norm_etype)

    where_clause = " WHERE " + " AND ".join(conditions)
    query = f"""
        SELECT canonical_event_id, date, year, district, primary_event_type, tehsil, panchayat_village,
               fatalities, houses_damaged_fully, financial_loss_inr_lakh, primary_source, event_summary
        FROM extreme_weather_events
        {where_clause}
        ORDER BY date ASC
    """
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    events = [dict(r) for r in rows]
    count = len(events)

    if count == 0:
        return {
            "status": "ZERO_DOCUMENTED_EVENTS",
            "evidence_id": f"EVID_EVENTS_{year}_{norm_dist or 'ALL'}",
            "evidence_type": "CALCULATED",
            "source_id": "SRC_HPSDMA_LOSS_MEMORANDUMS",
            "message": f"Zero documented {norm_etype or 'extreme weather'} events found in {norm_dist or 'all target districts'} for year {year}.",
            "count": 0,
            "events": []
        }

    return {
        "status": "OK",
        "evidence_id": f"EVID_EVENTS_{year}_{norm_dist or 'ALL'}",
        "evidence_type": "OBSERVED",
        "source_id": "SRC_HPSDMA_LOSS_MEMORANDUMS",
        "year": year,
        "district": norm_dist,
        "event_type": norm_etype,
        "count": count,
        "events": events
    }

# -------------------------------------------------------------
# 5. get_events_by_type
# -------------------------------------------------------------
def get_events_by_type(event_type: str, district: Optional[str] = None, 
                       start_year: Optional[int] = 2011, end_year: Optional[int] = 2025) -> Dict[str, Any]:
    norm_etype = normalize_event_type(event_type)
    if not norm_etype:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"Event type '{event_type}' is outside authorized scope.",
            "count": 0,
            "events": []
        }

    norm_dist = normalize_district(district) if district else None
    if district and not norm_dist:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"District '{district}' is outside authorized scope.",
            "count": 0,
            "events": []
        }

    conn = get_connection()
    cur = conn.cursor()

    conditions = ["primary_event_type = ?"]
    params = [norm_etype]

    if norm_dist:
        conditions.append("district = ?")
        params.append(norm_dist)
    if start_year:
        conditions.append("year >= ?")
        params.append(start_year)
    if end_year:
        conditions.append("year <= ?")
        params.append(end_year)

    where_clause = " WHERE " + " AND ".join(conditions)
    query = f"""
        SELECT canonical_event_id, date, year, district, primary_event_type, tehsil, panchayat_village,
               fatalities, houses_damaged_fully, financial_loss_inr_lakh, primary_source, event_summary
        FROM extreme_weather_events
        {where_clause}
        ORDER BY date ASC
    """
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    events = [dict(r) for r in rows]
    count = len(events)

    status = "ZERO_DOCUMENTED_EVENTS" if count == 0 else "OK"

    return {
        "status": status,
        "evidence_id": f"EVID_TYPE_{norm_etype}_{norm_dist or 'ALL'}",
        "evidence_type": "CALCULATED",
        "source_id": "SRC_HPSDMA_LOSS_MEMORANDUMS",
        "event_type": norm_etype,
        "district": norm_dist,
        "start_year": start_year,
        "end_year": end_year,
        "count": count,
        "events": events
    }

# -------------------------------------------------------------
# 6. get_cloudburst_summary
# -------------------------------------------------------------
def get_cloudburst_summary(district: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()

    if district:
        norm_dist = normalize_district(district)
        if not norm_dist:
            conn.close()
            return {"status": "NO_SUPPORTED_EVIDENCE", "message": f"District '{district}' is not authorized."}
        cur.execute("""
            SELECT district, COUNT(*) as event_count, SUM(fatalities) as total_fatalities, 
                   SUM(financial_loss_inr_lakh) as total_loss_lakh,
                   MIN(year) as first_year, MAX(year) as last_year
            FROM cloudburst_events
            WHERE district = ?
            GROUP BY district
        """, (norm_dist,))
    else:
        cur.execute("""
            SELECT district, COUNT(*) as event_count, SUM(fatalities) as total_fatalities, 
                   SUM(financial_loss_inr_lakh) as total_loss_lakh,
                   MIN(year) as first_year, MAX(year) as last_year
            FROM cloudburst_events
            GROUP BY district
            ORDER BY event_count DESC
        """)

    rows = cur.fetchall()
    conn.close()

    summary = [dict(r) for r in rows]
    top_district = summary[0]["district"] if summary else None

    return {
        "status": "OK",
        "evidence_id": "EVID_CLOUDBURST_SUMMARY",
        "evidence_type": "CALCULATED",
        "source_id": "SRC_HPSDMA_LOSS_MEMORANDUMS",
        "top_district": top_district,
        "district_breakdown": summary
    }

# -------------------------------------------------------------
# 7. get_event_by_id
# -------------------------------------------------------------
def get_event_by_id(event_id: str) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM extreme_weather_events
        WHERE canonical_event_id = ?
    """, (event_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "status": "NO_SUPPORTED_EVIDENCE",
            "message": f"Event ID '{event_id}' does not exist.",
            "data": None
        }

    return {
        "status": "OK",
        "evidence_id": f"EVID_{event_id}",
        "evidence_type": "OBSERVED",
        "source_id": row["primary_source"],
        "data": dict(row)
    }

# -------------------------------------------------------------
# 8. get_telemetry_2026
# -------------------------------------------------------------
def get_telemetry_2026(district: Optional[str] = None) -> Dict[str, Any]:
    norm_dist = normalize_district(district) if district else None
    conn = get_connection()
    cur = conn.cursor()

    if norm_dist:
        cur.execute("""
            SELECT station_name, district, date, year, timestamp_ist, rainfall_mm, source_document
            FROM telemetry_rainfall
            WHERE district = ?
            ORDER BY timestamp_ist DESC
        """, (norm_dist,))
    else:
        cur.execute("""
            SELECT station_name, district, date, year, timestamp_ist, rainfall_mm, source_document
            FROM telemetry_rainfall
            ORDER BY timestamp_ist DESC
        """)
    rows = cur.fetchall()
    conn.close()

    records = [dict(r) for r in rows]

    return {
        "status": "OK",
        "evidence_id": "EVID_TELEMETRY_2026",
        "evidence_type": "OBSERVED",
        "source_id": "SRC_IMD_SHIMLA_TELEMETRY_2026",
        "year_status": "PARTIAL",
        "coverage_note": "Observations represent active live AWS telemetry recorded in September 2026.",
        "records_count": len(records),
        "records": records
    }
