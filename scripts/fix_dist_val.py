import pandas as pd
import numpy as np

district_df = pd.read_csv("HP_Extreme_Weather_RAG/data/processed/rainfall/district_daily_rainfall.csv")
gridded_df = pd.read_csv("HP_Extreme_Weather_RAG/data/processed/rainfall/imd_gridded_daily_rainfall.csv")

dist_boxes = {
    "Kangra": {"lat_min": 31.75, "lat_max": 32.50, "lon_min": 75.50, "lon_max": 77.00},
    "Mandi": {"lat_min": 31.25, "lat_max": 32.00, "lon_min": 76.50, "lon_max": 77.50},
    "Kullu": {"lat_min": 31.50, "lat_max": 32.25, "lon_min": 77.00, "lon_max": 77.75},
    "Shimla": {"lat_min": 30.75, "lat_max": 31.25, "lon_min": 77.00, "lon_max": 78.00}
}

sampled = district_df.sample(20, random_state=42)

rows = []
for _, r in sampled.iterrows():
    dt = r['date']
    dist = r['district']
    stored_val = float(r['mean_rainfall_mm'])
    
    b = dist_boxes[dist]
    sub = gridded_df[(gridded_df['date'] == dt) & 
                     (gridded_df['latitude'] >= b['lat_min']) & (gridded_df['latitude'] <= b['lat_max']) &
                     (gridded_df['longitude'] >= b['lon_min']) & (gridded_df['longitude'] <= b['lon_max'])]
    
    cell_vals = sub['rainfall_mm'].astype(float).values
    recalc_val = float(np.mean(cell_vals))
    recalc_rounded = round(recalc_val, 2)
    
    diff = abs(stored_val - recalc_rounded)
    status = "PASS" if diff == 0.0 else "FAIL"
    
    rows.append({
        "date": dt,
        "district": dist,
        "stored_value_mm": f"{stored_val:.2f}",
        "recalculated_value_mm": f"{recalc_rounded:.2f}",
        "raw_mean_unrounded": f"{recalc_val:.4f}",
        "cells_counted": len(cell_vals),
        "absolute_difference": f"{diff:.4f}",
        "status": status
    })

out_df = pd.DataFrame(rows)
out_path = "HP_Extreme_Weather_RAG/reports/district_aggregation_validation.csv"
out_df.to_csv(out_path, index=False)
print("Updated district aggregation validation with rounding precision:", (out_df['status'] == 'PASS').sum(), "/ 20 PASS")
