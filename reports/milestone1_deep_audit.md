# FORENSIC DEEP AUDIT: MILESTONE 1 DATA FOUNDATION
**Himachal Pradesh Extreme Weather RAG System (2011–2026)**  
**Districts Audited:** Kangra, Mandi, Shimla, Kullu  
**Parameters Audited:** Rainfall, Cloudburst, Flash Flood  
**Audit Date:** September 7, 2026  
**Auditor:** Lead Data Engineer & Forensic Data Auditor  
**Final Classification:** `NOT_READY — DATA REPAIR REQUIRED`

---

## EXECUTIVE SUMMARY

A forensic inspection of the generated data foundation for Milestone 1 was conducted. While earlier automated pipeline logs reported Milestone 1 as "fully verified", an audit of the underlying datasets reveals a **critical, systemic data-completeness failure**:

1. **Catastrophic Rainfall Missingness (99.9665% Missing):**  
   Out of **86,534 total rainfall records**, exactly **29 are VALID** and **86,505 are marked MISSING** (NaN). The valid observation percentage is **0.0335%**, rendering the daily rainfall dataset completely unusable in its current state.
2. **Smoking Gun Root Cause Identified:**  
   The missingness is **NOT caused by missing source data**. The raw binary files (`imd_gridded_rain_2018.grd`, `2021.grd`, `2023.grd`) contain dense, valid rainfall values over Himachal Pradesh. The catastrophic missingness was caused by a **matrix dimension inversion bug in `clean_data.py`**. The parser reshaped the daily binary array as `(135, 129)` (treating axes as `[lon, lat]`) instead of the true IMD Pune layout of `(129, 135)` (`[lat, lon]`). Consequently, the parser sampled coordinates in the high Tibetan Plateau outside India's land boundary, where all values are IMD nodata sentinels (`-999.0`).
3. **Temporal Gaps in Gridded Data:**  
   Only 3 out of 16 years (2018, 2021, 2023) were downloaded for IMD gridded data. 9 completed years (2012, 2013, 2015, 2016, 2019, 2020, 2022, 2024, 2025) lack daily gridded records because the initial acquisition catalog was truncated, despite data being available on the IMD Pune portal.
4. **Event Deduplication & Coverage Verification:**  
   The event dataset contains 27 canonical events derived from 28 source event records (17 cloudbursts, 11 flash floods). The merge of 28 into 27 is fully verified: on `2021-07-12` in Dharamshala/Boh (Kangra), an SDMA cloudburst record and a GSI flash flood report represent the identical physical event and were appropriately unified. However, several years (2012, 2013, 2015, 2016, 2025) have multi-megabyte official loss memorandums sitting unparsed in `data/raw/disaster_reports/`, creating artificial "NO_DATA" holes in the historical timeline.

---

## 1. CRITICAL RAINFALL AUDIT

### 1.1 Metrics & Proportions
* **Total Rainfall Records:** 86,534
* **Valid Observations:** 29
* **Missing Observations:** 86,505
* **Valid Percentage:** **0.0335%**
* **Missing Percentage:** **99.9665%**

### 1.2 Forensic Q&A Diagnosis

| # | Question | Finding & Forensic Evidence |
|---|---|---|
| **1** | **Are the original rainfall values actually present in the raw files?** | **YES.** Forensic binary inspection of `imd_gridded_rain_2018.grd`, `2021.grd`, and `2023.grd` proves that valid float32 values (ranging from 0.0 mm to >246 mm) are physically present in the binary payload for every single day. |
| **2** | **Were values lost during parsing?** | **YES.** 86,505 values were converted to `NaN` during parsing because the parser queried the wrong memory offsets. |
| **3** | **Was the wrong binary format interpreted?** | **PARTIALLY.** The data type (`float32`, little-endian) was correct, but the **2D array shape and axis ordering were inverted**. |
| **4** | **Were nodata/sentinel values incorrectly converted to NULL?** | **YES.** The sentinel value `-999.0` was correctly identified as nodata, but because the parser looked at the wrong geographical coordinates, valid HP points were never read; only `-999.0` sentinels were read and converted to NULL. |
| **5** | **Was the IMD gridded binary matrix decoded correctly?** | **NO.** The IMD Pune 0.25° grid documentation specifies 129 latitude points (6.5°N to 38.5°N) and 135 longitude points (66.5°E to 100.0°E). The data is stored row-major as `[lat_idx, lon_idx]` (129 rows × 135 columns). The parser executed `reshape((135, 129))`, inverting row and column strides. |
| **6** | **Were latitude/longitude indexes mapped correctly?** | **NO.** Because of the `(135, 129)` inversion, the formula `grid[lon_idx, lat_idx]` effectively accessed latitude index 98–104 and longitude index 37–46, pointing into unmasked Tibetan territory outside the Indian subcontinent mask where the matrix is populated exclusively with `-999.0`. |
| **7** | **Was the rainfall unit interpreted correctly?** | **YES.** The unit is millimeters (`mm`), matching IMD standards. |
| **8** | **Did the parser extract only metadata rather than observations?** | **NO.** The parser attempted to read grid cells, but due to the spatial index inversion, read 86,505 consecutive sentinel values. |
| **9** | **Are the 29 valid observations genuine?** | **YES.** All 29 valid observations originate from **station reports, telemetry bulletins, and climatological tables** (e.g., Dharamshala 226 mm on 2021-07-12, Shimla 146 mm on 2023-07-10, Mandi 62 mm on 2026-08-01). None came from the gridded matrix. |
| **10** | **Is the missingness caused by source data or by our processing pipeline?** | **PROCESSING PIPELINE FAILURE.** The IMD source data is intact and dense. The missingness is 100% attributable to the matrix reshape bug in `clean_data.py`. |

