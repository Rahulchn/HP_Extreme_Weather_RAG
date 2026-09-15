import pandas as pd
import os
import glob

reg = pd.read_csv('HP_Extreme_Weather_RAG/reports/source_registry.csv')
raw_files = []
for root, dirs, files in os.walk('HP_Extreme_Weather_RAG/data/raw'):
    for f in files:
        raw_files.append((f, os.path.join(root, f), os.path.getsize(os.path.join(root, f))))

print("=== RAW FILES FOUND IN data/raw/ ===")
for f, p, s in sorted(raw_files):
    print(f"{f} ({s:,} bytes) in {os.path.dirname(p)}")

print("\n=== SOURCE REGISTRY AUDIT VS ACTUAL FILES ===")
for idx, r in reg.iterrows():
    print(f"[{r['source_id']}] {r['source_name']}")
    print(f"  Organization: {r['organization']}")
    print(f"  Parameter: {r['measurement_type']}")
    print(f"  Years Covered in Registry: {r['actual_start_year']}-{r['actual_end_year']} (2026: {r['year_status_2026']})")
    print(f"  Districts Covered: {r['geographic_resolution']}")
    
    # Check matching raw files
    matched = []
    for f, p, s in raw_files:
        if r['source_id'] == 'SRC_IMD_GRIDDED_025' and 'gridded' in f:
            matched.append((f, s))
        elif r['source_id'] == 'SRC_IMD_SHIMLA_DISTRICT_MONSOON' and ('yearlymonsoon' in f or 'climatology' in f or 'rainfallmonthly' in f or 'monsoon_report' in f):
            matched.append((f, s))
        elif r['source_id'] == 'SRC_IMD_SHIMLA_TELEMETRY_2026' and ('2026' in f and ('telemetry' in f or 'bulletin' in f or 'rainfall' in f)):
            matched.append((f, s))
        elif r['source_id'] == 'SRC_HPSDMA_PDNA_2023' and 'pdna_monsoon_2023' in f:
            matched.append((f, s))
        elif r['source_id'] == 'SRC_HPSDMA_PDNA_2025' and '2025' in f and 'pdna' in f:
            matched.append((f, s))
        elif r['source_id'] == 'SRC_HPSDMA_LOSS_MEMORANDUMS' and 'hpsdma_memo' in f:
            matched.append((f, s))
        elif r['source_id'] == 'SRC_HPSDMA_HISTORICAL_LOSS_2007_2015' and 'lr3' in f:
            matched.append((f, s))
        elif r['source_id'] == 'SRC_HPSDMA_10YR_LOSSES_2016_2025' and '10year_losses' in f:
            matched.append((f, s))
        elif r['source_id'] == 'SRC_GSI_WADIA_EVENT_STUDIES' and 'gsi' in f:
            matched.append((f, s))
        elif r['source_id'] == 'SRC_PARLIAMENT_MHA_MOES_QA' and 'parliament' in f:
            matched.append((f, s))
            
    print(f"  Actual Files Matched ({len(matched)}): {[m[0] for m in matched]}")
    if matched:
        print("  Actual Availability: PHYSICALLY DOWNLOADED IN data/raw/")
    else:
        print("  Actual Availability: NOT DOWNLOADED / CATALOG REFERENCE ONLY")
    print("-" * 60)
