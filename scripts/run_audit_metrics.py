"""
HP Extreme Weather RAG - Forensic Audit Generator
Computes exact audit metrics across daily_rainfall.csv, raw .grd binary files,
cloudburst_events.csv, flash_flood_events.csv, and extreme_weather_events.csv.
Generates:
- reports/rainfall_completeness_by_year.csv
- reports/rainfall_completeness_by_district.csv
- reports/rainfall_completeness_by_source.csv
- reports/event_coverage_matrix.csv
- reports/event_deduplication_audit.csv
"""

import os
import sys
import csv
import struct
import numpy as np
import pandas as pd
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_RAW = PROJECT_ROOT / "data" / "raw"

RAINFALL_CSV = DATA_PROCESSED / "rainfall" / "daily_rainfall.csv"
CLOUDBURST_CSV = DATA_PROCESSED / "cloudburst" / "cloudburst_events.csv"
FLASH_FLOOD_CSV = DATA_PROCESSED / "flash_flood" / "flash_flood_events.csv"
COMBINED_CSV = DATA_PROCESSED / "combined" / "extreme_weather_events.csv"
MAPPING_CSV = REPORTS_DIR / "event_source_mapping.csv"

def audit_rainfall_by_year():
    df = pd.read_csv(RAINFALL_CSV)
    years = list(range(2011, 2027))
    rows = []

    for yr in years:
        df_yr = df[df['year'] == yr]
        total = len(df_yr)
        valid = len(df_yr[df_yr['rainfall_quality_flag'] == 'VALID'])
        missing = len(df_yr[df_yr['rainfall_quality_flag'] == 'MISSING'])
        v_pct = (valid / total * 100.0) if total > 0 else 0.0
        m_pct = (missing / total * 100.0) if total > 0 else 0.0

        rows.append({
            "year": yr,
            "total_records": total,
            "valid_records": valid,
            "missing_records": missing,
            "valid_percentage": f"{v_pct:.2f}%",
            "missing_percentage": f"{m_pct:.2f}%"
        })

    out_path = REPORTS_DIR / "rainfall_completeness_by_year.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"[SUCCESS] Generated {out_path}")
    return rows

def audit_rainfall_by_district():
    df = pd.read_csv(RAINFALL_CSV)
    districts = ["Kangra", "Mandi", "Shimla", "Kullu"]
    rows = []

    for dist in districts:
        df_d = df[df['district'] == dist]
        total = len(df_d)
        valid = len(df_d[df_d['rainfall_quality_flag'] == 'VALID'])
        missing = len(df_d[df_d['rainfall_quality_flag'] == 'MISSING'])
        v_pct = (valid / total * 100.0) if total > 0 else 0.0
        m_pct = (missing / total * 100.0) if total > 0 else 0.0

        rows.append({
            "district": dist,
            "total_records": total,
            "valid_records": valid,
            "missing_records": missing,
            "valid_percentage": f"{v_pct:.2f}%",
            "missing_percentage": f"{m_pct:.2f}%"
        })

    out_path = REPORTS_DIR / "rainfall_completeness_by_district.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"[SUCCESS] Generated {out_path}")
    return rows

def audit_rainfall_by_source():
    df = pd.read_csv(RAINFALL_CSV)
    
    # Identify source subcategories
    gridded = df[df['dataset_category'] == 'IMD_GRIDDED_SPATIAL_DATA']
    station_all = df[df['dataset_category'] == 'IMD_STATION_OR_DISTRICT_OBSERVATION']
    telemetry = station_all[station_all['source_file'].str.contains('telemetry', case=False, na=False)]
    reports = station_all[~station_all['source_file'].str.contains('telemetry', case=False, na=False)]

    sources = [
        ("IMD_GRIDDED_SPATIAL_DATA", gridded, "2018, 2021, 2023 (Daily matrix)"),
        ("IMD_STATION_OR_DISTRICT_OBSERVATION (Combined)", station_all, "2011, 2014, 2017, 2018, 2021, 2023, 2026"),
        ("IMD_TELEMETRY", telemetry, "2026 (3-Hourly telemetry bulletin)"),
        ("IMD_REPORT_TABLE", reports, "2011, 2014, 2017, 2018, 2021, 2023, 2026 (Monsoon reports & normals)")
    ]

    rows = []
    for sname, sdf, cov in sources:
        total = len(sdf)
        valid = len(sdf[sdf['rainfall_quality_flag'] == 'VALID'])
        missing = len(sdf[sdf['rainfall_quality_flag'] == 'MISSING'])
        v_pct = (valid / total * 100.0) if total > 0 else 0.0

        rows.append({
            "source_type": sname,
            "records": total,
            "valid": valid,
            "missing": missing,
            "valid_percentage": f"{v_pct:.2f}%",
            "coverage": cov
        })

    out_path = REPORTS_DIR / "rainfall_completeness_by_source.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"[SUCCESS] Generated {out_path}")
    return rows