---

## 2. RAINFALL COMPLETENESS BY YEAR (2011–2026)

Full counts from `reports/rainfall_completeness_by_year.csv`:

| Year | Total Records | Valid Records | Missing Records | Valid % | Missing % | Status |
|---|---:|---:|---:|---:|---:|---|
| **2011** | 1 | 1 | 0 | 100.00% | 0.00% | Station Report Only (Climatological normal/extreme) |
| **2012** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2013** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2014** | 1 | 1 | 0 | 100.00% | 0.00% | Station Report Only |
| **2015** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2016** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2017** | 2 | 2 | 0 | 100.00% | 0.00% | Station Report Only |
| **2018** | 28,839 | 4 | 28,835 | 0.01% | 99.99% | Gridded matrix parsed with dimension inversion |
| **2019** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2020** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2021** | 28,838 | 3 | 28,835 | 0.01% | 99.99% | Gridded matrix parsed with dimension inversion |
| **2022** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2023** | 28,845 | 10 | 28,835 | 0.03% | 99.97% | Gridded matrix parsed with dimension inversion |
| **2024** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2025** | 0 | 0 | 0 | 0.00% | 0.00% | Genuinely missing from processed table |
| **2026** | 8 | 8 | 0 | 100.00% | 0.00% | Telemetry & Daily Station Bulletins (PARTIAL) |
| **TOTAL** | **86,534** | **29** | **86,505** | **0.0335%** | **99.9665%** | **CRITICAL PIPELINE DEFECT** |

---

## 3. RAINFALL COMPLETENESS BY DISTRICT

Full counts from `reports/rainfall_completeness_by_district.csv`:

| District | Total Records | Valid Records | Missing Records | Valid % | Missing % | Primary Cause of Defect |
|---|---:|---:|---:|---:|---:|---|
| **Kangra** | 30,669 | 9 | 30,660 | 0.03% | 99.97% | Gridded cell extraction inverted (28 cells × 365 days × 3 yrs) |
| **Mandi** | 21,908 | 8 | 21,900 | 0.04% | 99.96% | Gridded cell extraction inverted (20 cells × 365 days × 3 yrs) |
| **Shimla** | 16,430 | 5 | 16,425 | 0.03% | 99.97% | Gridded cell extraction inverted (15 cells × 365 days × 3 yrs) |
| **Kullu** | 17,527 | 7 | 17,520 | 0.04% | 99.96% | Gridded cell extraction inverted (16 cells × 365 days × 3 yrs) |
| **TOTAL** | **86,534** | **29** | **86,505** | **0.03%** | **99.97%** | All 4 target districts equally disabled |

---

## 4. RAINFALL COMPLETENESS BY SOURCE TYPE

Full counts from `reports/rainfall_completeness_by_source.csv`:

| Source Type | Records | Valid | Missing | Coverage Years | Completeness Assessment |
|---|---:|---:|---:|---|---|
| **IMD_GRIDDED_SPATIAL_DATA** | 86,505 | 0 | 86,505 | 2018, 2021, 2023 | **0.00% Valid (Completely Broken)** |
| **IMD_STATION_OR_DISTRICT_OBSERVATION** | 29 | 29 | 0 | 2011, 2014, 2017, 2018, 2021, 2023, 2026 | **100.00% Valid** (High precision, but sparse) |
| **IMD_TELEMETRY** (Sub-type) | 4 | 4 | 0 | 2026 (Live bulletins) | **100.00% Valid** (Current season) |
| **IMD_REPORT_TABLE** (Sub-type) | 25 | 25 | 0 | 2011–2023 (Monsoon reports) | **100.00% Valid** (Extreme event benchmarks) |

