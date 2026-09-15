"""
build_sqlite_db.py
Creates the authoritative SQLite structured database: data/master/hp_extreme_weather.db
Loads verified Milestone 1 datasets:
- district_daily_rainfall (21,916 rows)
- station_district_rainfall (25 rows)
- telemetry_rainfall (4 rows)
- cloudburst_events (23 rows)
- flash_flood_events (17 rows)
- extreme_weather_events (39 canonical events)
- source_registry (8 authoritative sources)
Builds indexes for high-performance controlled queries.
"""

import os
import sqlite3
import pandas as pd

DB_PATH = "data/master/hp_extreme_weather.db"
SOURCES = {
    "district_daily_rainfall": "data/processed/rainfall/district_daily_rainfall.csv",
    "station_district_rainfall": "data/processed/rainfall/station_district_rainfall.csv",
    "telemetry_rainfall": "data/processed/rainfall/telemetry_rainfall.csv",
    "cloudburst_events": "data/processed/cloudburst/cloudburst_events.csv",
    "flash_flood_events": "data/processed/flash_flood/flash_flood_events.csv",
    "extreme_weather_events": "data/processed/combined/extreme_weather_events.csv",
    "source_registry": "reports/source_registry.csv",
}

def create_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        print(f"Removing existing database to ensure clean idempotency: {DB_PATH}")
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for table_name, csv_path in SOURCES.items():
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing required input dataset: {csv_path}")
        
        df = pd.read_csv(csv_path)
        print(f"Loading {table_name} from {csv_path} ({len(df)} rows)...")
        df.to_sql(table_name, conn, if_exists="replace", index=False)

    # Create indexes
    print("Creating indexes on structured tables...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dist_rain_date_dist ON district_daily_rainfall (date, district)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dist_rain_year_dist ON district_daily_rainfall (year, district)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_station_date_dist ON station_district_rainfall (date, district)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cb_dist_year ON cloudburst_events (district, year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cb_event_id ON cloudburst_events (event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ff_dist_year ON flash_flood_events (district, year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ff_event_id ON flash_flood_events (event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_canon_dist_year_type ON extreme_weather_events (district, year, primary_event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_canon_event_id ON extreme_weather_events (canonical_event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_src_id ON source_registry (source_id)")

    conn.commit()

    # Verification
    print("\n--- SQLite Database Verification ---")
    for table_name in SOURCES.keys():
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Table '{table_name}': {count} rows")

    conn.close()
    print(f"\nAuthoritative SQLite database successfully built at: {DB_PATH}")

if __name__ == "__main__":
    create_database()