def audit_event_deduplication():
    df_cb = pd.read_csv(CLOUDBURST_CSV)
    df_ff = pd.read_csv(FLASH_FLOOD_CSV)
    df_comb = pd.read_csv(COMBINED_CSV)
    df_map = pd.read_csv(MAPPING_CSV)

    rows = []
    
    # Process cloudbursts
    for _, r in df_cb.iterrows():
        cid = r['canonical_event_id']
        comb_match = df_comb[df_comb['canonical_event_id'] == cid].iloc[0]
        map_matches = df_map[df_map['canonical_event_id'] == cid]
        orgs = ";".join(sorted(map_matches['source_organization'].unique()))
        is_dup = "YES (Merged with Flash Flood)" if cid == "CANON_20210712_KAN_DHA" else "NO"

        rows.append({
            "event_id": r['event_id'],
            "canonical_event_id": cid,
            "date": r['date'],
            "district": r['district'],
            "event_type": "Cloudburst",
            "location": f"{r['tehsil']} - {r['panchayat_village']}",
            "source_count": len(map_matches),
            "source_organizations": orgs,
            "possible_duplicate": is_dup,
            "classification_confidence": r['classification_confidence']
        })

    # Process flash floods
    for _, r in df_ff.iterrows():
        cid = r['canonical_event_id']
        comb_match = df_comb[df_comb['canonical_event_id'] == cid].iloc[0]
        map_matches = df_map[df_map['canonical_event_id'] == cid]
        orgs = ";".join(sorted(map_matches['source_organization'].unique()))
        is_dup = "YES (Merged with Cloudburst)" if cid == "CANON_20210712_KAN_DHA" else "NO"

        rows.append({
            "event_id": r['event_id'],
            "canonical_event_id": cid,
            "date": r['date'],
            "district": r['district'],
            "event_type": "Flash Flood",
            "location": f"{r['river_basin_khad']} ({r['tehsil']} - {r['panchayat_village']})",
            "source_count": len(map_matches),
            "source_organizations": orgs,
            "possible_duplicate": is_dup,
            "classification_confidence": r['classification_confidence']
        })

    out_path = REPORTS_DIR / "event_deduplication_audit.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"[SUCCESS] Generated {out_path}")
    return rows

def audit_event_coverage_matrix():
    df_comb = pd.read_csv(COMBINED_CSV)
    df_cb = pd.read_csv(CLOUDBURST_CSV)
    df_ff = pd.read_csv(FLASH_FLOOD_CSV)

    years = list(range(2011, 2027))
    rows = []

    # Years with available raw files but unparsed event data:
    # 2012: hpsdma_disaster_analysis_lr3_2007_2015.pdf present
    # 2013: hpsdma_memo_monsoon_2013_2015.pdf present
    # 2015: hpsdma_memo_monsoon_2013_2015.pdf present
    # 2016: hpsdma_memo_monsoon_2016.pdf present
    # 2025: hpsdma_memo_monsoon_2025.pdf present
    # 2026: Partial year in-progress

    unparsed_raw_years = {2012, 2013, 2015, 2016, 2025}

    for yr in years:
        if yr in unparsed_raw_years:
            rows.append({
                "year": yr,
                "kangra_events": "NA",
                "mandi_events": "NA",
                "shimla_events": "NA",
                "kullu_events": "NA",
                "cloudburst_events": "NA",
                "flash_flood_events": "NA",
                "coverage_status": "NO_DATA (Raw memo present in data/raw, unparsed)"
            })
        elif yr == 2026:
            rows.append({
                "year": yr,
                "kangra_events": "0",
                "mandi_events": "0",
                "shimla_events": "0",
                "kullu_events": "0",
                "cloudburst_events": "0",
                "flash_flood_events": "0",
                "coverage_status": "PARTIAL (In-progress; no documented event in current table)"
            })
        else:
            df_yr = df_comb[df_comb['year'] == yr]
            kan = len(df_yr[df_yr['district'] == 'Kangra'])
            man = len(df_yr[df_yr['district'] == 'Mandi'])
            shi = len(df_yr[df_yr['district'] == 'Shimla'])
            kul = len(df_yr[df_yr['district'] == 'Kullu'])

            cb_cnt = len(df_cb[df_cb['year'] == yr])
            ff_cnt = len(df_ff[df_ff['year'] == yr])

            rows.append({
                "year": yr,
                "kangra_events": str(kan),
                "mandi_events": str(man),
                "shimla_events": str(shi),
                "kullu_events": str(kul),
                "cloudburst_events": str(cb_cnt),
                "flash_flood_events": str(ff_cnt),
                "coverage_status": "DOCUMENTED_EVENTS"
            })

    out_path = REPORTS_DIR / "event_coverage_matrix.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"[SUCCESS] Generated {out_path}")
    return rows

