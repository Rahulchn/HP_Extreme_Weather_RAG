"""
HP Extreme Weather RAG - Source Acquisition Script
Strictly enforces User Correction #5, #7, #10 (Data Lineage & Provenance),
and Section 12 (acquisition_log.md).
"""

import os
import sys
import time
import hashlib
import requests
import urllib3
from pathlib import Path

# Suppress insecure HTTPS warnings for government legacy certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ACQUISITION_LOG_PATH = REPORTS_DIR / "acquisition_log.md"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

DOWNLOAD_CATALOG = [
    # --- IMD SHIMLA OFFICIAL METEOROLOGICAL REPORTS ---
    {
        "category": "rainfall",
        "filename": "imd_shimla_yearlymonsoon_2004_2025.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/yearlymonsoon.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "Historical SouthWest Monsoon cumulative rainfall dataset (2004-2025) for Himachal Pradesh districts."
    },
    {
        "category": "rainfall",
        "filename": "imd_shimla_monsoon_report_2023.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/monsoon2023.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "SouthWest Monsoon 2023 comprehensive seasonal and extreme event report."
    },
    {
        "category": "rainfall",
        "filename": "imd_shimla_rainfallmonthly_2023.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/rainfallmonthly2023.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "District-wise monthly rainfall totals and departures for 2023."
    },
    {
        "category": "rainfall",
        "filename": "imd_shimla_three_hourly_telemetry_2026.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/three_hourly.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "Official 3-hourly telemetry rainfall observations across HP stations for 2026 (PARTIAL year)."
    },
    {
        "category": "rainfall",
        "filename": "imd_shimla_daily_bulletin_2026.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/daily.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "Daily precipitation observation bulletin for Himachal Pradesh stations (2026 PARTIAL)."
    },
    {
        "category": "rainfall",
        "filename": "imd_shimla_chief_rainfall_2026.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/chief.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "Chief amounts of heavy rainfall recorded across Himachal Pradesh stations (2026 PARTIAL)."
    },
    {
        "category": "rainfall",
        "filename": "imd_climatology_kangra.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/cli_kangra.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "Official Climate Normals and Extreme Rainfall Records for Kangra District (Dharamshala, Kangra Aero)."
    },
    {
        "category": "rainfall",
        "filename": "imd_climatology_mandi.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/cli_mandi.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "Official Climate Normals and Extreme Rainfall Records for Mandi District (Sundernagar, Mandi)."
    },
    {
        "category": "rainfall",
        "filename": "imd_climatology_shimla.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/cli_shimla2.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "Official Climate Normals and Extreme Rainfall Records for Shimla District (Shimla City, Kufri)."
    },
    {
        "category": "rainfall",
        "filename": "imd_climatology_kullu.pdf",
        "url": "https://mausam.imd.gov.in/shimla/mcdata/cli_kullu.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "IMD MC Shimla",
        "description": "Official Climate Normals and Extreme Rainfall Records for Kullu District (Bhuntar Aero, Manali)."
    },

    # --- HP SDMA DISASTER REPORTS & POST DISASTER ASSESSMENTS ---
    {
        "category": "disaster_reports",
        "filename": "hpsdma_pdna_monsoon_2023.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3788",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "Master Post Disaster Needs Assessment (PDNA) Monsoon 2023 detailing extreme events, cloudbursts, and flash floods."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_10year_losses_2016_2025.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=4041",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "Last 10 Years (2016-2025) Losses Due to Various Disasters in Himachal Pradesh (Cloudbursts, Flash Floods, Landslides)."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2023.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3573",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2023 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2024.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3664",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2024 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2025.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3806",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2025 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2022.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3520",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2022 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2021.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3487",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2021 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2020.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3372",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2020 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2019.pdf",
        "url": "https://hpsdma.hp.gov.in/WriteReadData/LINKS/0f5c2230-7150-4899-b290-df40ea8287e8.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2019 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2018.pdf",
        "url": "https://hpsdma.hp.gov.in/WriteReadData/LINKS/c237c1ce-1102-4dce-853a-3472e83bed19.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2018 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2017.pdf",
        "url": "https://hpsdma.hp.gov.in/WriteReadData/LINKS/5a99ba541-0548-4774-a08a-dc47f1f50aa6.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2017 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2016.pdf",
        "url": "https://hpsdma.hp.gov.in/WriteReadData/LINKS/a4f792cb-73a9-440a-a1ad-f4669dd497eb.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2016 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_memo_monsoon_2013_2015.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3633",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA",
        "description": "State Memorandum of damages during Monsoon-2013-15 submitted to Government of India."
    },
    {
        "category": "disaster_reports",
        "filename": "hpsdma_disaster_analysis_lr3_2007_2015.pdf",
        "url": "https://hpsdma.hp.gov.in/WriteReadData/LINKS/250a3928a-f478-4f12-ada3-1fc6983f0626.pdf",
        "method": "GET",
        "post_data": None,
        "organization": "HP SDMA / TARU",
        "description": "Longitudinal Disaster Analysis (Loss, Rescue Relief & Rehabilitation LR3 2007-15) covering historical cloudbursts and floods."
    },

    # --- CLOUDBURST & FLASH FLOOD SCIENTIFIC FIELD REPORTS ---
    {
        "category": "flash_flood",
        "filename": "gsi_kotrupi_mandi_investigation.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3472",
        "method": "GET",
        "post_data": None,
        "organization": "Geological Survey of India (GSI)",
        "description": "GSI Geological Assessment of Kotrupi Landslide & Flash Debris Flow (Mandi district)."
    },
    {
        "category": "flash_flood",
        "filename": "gsi_boh_kangra_investigation.pdf",
        "url": "https://hpsdma.hp.gov.in/admnis/admin/showimg.aspx?ID=3475",
        "method": "GET",
        "post_data": None,
        "organization": "Geological Survey of India (GSI)",
        "description": "GSI Scientific Note on Boh Flash Flood & Landslide Incident (Kangra district)."
    },

    # --- IMD PUNE 0.25° DAILY GRIDDED RAINFALL MATRIX ---
    {
        "category": "rainfall",
        "filename": "imd_gridded_rain_2023.grd",
        "url": "https://imdpune.gov.in/cmpg/Griddata/rainfall.php",
        "method": "POST",
        "post_data": {"rain": 2023},
        "organization": "IMD Pune (CRS)",
        "description": "Official 0.25° x 0.25° daily gridded binary rainfall matrix for year 2023 (135x129 grid points, 365 days)."
    },
    {
        "category": "rainfall",
        "filename": "imd_gridded_rain_2021.grd",
        "url": "https://imdpune.gov.in/cmpg/Griddata/rainfall.php",
        "method": "POST",
        "post_data": {"rain": 2021},
        "organization": "IMD Pune (CRS)",
        "description": "Official 0.25° x 0.25° daily gridded binary rainfall matrix for year 2021."
    },
    {
        "category": "rainfall",
        "filename": "imd_gridded_rain_2018.grd",
        "url": "https://imdpune.gov.in/cmpg/Griddata/rainfall.php",
        "method": "POST",
        "post_data": {"rain": 2018},
        "organization": "IMD Pune (CRS)",
        "description": "Official 0.25° x 0.25° daily gridded binary rainfall matrix for year 2018."
    }
]

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def download_file(item, max_retries=3):
    cat_dir = DATA_RAW / item["category"]
    cat_dir.mkdir(parents=True, exist_ok=True)
    target_path = cat_dir / item["filename"]

    # If already downloaded and non-empty, check validity
    if target_path.exists() and target_path.stat().st_size > 1024:
        sha = compute_sha256(target_path)
        size_bytes = target_path.stat().st_size
        print(f"[CACHE HIT] {item['filename']} ({size_bytes / 1024 / 1024:.2f} MB)")
        return {
            "status": "CACHED",
            "size_bytes": size_bytes,
            "sha256": sha,
            "error": None
        }

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[DOWNLOADING] ({attempt}/{max_retries}) {item['filename']} from {item['url']} ...")
            if item["method"] == "GET":
                resp = requests.get(item["url"], headers=HEADERS, verify=False, timeout=30, stream=True)
            elif item["method"] == "POST":
                resp = requests.post(item["url"], data=item["post_data"], headers=HEADERS, verify=False, timeout=45, stream=True)

            resp.raise_for_status()

            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            size_bytes = target_path.stat().st_size
            if size_bytes < 100:
                target_path.unlink(missing_ok=True)
                raise ValueError(f"Downloaded payload suspiciously small: {size_bytes} bytes")

            sha = compute_sha256(target_path)
            print(f"[SUCCESS] {item['filename']} -> {size_bytes / 1024 / 1024:.2f} MB (SHA-256: {sha[:16]}...)")
            return {
                "status": "DOWNLOADED",
                "size_bytes": size_bytes,
                "sha256": sha,
                "error": None
            }
        except Exception as e:
            print(f"[WARNING] Attempt {attempt} failed for {item['filename']}: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                return {
                    "status": "FAILED",
                    "size_bytes": 0,
                    "sha256": "N/A",
                    "error": str(e)
                }