---

## 5. INSPECTION OF RAW IMD GRIDDED BINARY DATA

### 5.1 Binary Specifications
* **Grid Resolution:** 0.25° × 0.25°
* **Latitude Range:** 6.5° N to 38.5° N ($N_{lat} = 129$ grid points, increment 0.25°)
* **Longitude Range:** 66.5° E to 100.0° E ($N_{lon} = 135$ grid points, increment 0.25°)
* **Total Grid Cells per Day:** $129 \times 135 = 17,415$ cells
* **Bytes per Cell:** 4 bytes (IEEE 754 single-precision float32, little-endian)
* **Bytes per Day:** $17,415 \times 4 = 69,660$ bytes
* **Days per Non-Leap Year (2018, 2021, 2023):** 365 days
* **Expected File Size:** $69,660 \times 365 = 25,425,900$ bytes
* **Actual File Size on Disk:** Exactly **25,425,900 bytes** (100% byte integrity verified)
* **Nodata / Sentinel Value:** `-999.0`
* **Rainfall Unit:** Millimeters (`mm`)

### 5.2 Independent Raw-to-Decoded Verification (10 Random Spot Checks)
To prove that rainfall values exist in the raw files, we extracted 10 random space-time coordinates using the correct `(129, 135)` layout and compared them against the existing processed CSV:

| # | Date | District | Grid Lat | Grid Lon | Raw Binary Hex | Decoded Value (Correct layout) | Existing Processed CSV Value | Status |
|---|---|---|---:|---:|---|---:|---:|---|
| **1** | 2023-07-09 | Kullu | 31.75°N | 77.25°E | `0xcd 0x56 0xf1 0x42` | **120.67 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **2** | 2023-07-09 | Mandi | 31.50°N | 77.00°E | `0x8f 0x47 0xbe 0x42` | **95.14 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **3** | 2023-07-10 | Shimla | 31.25°N | 77.25°E | `0x33 0x33 0xa3 0x42` | **81.60 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **4** | 2023-08-14 | Kangra | 32.25°N | 76.25°E | `0x71 0x68 0x76 0x43` | **246.81 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **5** | 2023-08-14 | Mandi | 31.75°N | 76.75°E | `0xec 0x51 0xba 0x42` | **93.16 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **6** | 2021-07-12 | Kangra | 32.25°N | 76.25°E | `0xd7 0xa3 0x41 0x43` | **193.64 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **7** | 2018-09-23 | Kullu | 32.00°N | 77.25°E | `0x52 0xb8 0x86 0x42` | **67.36 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **8** | 2018-09-24 | Kangra | 32.00°N | 76.50°E | `0x1f 0x85 0xeb 0x41` | **29.44 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **9** | 2023-01-15 | Shimla | 31.00°N | 77.25°E | `0x00 0x00 0x00 0x00` | **0.00 mm** | `NaN (MISSING)` | **RECOVERABLE** |
| **10**| 2018-06-15 | Mandi | 31.75°N | 77.00°E | `0x66 0x66 0x96 0x41` | **18.80 mm** | `NaN (MISSING)` | **RECOVERABLE** |

**Conclusion:** The raw data contains genuine, high-magnitude, research-grade rainfall values. The bug in `clean_data.py` turned 100% of these valid observations into `NaN`.

---

## 6. DIAGNOSIS OF "MISSING YEARS"

The 9 missing years in the gridded daily series (2012, 2013, 2015, 2016, 2019, 2020, 2022, 2024, 2025) were audited:

