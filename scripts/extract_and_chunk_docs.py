"""
extract_and_chunk_docs.py
Extracts text from raw PDF reports and builds:
1. data/master/document_registry.csv
2. data/master/document_chunks.json
3. Adds document_chunks and document_registry tables into data/master/hp_extreme_weather.db

Preserves:
- chunk_id (deterministic: CHK_{doc_id}_P{page}_{idx})
- document_id
- source_id
- page_number
- section_title
- year
- districts (Kangra, Mandi, Shimla, Kullu)
- event_types (Cloudburst, Flash Flood, Heavy Rainfall, Landslide)
- parameters (Rainfall, Discharge, Inundation, Damage, Casualties)
- authority_level (GOVERNMENT_OFFICIAL, SCIENTIFIC_LITERATURE, REPUTABLE_SECONDARY)
- authority_rank (1 = Govt, 2 = Scientific, 3 = Secondary)
- text
- fingerprint (sha256 of text)
"""

import os
import re
import json
import sqlite3
import hashlib
import pandas as pd
import pypdf

DOC_SPECS = [
    {
        "document_id": "DOC_HPSDMA_PDNA_2023",
        "source_id": "SRC_HPSDMA_PDNA_2023",
        "title": "Post Disaster Needs Assessment (PDNA) Monsoon 2023",
        "file_path": "data/raw/disaster_reports/hpsdma_pdna_monsoon_2023.pdf",
        "year": 2023,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 202
    },
    {
        "document_id": "DOC_HPSDMA_10YR_LOSSES",
        "source_id": "SRC_HPSDMA_10YR_LOSSES_2016_2025",
        "title": "10-Year Cumulative Disaster Losses in Himachal Pradesh (2016-2025)",
        "file_path": "data/raw/disaster_reports/hpsdma_10year_losses_2016_2025.pdf",
        "year": 2025,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 10
    },
    {
        "document_id": "DOC_HPSDMA_LR3_2007_2015",
        "source_id": "SRC_HPSDMA_HISTORICAL_LOSS_2007_2015",
        "title": "Disaster Analysis and Management (LR3 2007-2015) Hazard Study",
        "file_path": "data/raw/disaster_reports/hpsdma_disaster_analysis_lr3_2007_2015.pdf",
        "year": 2015,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 134
    },
    {
        "document_id": "DOC_GSI_BOH_2021",
        "source_id": "SRC_GSI_WADIA_EVENT_STUDIES",
        "title": "GSI Scientific Investigation of Boh-Dharamshala Flash Flood and Debris Flow 2021",
        "file_path": "data/raw/flash_flood/gsi_boh_kangra_investigation.pdf",
        "year": 2021,
        "authority_level": "SCIENTIFIC_LITERATURE",
        "authority_rank": 2,
        "max_pages": 10
    },
    {
        "document_id": "DOC_GSI_KOTRUPI_2017",
        "source_id": "SRC_GSI_WADIA_EVENT_STUDIES",
        "title": "GSI Geotechnical & Hydrometeorological Study of Kotrupi Mandi Disaster 2017",
        "file_path": "data/raw/flash_flood/gsi_kotrupi_mandi_investigation.pdf",
        "year": 2017,
        "authority_level": "SCIENTIFIC_LITERATURE",
        "authority_rank": 2,
        "max_pages": 30
    },
    {
        "document_id": "DOC_IMD_MONSOON_REPORT_2023",
        "source_id": "SRC_IMD_SHIMLA_DISTRICT_MONSOON",
        "title": "IMD MC Shimla Southwest Monsoon 2023 End of Season Report",
        "file_path": "data/raw/rainfall/imd_shimla_monsoon_report_2023.pdf",
        "year": 2023,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 15
    },
    {
        "document_id": "DOC_IMD_MONTHLY_RAIN_2023",
        "source_id": "SRC_IMD_SHIMLA_DISTRICT_MONSOON",
        "title": "IMD MC Shimla Monthly Rainfall & Departure Statement 2023",
        "file_path": "data/raw/rainfall/imd_shimla_rainfallmonthly_2023.pdf",
        "year": 2023,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 10
    },
    {
        "document_id": "DOC_IMD_YEARLY_MONSOON_2004_2025",
        "source_id": "SRC_IMD_SHIMLA_DISTRICT_MONSOON",
        "title": "IMD MC Shimla Long-Term Monsoon Rainfall Statistics (2004-2025)",
        "file_path": "data/raw/rainfall/imd_shimla_yearlymonsoon_2004_2025.pdf",
        "year": 2025,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 5
    },
    {
        "document_id": "DOC_IMD_CLI_KANGRA",
        "source_id": "SRC_IMD_SHIMLA_DISTRICT_MONSOON",
        "title": "IMD Climatological Profile and Historical Extremes: Kangra District",
        "file_path": "data/raw/rainfall/imd_climatology_kangra.pdf",
        "year": 2020,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 5
    },
    {
        "document_id": "DOC_IMD_CLI_KULLU",
        "source_id": "SRC_IMD_SHIMLA_DISTRICT_MONSOON",
        "title": "IMD Climatological Profile and Historical Extremes: Kullu District",
        "file_path": "data/raw/rainfall/imd_climatology_kullu.pdf",
        "year": 2020,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 5
    },
    {
        "document_id": "DOC_IMD_CLI_MANDI",
        "source_id": "SRC_IMD_SHIMLA_DISTRICT_MONSOON",
        "title": "IMD Climatological Profile and Historical Extremes: Mandi District",
        "file_path": "data/raw/rainfall/imd_climatology_mandi.pdf",
        "year": 2020,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 5
    },
    {
        "document_id": "DOC_IMD_CLI_SHIMLA",
        "source_id": "SRC_IMD_SHIMLA_DISTRICT_MONSOON",
        "title": "IMD Climatological Profile and Historical Extremes: Shimla District",
        "file_path": "data/raw/rainfall/imd_climatology_shimla.pdf",
        "year": 2020,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 5
    },
    {
        "document_id": "DOC_IMD_TELEMETRY_2026",
        "source_id": "SRC_IMD_SHIMLA_TELEMETRY_2026",
        "title": "IMD MC Shimla Real-Time AWS Telemetry Report (September 2026)",
        "file_path": "data/raw/rainfall/imd_shimla_three_hourly_telemetry_2026.pdf",
        "year": 2026,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 5
    },
    {
        "document_id": "DOC_IMD_CHIEF_RAIN_2026",
        "source_id": "SRC_IMD_SHIMLA_TELEMETRY_2026",
        "title": "IMD MC Shimla Chief Daily Rainfall Amounts Bulletin (September 2026)",
        "file_path": "data/raw/rainfall/imd_shimla_chief_rainfall_2026.pdf",
        "year": 2026,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 5
    },
    {
        "document_id": "DOC_IMD_DAILY_BULLETIN_2026",
        "source_id": "SRC_IMD_SHIMLA_TELEMETRY_2026",
        "title": "IMD MC Shimla Daily Weather Bulletin (September 2026)",
        "file_path": "data/raw/rainfall/imd_shimla_daily_bulletin_2026.pdf",
        "year": 2026,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 5
    },
]

