import os
import sys
import hashlib
import time
import urllib3
import requests
import ssl
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_RAIN = PROJECT_ROOT / "data" / "raw" / "rainfall"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_RAW_RAIN.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

ACQUISITION_CSV = REPORTS_DIR / "rainfall_acquisition_by_year.csv"

class HostHeaderSSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount('https://', HostHeaderSSLAdapter())

url = 'https://imdpune.gov.in/cmpg/Griddata/rainfall.php'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def is_leap_year(y):
    return (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))

acquisition_records = []

print("=== ACQUIRING OFFICIAL IMD 0.25° GRIDDED RAINFALL (2011–2026) ===")

for year in range(2011, 2027):
    # 2026 is current / in-progress year
    if year == 2026:
        acquisition_records.append({
            "year": 2026,
            "source": "IMD Pune (CRS) 0.25° Gridded",
            "requested": "NO",
            "downloaded": "NO",
            "file_present": "NO",
            "file_size": 0,
            "sha256": "N/A",
            "expected_structure": "N/A",
            "acquisition_status": "PARTIAL_YEAR_NOT_RELEASED_IN_ANNUAL_GRID",
            "failure_reason": "Annual gridded binary matrix released by IMD Pune only post-calendar year completion. 2026 tracked via IMD MC Shimla live telemetry bulletins."
        })
        continue

    is_leap = is_leap_year(year)
    num_days = 366 if is_leap else 365
    expected_size = 129 * 135 * 4 * num_days
    expected_structure = f"129x135x4x{num_days} ({expected_size:,} bytes)"
    
    target_file = DATA_RAW_RAIN / f"imd_gridded_rain_{year}.grd"
    
    # Check if already present and valid
    if target_file.exists() and target_file.stat().st_size == expected_size:
        size = target_file.stat().st_size
        sha = compute_sha256(target_file)
        print(f"[{year}] ALREADY PRESENT & VERIFIED: {target_file.name} ({size:,} bytes, SHA: {sha[:16]}...)")
        acquisition_records.append({
            "year": year,
            "source": "IMD Pune (CRS) 0.25° Gridded",
            "requested": "YES",
            "downloaded": "PREVIOUSLY_DOWNLOADED",
            "file_present": "YES",
            "file_size": size,
            "sha256": sha,
            "expected_structure": expected_structure,
            "acquisition_status": "VERIFIED_ON_DISK",
            "failure_reason": "NONE"
        })
        continue
    
    # Download
    print(f"[{year}] Downloading from {url} ...")
    max_retries = 3
    success = False
    fail_reason = "NONE"
    
    for attempt in range(1, max_retries + 1):
        try:
            r = session.post(url, data={'rain': year}, headers=headers, verify=False, timeout=60, stream=True)
            if r.status_code != 200:
                fail_reason = f"HTTP status {r.status_code}"
                continue
            
            # Temporary file first to prevent partial corruption
            temp_file = DATA_RAW_RAIN / f"temp_{year}.grd"
            with open(temp_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=131072):
                    if chunk:
                        f.write(chunk)
            
            actual_size = temp_file.stat().st_size
            if actual_size == expected_size:
                # Atomically rename
                temp_file.replace(target_file)
                sha = compute_sha256(target_file)
                print(f"[{year}] SUCCESS: {target_file.name} ({actual_size:,} bytes, SHA: {sha[:16]}...)")
                acquisition_records.append({
                    "year": year,
                    "source": "IMD Pune (CRS) 0.25° Gridded",
                    "requested": "YES",
                    "downloaded": "YES",
                    "file_present": "YES",
                    "file_size": actual_size,
                    "sha256": sha,
                    "expected_structure": expected_structure,
                    "acquisition_status": "DOWNLOADED_AND_VERIFIED",
                    "failure_reason": "NONE"
                })
                success = True
                break
            elif actual_size > 1000 and actual_size != expected_size:
                # Could be 365 days instead of 366 or vice versa, or partial year (e.g. 2025)
                # Let's inspect days
                pts_per_day = 129 * 135 * 4
                days_got = actual_size // pts_per_day
                rem = actual_size % pts_per_day
                if rem == 0 and days_got > 0:
                    temp_file.replace(target_file)
                    sha = compute_sha256(target_file)
                    print(f"[{year}] ACCEPTED WITH DAYS={days_got}: {target_file.name} ({actual_size:,} bytes, SHA: {sha[:16]}...)")
                    acquisition_records.append({
                        "year": year,
                        "source": "IMD Pune (CRS) 0.25° Gridded",
                        "requested": "YES",
                        "downloaded": "YES",
                        "file_present": "YES",
                        "file_size": actual_size,
                        "sha256": sha,
                        "expected_structure": f"129x135x4x{days_got} ({actual_size:,} bytes)",
                        "acquisition_status": "DOWNLOADED_PARTIAL_DAYS",
                        "failure_reason": f"Expected {num_days} days ({expected_size} bytes), got {days_got} days"
                    })
                    success = True
                    break
                else:
                    temp_file.unlink(missing_ok=True)
                    fail_reason = f"Size mismatch: expected {expected_size} bytes, received {actual_size} bytes"
            else:
                temp_file.unlink(missing_ok=True)
                fail_reason = f"Downloaded payload too small: {actual_size} bytes"
        except Exception as e:
            fail_reason = f"Exception: {str(e)}"
            time.sleep(2)
            
    if not success:
        print(f"[{year}] FAILED: {fail_reason}")
        acquisition_records.append({
            "year": year,
            "source": "IMD Pune (CRS) 0.25° Gridded",
            "requested": "YES",
            "downloaded": "NO",
            "file_present": "NO",
            "file_size": 0,
            "sha256": "N/A",
            "expected_structure": expected_structure,
            "acquisition_status": "DOWNLOAD_FAILED",
            "failure_reason": fail_reason
        })

# Write CSV report
import csv
with open(ACQUISITION_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "year", "source", "requested", "downloaded", "file_present",
        "file_size", "sha256", "expected_structure", "acquisition_status", "failure_reason"
    ])
    writer.writeheader()
    writer.writerows(acquisition_records)

print(f"\nAcquisition report successfully saved to: {ACQUISITION_CSV}")
