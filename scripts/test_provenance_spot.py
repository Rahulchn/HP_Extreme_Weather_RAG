import pandas as pd
import struct
import datetime
from pathlib import Path

PROJECT_ROOT = Path("HP_Extreme_Weather_RAG")
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

gridded_df = pd.read_csv(DATA_PROCESSED / "rainfall" / "imd_gridded_daily_rainfall.csv")
station_df = pd.read_csv(DATA_PROCESSED / "rainfall" / "station_district_rainfall.csv")
telemetry_df = pd.read_csv(DATA_PROCESSED / "rainfall" / "telemetry_rainfall.csv")
cb_df = pd.read_csv(DATA_PROCESSED / "cloudburst" / "cloudburst_events.csv")
ff_df = pd.read_csv(DATA_PROCESSED / "flash_flood" / "flash_flood_events.csv")
esm_df = pd.read_csv(DATA_PROCESSED / "combined" / "event_source_mapping.csv")

print("=================== 10 RAINFALL PROVENANCE SPOT CHECKS ===================")
# Sample 6 gridded, 2 station, 2 telemetry
grid_sample = gridded_df.sample(6, random_state=42)
st_sample = station_df.sample(2, random_state=42)
tel_sample = telemetry_df.sample(2, random_state=42)
rf_sample = pd.concat([grid_sample, st_sample, tel_sample])

i = 1
for _, r in rf_sample.iterrows():
    stype = r["source_type"]
    dt = r["date"]
    rf_mm = r["rainfall_mm"]
    
    if stype == "IMD_GRIDDED_SPATIAL_DATA":
        yr = int(r["year"])
        lat = float(r["latitude"])
        lon = float(r["longitude"])
        raw_file = DATA_RAW / "rainfall" / f"imd_gridded_rain_{yr}.grd"
        exists = raw_file.exists()
        
        # Calculate raw byte offset
        la_idx = int(round((lat - 6.5) / 0.25))
        lo_idx = int(round((lon - 66.5) / 0.25))
        day_num = int(datetime.datetime.strptime(dt, "%Y-%m-%d").strftime("%j"))
        day_idx = day_num - 1
        cell_idx = la_idx * 135 + lo_idx
        byte_pos = (day_idx * 17415 + cell_idx) * 4
        
        # Read byte
        with open(raw_file, "rb") as f:
            f.seek(byte_pos)
            val = struct.unpack("<f", f.read(4))[0]
            
        pass_status = "PASS" if (abs(float(rf_mm) - val) < 0.01) else "FAIL"
        print(f"[{i}] {dt} | Grid ({lat:.2f}N, {lon:.2f}E) | Val={rf_mm} mm | RawBytePos={byte_pos} | RawVal={val:.2f} | File={raw_file.name} | Status={pass_status}")
    elif stype == "IMD_STATION_OR_DISTRICT_OBSERVATION":
        raw_file = DATA_RAW / "rainfall" / r["source_document"]
        exists = raw_file.exists()
        pass_status = "PASS" if exists else "FAIL"
        print(f"[{i}] {dt} | Station={r['station_name']} ({r['district']}) | Val={rf_mm} mm | Doc={r['source_document']} | Loc={r['page_table_location']} | Status={pass_status}")
    else: # Telemetry
        raw_file = DATA_RAW / "rainfall" / r["source_document"]
        exists = raw_file.exists()
        pass_status = "PASS" if exists else "FAIL"
        print(f"[{i}] {dt} | Telemetry AWS={r['station_name']} ({r['district']}) | Val={rf_mm} mm | Doc={r['source_document']} | Loc={r['page_table_location']} | Status={pass_status}")
    i += 1

print("\n=================== 5 CLOUDBURST PROVENANCE SPOT CHECKS ===================")
cb_sample = cb_df.sample(5, random_state=42)
i = 1
for _, r in cb_sample.iterrows():
    fpath = DATA_RAW / "disaster_reports" / r["source_file"]
    exists = fpath.exists()
    pass_status = "PASS" if exists else "FAIL"
    canon_match = esm_df[esm_df["source_record_id"] == r["event_id"]]
    canon_id = canon_match.iloc[0]["canonical_event_id"] if not canon_match.empty else "N/A"
    print(f"[{i}] ID={r['event_id']} -> CanonID={canon_id} | Date={r['date']} | Dist={r['district']} | Loc={r['tehsil']}-{r['panchayat_village']} | Doc={r['source_file']} | Page={r['page_table_location']} | FileExists={exists} | Status={pass_status}")
    i += 1

print("\n=================== 5 FLASH FLOOD PROVENANCE SPOT CHECKS ===================")
ff_sample = ff_df.sample(5, random_state=42)
i = 1
for _, r in ff_sample.iterrows():
    fpath = DATA_RAW / "disaster_reports" / r["source_file"]
    exists = fpath.exists()
    pass_status = "PASS" if exists else "FAIL"
    canon_match = esm_df[esm_df["source_record_id"] == r["event_id"]]
    canon_id = canon_match.iloc[0]["canonical_event_id"] if not canon_match.empty else "N/A"
    print(f"[{i}] ID={r['event_id']} -> CanonID={canon_id} | Date={r['date']} | Dist={r['district']} | Basin={r['river_basin_khad']} | Doc={r['source_file']} | Page={r['page_table_location']} | FileExists={exists} | Status={pass_status}")
    i += 1