# Annual memorandums
for yr in range(2016, 2026):
    DOC_SPECS.append({
        "document_id": f"DOC_HPSDMA_MEMO_{yr}",
        "source_id": "SRC_HPSDMA_LOSS_MEMORANDUMS",
        "title": f"HP SDMA State Memorandum of Loss and Damage Monsoon {yr}",
        "file_path": f"data/raw/disaster_reports/hpsdma_memo_monsoon_{yr}.pdf",
        "year": yr,
        "authority_level": "GOVERNMENT_OFFICIAL",
        "authority_rank": 1,
        "max_pages": 40  # Extract core narrative chapters (rainfall, cloudburst, infrastructure damage)
    })

TARGET_DISTRICTS = ["Kangra", "Mandi", "Shimla", "Kullu"]
EVENT_KEYWORDS = {
    "Cloudburst": ["cloudburst", "cloud burst", "cloud-burst"],
    "Flash Flood": ["flash flood", "flash-flood", "flashflood", "inundation", "torrential run-off", "spate"],
    "Heavy Rainfall": ["heavy rainfall", "extremely heavy rain", "very heavy rain", "excessive rainfall", "monsoon deluge"],
    "Landslide": ["landslide", "debris flow", "mudslide", "slope failure", "rockfall"]
}
PARAM_KEYWORDS = {
    "Rainfall": ["rainfall", "precipitation", "mm", "rain gauge", "monsoon"],
    "Infrastructure Damage": ["bridge", "road", "highway", "national highway", "nh-", "houses damaged", "power line", "water supply", "crore", "lakh"],
    "Casualties": ["deaths", "fatalities", "loss of life", "injured", "missing", "human loss", "livestock lost"]
}

