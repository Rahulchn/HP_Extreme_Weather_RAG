import os
import re
from pypdf import PdfReader

def extract_events_2013_2015():
    fpath = "HP_Extreme_Weather_RAG/data/raw/disaster_reports/hpsdma_memo_monsoon_2013_2015.pdf"
    reader = PdfReader(fpath)
    print(f"--- 2013-2015 Memo Pages: {len(reader.pages)} ---")
    
    # Check page 19-35 for 2013 June 15-17 flash floods
    for pno in [19, 20, 21, 22, 23, 24, 25, 36, 37]:
        if pno <= len(reader.pages):
            text = reader.pages[pno-1].extract_text() or ""
            print(f"\n[Page {pno}]")
            for line in text.split("\n"):
                if any(w in line.lower() for w in ["kinnaur", "shimla", "kullu", "mandi", "kangra", "dead", "died", "loss of life", "flash"]):
                    print("  ", line.strip())

def extract_events_2016():
    fpath = "HP_Extreme_Weather_RAG/data/raw/disaster_reports/hpsdma_memo_monsoon_2016.pdf"
    reader = PdfReader(fpath)
    print(f"\n--- 2016 Memo Pages: {len(reader.pages)} ---")
    for pno in range(9, 20):
        if pno <= len(reader.pages):
            text = reader.pages[pno-1].extract_text() or ""
            print(f"\n[Page {pno}]")
            for line in text.split("\n"):
                if any(w in line.lower() for w in ["mandi", "kullu", "kangra", "shimla", "cloud", "burst", "flash", "flood", "lives"]):
                    print("  ", line.strip())

def extract_events_2025():
    fpath = "HP_Extreme_Weather_RAG/data/raw/disaster_reports/hpsdma_memo_monsoon_2025.pdf"
    reader = PdfReader(fpath)
    print(f"\n--- 2025 Memo Pages: {len(reader.pages)} ---")
    for pno in [40, 41, 42, 48, 49, 50, 63, 64, 65]:
        if pno <= len(reader.pages):
            text = reader.pages[pno-1].extract_text() or ""
            print(f"\n[Page {pno}]")
            for line in text.split("\n"):
                if any(w in line.lower() for w in ["mandi", "kullu", "kangra", "shimla", "cloudburst", "flash flood", "date", "incident", "tehsil"]):
                    print("  ", line.strip())

extract_events_2013_2015()
extract_events_2016()
extract_events_2025()