| Year | Raw Source Available | Raw Data Present in `data/raw/` | Processed Data Present | Reason for Gap | Category | Recommended Fix |
|---|---|---|---|---|---|---|
| **2012** | YES (IMD Pune) | NO | NO | Hardcoded download script only fetched [2018, 2021, 2023] | C (Available upstream) | Download `rain_val_2012.grd` via HTTP POST |
| **2013** | YES (IMD Pune & HPSDMA) | YES (HPSDMA memo), NO (Gridded) | NO | Gridded file unrequested; HPSDMA 2013 memo unparsed | C / D | Download 2013 gridded binary; extract memo tables |
| **2015** | YES (IMD Pune & HPSDMA) | YES (HPSDMA memo), NO (Gridded) | NO | Gridded file unrequested; HPSDMA 2015 memo unparsed | C / D | Download 2015 gridded binary; extract memo tables |
| **2016** | YES (IMD Pune & HPSDMA) | YES (HPSDMA memo), NO (Gridded) | NO | Gridded file unrequested; HPSDMA 2016 memo unparsed | C / D | Download 2016 gridded binary; extract memo tables |
| **2019** | YES (IMD Pune & HPSDMA) | YES (HPSDMA memo), NO (Gridded) | NO | Gridded file unrequested | C | Download 2019 gridded binary via HTTP POST |
| **2020** | YES (IMD Pune & HPSDMA) | YES (HPSDMA memo), NO (Gridded) | NO | Gridded file unrequested | C | Download 2020 gridded binary via HTTP POST |
| **2022** | YES (IMD Pune & HPSDMA) | YES (HPSDMA memo), NO (Gridded) | NO | Gridded file unrequested | C | Download 2022 gridded binary via HTTP POST |
| **2024** | YES (IMD Pune & HPSDMA) | YES (HPSDMA memo), NO (Gridded) | NO | Gridded file unrequested | C | Download 2024 gridded binary via HTTP POST |
| **2025** | YES (HPSDMA Memo) | YES (HPSDMA memo), NO (Gridded) | NO | IMD Pune releases completed years; 2025 gridded delayed | C / A | Parse 2025 HPSDMA memo; download 2025 when released |

---

## 7. VERIFICATION OF 2026

* **2026 Earliest Date:** `2026-08-01`
* **2026 Latest Date:** `2026-09-07`
* **2026 Total Records:** 8
* **2026 Valid Records:** 8
* **2026 Missing Records:** 0
* **Data Sources:** 
  - `imd_shimla_daily_bulletin_2026.pdf` (Table 1: Daily Precipitation)
  - `imd_shimla_three_hourly_telemetry_2026.pdf` (Table 1: 3-Hourly Telemetry)
* **Temporal Status:** Strictly maintained as `year_status = PARTIAL`. No missing observations are fabricated or interpolated.

---

## 8. EVENT DATA AUDIT & DEDUPLICATION

### 8.1 Summary
* **Raw Extracted Records:** 28 (17 Cloudbursts + 11 Flash Floods)
* **Canonical Deduplicated Events:** 27
* **Provenance Links:** 32 links preserved in `reports/event_source_mapping.csv`

### 8.2 Why 28 Became 27: The Canonical Merge
On **July 12, 2021**, a major disaster occurred in Kangra district affecting Dharamshala, Bhagsunag, and Boh village:
1. **Source Record 1 (`CB_2021_KANGRA_001`):** Recorded from HP SDMA Monsoon Memorandum 2021 (p. 18) as a "Cloudburst in Dharamshala/Boh" (10 fatalities, houses destroyed).
2. **Source Record 2 (`FF_2021_KANGRA_001`):** Recorded from GSI Special Geological Report on Boh Landslide/Flash Flood as "Flash flood in Manjhi Khad and Gaj Khad" (10 fatalities, bridge scouring).

**The Deduplication Rule:**
Because both records share:
- Exactly the same calendar date (`2021-07-12`)
- Exactly the same administrative district (`Kangra`)
- Co-located catchments (Bhagsunag - Boh - Dharamshala)
- Identical casualty counts (10 deaths)

They were correctly merged into canonical event **`CANON_20210712_KAN_DHA`** with derived classification **`Cloudburst and Flash Flood`** ($confidence = HIGH$). Both source citations, page numbers, and quotes are retained in `reports/event_source_mapping.csv`. No data was destroyed.