def clean_text(text):
    text = re.sub(r'\x00', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def detect_tags(text, default_districts=None):
    text_lower = text.lower()
    districts = [d for d in TARGET_DISTRICTS if d.lower() in text_lower]
    if not districts and default_districts:
        districts = default_districts

    events = []
    for etype, kws in EVENT_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            events.append(etype)

    params = []
    for ptype, kws in PARAM_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            params.append(ptype)

    return districts, events, params

def extract_chunks():
    chunks = []
    doc_registry_rows = []

    print("Starting document extraction and chunking pipeline...")

    for spec in DOC_SPECS:
        path = spec["file_path"]
        if not os.path.exists(path):
            print(f"Skipping missing document: {path}")
            continue

        try:
            reader = pypdf.PdfReader(path)
            total_pages = len(reader.pages)
        except Exception as e:
            print(f"Failed to read {path}: {e}")
            continue

        pages_to_process = min(total_pages, spec["max_pages"])
        extracted_page_count = 0
        doc_chunks_count = 0

        # Infer any district specialization from title/filename
        default_dist = []
        for d in TARGET_DISTRICTS:
            if d.lower() in spec["title"].lower() or d.lower() in path.lower():
                default_dist.append(d)

        for page_idx in range(pages_to_process):
            page_num = page_idx + 1
            try:
                page_text = reader.pages[page_idx].extract_text() or ""
            except Exception:
                page_text = ""

            page_text = clean_text(page_text)
            if len(page_text) < 80:
                continue

            extracted_page_count += 1

            # Split large pages into smaller subchunks if text > 2200 chars (~500 tokens)
            subchunks = []
            if len(page_text) > 2400:
                paragraphs = page_text.split('\n\n')
                current_block = ""
                for p in paragraphs:
                    if len(current_block) + len(p) < 1800:
                        current_block += "\n\n" + p if current_block else p
                    else:
                        if current_block:
                            subchunks.append(current_block.strip())
                        current_block = p
                if current_block:
                    subchunks.append(current_block.strip())
            else:
                subchunks = [page_text]

            for s_idx, sub_text in enumerate(subchunks):
                if len(sub_text) < 80:
                    continue

                chunk_id = f"CHK_{spec['document_id']}_P{page_num:03d}_{s_idx+1:02d}"
                districts, event_types, parameters = detect_tags(sub_text, default_dist)

                # First line as potential section title if short
                lines = [l.strip() for l in sub_text.split('\n') if len(l.strip()) > 5]
                sec_title = lines[0][:100] if lines else spec["title"]

                fp = hashlib.sha256(sub_text.encode('utf-8')).hexdigest()
                approx_tokens = int(len(sub_text.split()) * 1.3)

                chunk = {
                    "chunk_id": chunk_id,
                    "document_id": spec["document_id"],
                    "source_id": spec["source_id"],
                    "document_title": spec["title"],
                    "page_number": page_num,
                    "section_title": sec_title,
                    "year": spec["year"],
                    "districts": districts,
                    "event_types": event_types,
                    "parameters": parameters,
                    "authority_level": spec["authority_level"],
                    "authority_rank": spec["authority_rank"],
                    "text": sub_text,
                    "char_count": len(sub_text),
                    "token_estimate": approx_tokens,
                    "fingerprint": fp
                }
                chunks.append(chunk)
                doc_chunks_count += 1

        print(f"Processed {spec['document_id']}: {pages_to_process}/{total_pages} pages -> {doc_chunks_count} chunks")

        doc_registry_rows.append({
            "document_id": spec["document_id"],
            "source_id": spec["source_id"],
            "title": spec["title"],
            "year": spec["year"],
            "authority_level": spec["authority_level"],
            "authority_rank": spec["authority_rank"],
            "file_path": spec["file_path"],
            "total_pages": total_pages,
            "processed_pages": pages_to_process,
            "chunks_count": doc_chunks_count
        })

    # Save to JSON
    os.makedirs("data/master", exist_ok=True)
    chunks_path = "data/master/document_chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)
    print(f"\nSaved {len(chunks)} document chunks to {chunks_path}")

    # Save Document Registry
    reg_df = pd.DataFrame(doc_registry_rows)
    reg_path = "data/master/document_registry.csv"
    reg_df.to_csv(reg_path, index=False)
    print(f"Saved document registry to {reg_path}")

    # Also save to SQLite hp_extreme_weather.db for cross-querying
    db_path = "data/master/hp_extreme_weather.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    reg_df.to_sql("document_registry", conn, if_exists="replace", index=False)

    # Flatten chunks for SQLite table
    flat_chunks = []
    for c in chunks:
        flat_chunks.append({
            "chunk_id": c["chunk_id"],
            "document_id": c["document_id"],
            "source_id": c["source_id"],
            "page_number": c["page_number"],
            "section_title": c["section_title"],
            "year": c["year"],
            "districts": ",".join(c["districts"]),
            "event_types": ",".join(c["event_types"]),
            "parameters": ",".join(c["parameters"]),
            "authority_level": c["authority_level"],
            "authority_rank": c["authority_rank"],
            "text": c["text"],
            "char_count": c["char_count"],
            "token_estimate": c["token_estimate"],
            "fingerprint": c["fingerprint"]
        })
    chunks_df = pd.DataFrame(flat_chunks)
    chunks_df.to_sql("document_chunks", conn, if_exists="replace", index=False)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunk_id ON document_chunks (chunk_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunk_doc_id ON document_chunks (document_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunk_year ON document_chunks (year)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunk_auth ON document_chunks (authority_rank)")
    conn.commit()
    conn.close()
    print(f"Saved document_chunks and document_registry tables into {db_path}")

if __name__ == "__main__":
    extract_chunks()
