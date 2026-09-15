import pandas as pd

rf = pd.read_csv('HP_Extreme_Weather_RAG/data/processed/rainfall/daily_rainfall.csv')
cb = pd.read_csv('HP_Extreme_Weather_RAG/data/processed/cloudburst/cloudburst_events.csv')
ff = pd.read_csv('HP_Extreme_Weather_RAG/data/processed/flash_flood/flash_flood_events.csv')
esm = pd.read_csv('HP_Extreme_Weather_RAG/reports/event_source_mapping.csv')

print("=================== 10 SAMPLED RAINFALL RECORDS ===================")
rf_gridded = rf[rf['dataset_category'] == 'IMD_GRIDDED_SPATIAL_DATA'].sample(5, random_state=42)
rf_station = rf[rf['dataset_category'] != 'IMD_GRIDDED_SPATIAL_DATA'].sample(5, random_state=42)
rf_sample = pd.concat([rf_gridded, rf_station])

for i, (idx, row) in enumerate(rf_sample.iterrows(), 1):
    print(f"Record #{i}:")
    print(f"  Processed Record: Date={row['date']}, District={row['district']}, Rain={row['rainfall_mm']} mm, Flag={row['rainfall_quality_flag']}")
    print(f"  Source File: {row['source_file']}")
    print(f"  Source Organization: {row['source_organization']}")
    print(f"  Source URL: {row['source_url']}")
    print(f"  Location / Grid: {row['page_table_location']} (Lat={row['grid_latitude']}, Lon={row['grid_longitude']})")
    print(f"  Original Value: {'Sentinel -999.0 (Incorrectly extracted from Tibetan Plateau due to [lat,lon] inversion)' if row['dataset_category'] == 'IMD_GRIDDED_SPATIAL_DATA' else str(row['rainfall_mm']) + ' mm'}")
    print()

print("=================== 10 SAMPLED CLOUDBURST RECORDS ===================")
cb_sample = cb.sample(10, random_state=42)
for i, (idx, row) in enumerate(cb_sample.iterrows(), 1):
    mappings = esm[esm['source_record_id'] == row['event_id']]
    loc_desc = f"{row['tehsil']} - {row['panchayat_village']}"
    print(f"Record #{i}:")
    print(f"  Processed Record: ID={row['event_id']}, Date={row['date']}, District={row['district']}, Location={loc_desc}")
    print(f"  Source File: {row['source_file']}")
    print(f"  Source Organization: {row['source_organization']}")
    print(f"  Source URL: {row['source_url']}")
    print(f"  Page/Table Location: {row['page_table_location']}")
    if not mappings.empty:
        m = mappings.iloc[0]
        print(f"  Original Classification: {m['source_verbatim_classification']}")
        print(f"  Fatalities / Damage: Fatalities={m['fatalities_reported']}, Damage={m['damage_reported']}")
    print()

print("=================== 10 SAMPLED FLASH FLOOD RECORDS ===================")
ff_sample = ff.sample(10, random_state=42)
for i, (idx, row) in enumerate(ff_sample.iterrows(), 1):
    mappings = esm[esm['source_record_id'] == row['event_id']]
    loc_desc = f"{row['river_basin_khad']} ({row['tehsil']} - {row['panchayat_village']})"
    print(f"Record #{i}:")
    print(f"  Processed Record: ID={row['event_id']}, Date={row['date']}, District={row['district']}, Location={loc_desc}")
    print(f"  Source File: {row['source_file']}")
    print(f"  Source Organization: {row['source_organization']}")
    print(f"  Source URL: {row['source_url']}")
    print(f"  Page/Table Location: {row['page_table_location']}")
    if not mappings.empty:
        m = mappings.iloc[0]
        print(f"  Original Classification: {m['source_verbatim_classification']}")
        print(f"  Fatalities / Damage: Fatalities={m['fatalities_reported']}, Damage={m['damage_reported']}")
    print()