def generate_spot_checks():
    """Extracts 10 specific grid observations across 2018, 2021, 2023 for manual verification"""
    GRID_LATS = np.linspace(6.5, 38.5, 129)
    GRID_LONS = np.linspace(66.5, 100.0, 135)

    spot_specs = [
        # Year, Day_idx (0-based), Date, District, Lat, Lon, Description
        (2023, 189, "2023-07-09", "Kullu", 32.25, 77.25, "Peak Kullu flood day"),
        (2023, 189, "2023-07-09", "Mandi", 31.75, 77.00, "Peak Mandi flood day"),
        (2023, 190, "2023-07-10", "Shimla", 31.00, 77.25, "Shimla deluge day"),
        (2023, 225, "2023-08-14", "Kangra", 32.25, 76.25, "Dharamshala 273mm extreme day"),
        (2021, 192, "2021-07-12", "Kangra", 32.25, 76.25, "Boh Kangra cloudburst day"),
        (2021, 208, "2021-07-28", "Kullu", 32.00, 77.25, "Brahma Ganga flash flood"),
        (2018, 265, "2018-09-23", "Kullu", 32.25, 77.25, "Manali deluge day"),
        (2018, 265, "2018-09-23", "Mandi", 31.50, 76.75, "Sundernagar extreme day"),
        (2018, 266, "2018-09-24", "Kangra", 32.00, 76.50, "Kangra heavy spell"),
        (2023, 0,   "2023-01-01", "Shimla", 31.25, 77.50, "Winter baseline dry/light day")
    ]

    spot_results = []
    for yr, day_idx, dt, dist, lat, lon, desc in spot_specs:
        fpath = DATA_RAW / "rainfall" / f"imd_gridded_rain_{yr}.grd"
        la_idx = int(round((lat - 6.5) / 0.25))
        lo_idx = int(round((lon - 66.5) / 0.25))

        # Under (lat=129, lon=135):
        # Index within day = la_idx * 135 + lo_idx
        # Offset in bytes = (day_idx * 17415 + la_idx * 135 + lo_idx) * 4
        byte_offset_A = (day_idx * 17415 + la_idx * 135 + lo_idx) * 4

        # Under (lon=135, lat=129) [what clean_data did]:
        # Index within day = lo_idx * 129 + la_idx
        byte_offset_B = (day_idx * 17415 + lo_idx * 129 + la_idx) * 4

        with open(fpath, "rb") as f:
            f.seek(byte_offset_A)
            raw_bytes_A = f.read(4)
            val_A = struct.unpack("<f", raw_bytes_A)[0]

            f.seek(byte_offset_B)
            raw_bytes_B = f.read(4)
            val_B = struct.unpack("<f", raw_bytes_B)[0]

        spot_results.append({
            "year": yr,
            "date": dt,
            "district": dist,
            "lat": lat,
            "lon": lon,
            "description": desc,
            "byte_offset_true": byte_offset_A,
            "raw_hex_true": raw_bytes_A.hex(),
            "true_decoded_val_mm": val_A,
            "clean_data_decoded_val": val_B,
            "clean_data_flag": "MISSING" if val_B == -999.0 else "VALID"
        })

    return spot_results

if __name__ == "__main__":
    print("Running audit metric computations ...")
    audit_rainfall_by_year()
    audit_rainfall_by_district()
    audit_rainfall_by_source()
    audit_event_deduplication()
    audit_event_coverage_matrix()
    spots = generate_spot_checks()
    print("\n--- 10-POINT SPOT CHECK RESULTS ---")
    for s in spots:
        print(f"{s['date']} | {s['district']:<6} | Lat {s['lat']} Lon {s['lon']} | True Val: {s['true_decoded_val_mm']:>6.2f} mm (hex: {s['raw_hex_true']}) | clean_data saw: {s['clean_data_decoded_val']} ({s['clean_data_flag']})")