### 8.3 Canonical Event Registry (All 27 Events)
See complete table in [event_deduplication_audit.csv](file:///c:/Users/rahul/Desktop/RAG/HP_Extreme_Weather_RAG/reports/event_deduplication_audit.csv).

---

## 9. EVENT COVERAGE MATRIX (2011–2026)

Full matrix distinguishing `DOCUMENTED_EVENTS` from unparsed raw source archives (`NO_DATA`):

| Year | Kangra | Mandi | Shimla | Kullu | Cloudburst | Flash Flood | Coverage Status |
|---|---:|---:|---:|---:|---:|---:|---|
| **2011** | 0 | 0 | 1 | 0 | 1 | 0 | DOCUMENTED_EVENTS |
| **2012** | NA | NA | NA | NA | NA | NA | NO_DATA (Raw memo present in `data/raw/`, unparsed) |
| **2013** | NA | NA | NA | NA | NA | NA | NO_DATA (Raw memo present in `data/raw/`, unparsed) |
| **2014** | 0 | 1 | 0 | 1 | 1 | 1 | DOCUMENTED_EVENTS |
| **2015** | NA | NA | NA | NA | NA | NA | NO_DATA (Raw memo present in `data/raw/`, unparsed) |
| **2016** | NA | NA | NA | NA | NA | NA | NO_DATA (Raw memo present in `data/raw/`, unparsed) |
| **2017** | 0 | 1 | 0 | 0 | 1 | 0 | DOCUMENTED_EVENTS |
| **2018** | 0 | 0 | 0 | 2 | 1 | 1 | DOCUMENTED_EVENTS |
| **2019** | 0 | 0 | 2 | 0 | 1 | 1 | DOCUMENTED_EVENTS |
| **2020** | 0 | 0 | 0 | 1 | 1 | 0 | DOCUMENTED_EVENTS |
| **2021** | 1 | 0 | 1 | 1 | 2 | 2 | DOCUMENTED_EVENTS |
| **2022** | 1 | 2 | 0 | 1 | 2 | 2 | DOCUMENTED_EVENTS |
| **2023** | 2 | 2 | 2 | 2 | 4 | 4 | DOCUMENTED_EVENTS |
| **2024** | 0 | 1 | 1 | 1 | 3 | 0 | DOCUMENTED_EVENTS |
| **2025** | NA | NA | NA | NA | NA | NA | NO_DATA (Raw memo present in `data/raw/`, unparsed) |
| **2026** | 0 | 0 | 0 | 0 | 0 | 0 | PARTIAL (Current season, no major event recorded to date) |

---

## 10. SOURCE COVERAGE & REGISTRY AUDIT

Audit of all 10 sources from `reports/source_registry.csv` against physical files on disk:

| Source ID | Organization | Registry Years | Physical Files in `data/raw/` | Size on Disk | Registry Discrepancy / Conflict |
|---|---|---|---|---:|---|
| `SRC_IMD_GRIDDED_025` | IMD Pune | 2011–2025 | 3 files (`2018`, `2021`, `2023`) | 76.2 MB | **Registry claimed 2011–2025, but 9 years were never downloaded.** |
| `SRC_IMD_SHIMLA_DISTRICT_MONSOON` | IMD MC Shimla | 2011–2025 | 7 files (Monsoon reports, climatology, historical summary) | 7.9 MB | Verified on disk. Historical monsoon series covers 2004–2025. |
| `SRC_IMD_SHIMLA_TELEMETRY_2026` | IMD MC Shimla | 2026 | 3 files (Chief rainfall, daily bulletin, 3-hr telemetry) | 458 KB | Verified on disk. Correctly marked `PARTIAL`. |
| `SRC_HPSDMA_PDNA_2023` | HP SDMA | 2023 | 1 file (`hpsdma_pdna_monsoon_2023.pdf`) | 21.8 MB | Verified on disk. Comprehensive event descriptions. |
| `SRC_HPSDMA_PDNA_2025` | HP SDMA | 2025 | 0 files | 0 B | **Conflict:** Listed as available, but not downloaded (memorandum downloaded instead). |
| `SRC_HPSDMA_LOSS_MEMORANDUMS` | HP Revenue Dept | 2013–2025 | 11 master PDF memorandums | 345.9 MB | **Massive archive physically present, but 5 years remain unparsed.** |
| `SRC_HPSDMA_HISTORICAL_LOSS_2007_2015` | HPSDMA / TARU | 2007–2015 | 1 file (`hpsdma_disaster_analysis_lr3_2007_2015.pdf`) | 2.1 MB | Verified on disk. Covers 2011, 2014 baseline events. |
| `SRC_HPSDMA_10YR_LOSSES_2016_2025` | HPSDMA SEOC | 2016–2025 | 1 file (`hpsdma_10year_losses_2016_2025.pdf`) | 195 KB | Verified on disk. Tabular summary across all 12 districts. |
| `SRC_PARLIAMENT_MHA_MOES_QA` | MHA / MoES | 2018–2024 | 0 files | 0 B | **Conflict:** Cataloged from Lok/Rajya Sabha portal, but no local file stored. |
| `SRC_GSI_WADIA_EVENT_STUDIES` | GSI | 2017–2023 | 2 files (Kotrupi Mandi, Boh Kangra) | 3.0 MB | Verified on disk. Excellent geological & hydrometric ground truth. |

---

## 11. PROVENANCE LINEAGE AUDIT

30 randomly sampled records (10 rainfall, 10 cloudburst, 10 flash flood) were traced from processed output back to original source documents:

### 11.1 Rainfall Provenance Trace (10 Records)
1. **Record #1 (Gridded):** `2018-03-19`, Kangra $\to$ `imd_gridded_rain_2018.grd` $\to$ IMD Pune $\to$ `https://imdpune.gov.in/cmpg/Griddata/rainfall.php` $\to$ Grid Index (day=77, lat=31.75, lon=75.75).  
   *Audit:* **BROKEN IN PROCESSING.** Read as `NaN` due to index inversion; raw binary contains `0.00 mm`.
2. **Record #2 (Gridded):** `2018-04-26`, Kullu $\to$ `imd_gridded_rain_2018.grd` $\to$ IMD Pune $\to$ Grid Index (day=115, lat=31.75, lon=77.75).  
   *Audit:* **BROKEN IN PROCESSING.** Read as `NaN`; raw binary contains valid value.
3. **Record #3 (Gridded):** `2023-06-07`, Shimla $\to$ `imd_gridded_rain_2023.grd` $\to$ IMD Pune $\to$ Grid Index (day=157, lat=30.75, lon=77.25).  
   *Audit:* **BROKEN IN PROCESSING.** Read as `NaN`; raw binary contains valid value.
4. **Record #4 (Gridded):** `2018-02-12`, Shimla $\to$ `imd_gridded_rain_2018.grd` $\to$ IMD Pune $\to$ Grid Index (day=42, lat=31.25, lon=77.25).  
   *Audit:* **BROKEN IN PROCESSING.** Read as `NaN`; raw binary contains valid value.
5. **Record #5 (Gridded):** `2023-11-28`, Kullu $\to$ `imd_gridded_rain_2023.grd` $\to$ IMD Pune $\to$ Grid Index (day=331, lat=31.75, lon=77.25).  
   *Audit:* **BROKEN IN PROCESSING.** Read as `NaN`; raw binary contains valid value.
6. **Record #6 (Telemetry):** `2026-09-05`, Shimla $\to$ `imd_shimla_three_hourly_telemetry_2026.pdf` $\to$ IMD MC Shimla $\to$ `https://mausam.imd.gov.in/shimla/` $\to$ Table 1 $\to$ **28.5 mm**.  
   *Audit:* **PERFECT LINEAGE.**
7. **Record #7 (Station Report):** `2023-07-10`, Shimla $\to$ `imd_shimla_monsoon_report_2023.pdf` $\to$ IMD MC Shimla $\to$ Page 15, Table 3.3 $\to$ **146.0 mm**.  
   *Audit:* **PERFECT LINEAGE.**
8. **Record #8 (Station Report):** `2023-07-09`, Kullu $\to$ `imd_shimla_monsoon_report_2023.pdf` $\to$ IMD MC Shimla $\to$ Page 14, Table 3.2 $\to$ **120.0 mm**.  
   *Audit:* **PERFECT LINEAGE.**
9. **Record #9 (Station Report):** `2026-08-01`, Mandi $\to$ `imd_shimla_daily_bulletin_2026.pdf` $\to$ IMD MC Shimla $\to$ Table 1 $\to$ **62.0 mm**.  
   *Audit:* **PERFECT LINEAGE.**
10. **Record #10 (Station Report):** `2021-07-12`, Kangra $\to$ `imd_climatology_kangra.pdf` $\to$ IMD MC Shimla $\to$ Table 2 $\to$ **226.0 mm**.  
    *Audit:* **PERFECT LINEAGE.**

### 11.2 Cloudburst Provenance Trace (10 Records)
1. **`CB_2024_SHIMLA_001` (2024-07-31, Rampur/Samej):** Traced to `hpsdma_memo_monsoon_2024.pdf`, Annexure IV, Incident 12. Fatalities=33, 2 Hydro projects destroyed. **PERFECT LINEAGE.**
2. **`CB_2024_KULLU_001` (2024-07-31, Nirmand/Bagipul):** Traced to `hpsdma_memo_monsoon_2024.pdf`, Annexure IV, Incident 13. Fatalities=9, Bridge washed away. **PERFECT LINEAGE.**
3. **`CB_2024_MANDI_001` (2024-07-31, Padhar/Rajban):** Traced to `hpsdma_memo_monsoon_2024.pdf`, Annexure IV, Incident 14. Fatalities=10, 8 houses destroyed. **PERFECT LINEAGE.**
4. **`CB_2023_KULLU_001` (2023-07-09, Bhuntar/Gadsa):** Traced to `hpsdma_pdna_monsoon_2023.pdf`, Page 18, Table 1.2. Fatalities=4, Bridges washed away. **PERFECT LINEAGE.**
5. **`CB_2023_MANDI_001` (2023-07-09, Thunag):** Traced to `hpsdma_pdna_monsoon_2023.pdf`, Page 19, Table 1.3. Market submerged under 5ft debris. **PERFECT LINEAGE.**
6. **`CB_2023_SHIMLA_001` (2023-08-14, Summer Hill/Shiv Mandir):** Traced to `hpsdma_pdna_monsoon_2023.pdf`, Page 22. Fatalities=20, Shiv Bawadi temple collapsed. **PERFECT LINEAGE.**
7. **`CB_2022_MANDI_001` (2022-08-19, Gohar/Kashan):** Traced to `hpsdma_memo_monsoon_2022.pdf`, Annexure II, Event 9. Fatalities=8, Link road buried. **PERFECT LINEAGE.**
8. **`CB_2021_KANGRA_001` (2021-07-12, Dharamshala/Boh):** Traced to `hpsdma_memo_monsoon_2021.pdf`, Page 18 and `gsi_boh_kangra_investigation.pdf`. Fatalities=10. **PERFECT LINEAGE.**
9. **`CB_2020_KULLU_001` (2020-08-10, Anni/Pani Nullah):** Traced to `hpsdma_memo_monsoon_2020.pdf`, Table 1.4. Fatalities=2. **PERFECT LINEAGE.**
10. **`CB_2018_KULLU_001` (2018-09-23, Manali/Palchan):** Traced to `hpsdma_memo_monsoon_2018.pdf`, Page 15. Fatalities=3, Manali bus stand inundated. **PERFECT LINEAGE.**

### 11.3 Flash Flood Provenance Trace (10 Records)
1. **`FF_2023_KULLU_001` (2023-07-09, Beas River / Manali):** Traced to `hpsdma_pdna_monsoon_2023.pdf`, Page 19-20, Section 1.1.6. Fatalities=14, 40 shops washed away. **PERFECT LINEAGE.**
2. **`FF_2023_MANDI_001` (2023-07-09, Beas River / Panchvaktra):** Traced to `hpsdma_pdna_monsoon_2023.pdf`, Page 42, Section 3.8. Fatalities=9, Panchvaktra historic temple inundated. **PERFECT LINEAGE.**
3. **`FF_2023_KANGRA_001` (2023-08-14, Pong Reservoir / Indora):** Traced to `hpsdma_pdna_monsoon_2023.pdf`, Page 20. Fatalities=8, Air Force rescue of marooned villagers. **PERFECT LINEAGE.**
4. **`FF_2023_SHIMLA_001` (2023-07-10, Ashwani Khad / Giri River):** Traced to `hpsdma_pdna_monsoon_2023.pdf`, Page 35. Water pumping station for Shimla submerged. **PERFECT LINEAGE.**
5. **`FF_2022_MANDI_001` (2022-08-20, Suketi Khad / Balh):** Traced to `hpsdma_memo_monsoon_2022.pdf`, Annexure II, Event 11. Fatalities=6, Commercial centers flooded. **PERFECT LINEAGE.**
6. **`FF_2022_KANGRA_001` (2022-08-20, Chakki River / Nurpur):** Traced to `hpsdma_memo_monsoon_2022.pdf`, Annexure II, Event 12. Chakki railway bridge collapsed. **PERFECT LINEAGE.**
7. **`FF_2021_KANGRA_001` (2021-07-12, Manjhi Khad / Shahpur):** Traced to `gsi_boh_kangra_investigation.pdf` and `hpsdma_memo_monsoon_2021.pdf`. Fatalities=10. **PERFECT LINEAGE.**
8. **`FF_2021_KULLU_001` (2021-07-28, Brahma Ganga / Manikaran):** Traced to `hpsdma_memo_monsoon_2021.pdf`, Page 11. Fatalities=5, Trekking camps washed away. **PERFECT LINEAGE.**
9. **`FF_2019_SHIMLA_001` (2019-08-18, Pabbar River / Chirgaon):** Traced to `hpsdma_memo_monsoon_2019.pdf`, Page 24, Table 3.1. Fatalities=12, Andhra HEP intake choked. **PERFECT LINEAGE.**
10. **`FF_2014_MANDI_001` (2014-06-08, Beas River / Thalout):** Traced to `hpsdma_disaster_analysis_lr3_2007_2015.pdf`, Page 62. Fatalities=25, Engineering students swept away. **PERFECT LINEAGE.**

---

## 12. STRUCTURED DEFECT AUDIT & REPAIR PROPOSALS

### DEFECT 1: 2D Matrix Reshape Axis Inversion in `clean_data.py`
* **PROBLEM:** 86,505 out of 86,534 daily gridded rainfall values are extracted as `NaN` (99.97% missingness).
* **ROOT CAUSE:** In `clean_data.py`, `np.frombuffer` was reshaped as `(135, 129)` treating the axis as `[lon, lat]`. The IMD Pune binary standard is stored row-major as `(129, 135)` corresponding to `[lat, lon]`. The transposed index queried high-altitude points in Tibet where values are nodata `-999.0`.
* **IMPACT:** The entire gridded rainfall dataset for 2018, 2021, and 2023 is corrupted and unusable.
* **PROPOSED FIX:**
  1. Modify `clean_data.py` grid parser to:
     ```python
     grid = np.frombuffer(raw_bytes, dtype='<f4').reshape((129, 135))
     val = grid[lat_idx, lon_idx]
     ```
  2. Map latitude indices `lat_idx = int(round((lat - 6.5) / 0.25))` and `lon_idx = int(round((lon - 66.5) / 0.25))`.
  3. Re-run cleaning to restore all 86,505 valid daily observations.

### DEFECT 2: Missing Gridded Years (2011–2017, 2019, 2020, 2022, 2024)
* **PROBLEM:** Only 2018, 2021, and 2023 are present in `data/raw/rainfall/`. 9 years required for the 2011–2026 scope are absent.
* **ROOT CAUSE:** `download_sources.py` contained a hardcoded subset of 3 years instead of iterating through the 2011–2024 range on `https://imdpune.gov.in/cmpg/Griddata/rainfall.php`.
* **IMPACT:** Longitudinal research cannot evaluate severe rainfall events for 2012, 2013, 2015, 2016, 2019, 2020, 2022, and 2024.
* **PROPOSED FIX:**
  1. Update `download_sources.py` to iterate through all completed years (2011 to 2024) using automated HTTP POST requests.
  2. Download and verify binary files into `data/raw/rainfall/imd_gridded_rain_{year}.grd`.

### DEFECT 3: Unparsed HPSDMA Disaster Loss Memorandums (2013, 2015, 2016, 2025)
* **PROBLEM:** 345 MB of official state loss memorandums exist in `data/raw/disaster_reports/`, but events for several years are omitted from `cloudburst_events.csv` and `flash_flood_events.csv`, showing artificial `NO_DATA` gaps in the timeline.
* **ROOT CAUSE:** `clean_data.py` only parsed a selective subset of tables from 2018, 2019, 2021, 2022, 2023, and 2024.
* **IMPACT:** Significant historical cloudbursts and flash floods (e.g., 2013 Kinnaur/Shimla spillover, 2016 Mandi flash floods, 2025 Dharamshala events) are missing from the canonical event database.
* **PROPOSED FIX:**
  1. Write dedicated tabular extractors for `hpsdma_memo_monsoon_2013_2015.pdf`, `2016.pdf`, and `2025.pdf`.
  2. Extract event date, district, tehsil, river basin, deaths, and financial damage into `cloudburst_events.csv` and `flash_flood_events.csv`.
  3. Re-run deduplication to update `reports/event_coverage_matrix.csv`.

---

## 13. AUDIT DELIVERABLES GENERATED

The following 6 forensic audit deliverables have been generated and validated:
1. `reports/milestone1_deep_audit.md` (This document)
2. `reports/rainfall_completeness_by_year.csv`
3. `reports/rainfall_completeness_by_district.csv`
4. `reports/rainfall_completeness_by_source.csv`
5. `reports/event_coverage_matrix.csv`
6. `reports/event_deduplication_audit.csv`

---

## 14. FINAL AUDIT DECISION & CLASSIFICATION

### Verdict:
```text
NOT_READY — DATA REPAIR REQUIRED
```

### Justification:
The data foundation cannot be certified for Milestone 2 (Chunking, Embeddings, Vector Indexing) because **99.9665% of all daily rainfall observations are currently corrupted by a matrix dimension inversion bug**, and **9 out of 16 years of daily gridded data remain un-downloaded**. Proceeding to build a RAG vector database over empty or missing data would produce hallucinations and fatal analytical errors.

**STOPPING EXECUTION.** Awaiting explicit user approval before applying any code or data modifications.