def run_acquisition():
    print("=" * 70)
    print("EXECUTING SOURCE ACQUISITION: HIMACHAL PRADESH EXTREME WEATHER RAG")
    print("=" * 70)

    log_entries = []
    total = len(DOWNLOAD_CATALOG)

    for i, item in enumerate(DOWNLOAD_CATALOG, 1):
        print(f"\n[{i}/{total}] Processing {item['filename']} ...")
        res = download_file(item)
        log_entries.append({
            "item": item,
            "result": res
        })

    # Write reports/acquisition_log.md
    print(f"\nGenerating acquisition log at {ACQUISITION_LOG_PATH} ...")
    with open(ACQUISITION_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("# Himachal Pradesh Extreme Weather RAG: Acquisition Log\n\n")
        f.write(f"**Execution Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
        f.write(f"**Total Catalog Items**: {total}\n\n")
        f.write("---\n\n")
        f.write("## Acquired Raw Datasets & Documents\n\n")
        f.write("| File Name | Category | Organization | Size (MB) | Status | SHA-256 Hash | Source URL |\n")
        f.write("|---|---|---|---|---|---|---|\n")

        for entry in log_entries:
            it = entry["item"]
            res = entry["result"]
            size_mb = f"{res['size_bytes'] / 1024 / 1024:.2f}" if res['size_bytes'] > 0 else "0.00"
            f.write(f"| `{it['filename']}` | {it['category']} | {it['organization']} | {size_mb} | {res['status']} | `{res['sha256'][:16]}...` | [{it['url']}]({it['url']}) |\n")

        f.write("\n---\n\n")
        f.write("## Lineage and Provenance Notes\n\n")
        for entry in log_entries:
            it = entry["item"]
            res = entry["result"]
            f.write(f"### `{it['filename']}`\n")
            f.write(f"- **Organization**: {it['organization']}\n")
            f.write(f"- **Description**: {it['description']}\n")
            f.write(f"- **Acquisition Method**: {it['method']}\n")
            f.write(f"- **Full SHA-256**: `{res['sha256']}`\n")
            f.write(f"- **Source URL**: {it['url']}\n")
            if res['error']:
                f.write(f"- **Errors Encountered**: {res['error']}\n")
            f.write("\n")

    print(f"[SUCCESS] Acquisition log successfully generated: {ACQUISITION_LOG_PATH}")

if __name__ == "__main__":
    run_acquisition()
