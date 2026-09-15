import os
from pypdf import PdfReader

reports = [
    "hpsdma_memo_monsoon_2013_2015.pdf",
    "hpsdma_memo_monsoon_2016.pdf",
    "hpsdma_memo_monsoon_2025.pdf"
]

base_dir = "HP_Extreme_Weather_RAG/data/raw/disaster_reports"

for rname in reports:
    fpath = os.path.join(base_dir, rname)
    if not os.path.exists(fpath):
        print(f"File not found: {fpath}")
        continue
    
    print(f"\n=======================================================")
    print(f"INSPECTING: {rname} ({os.path.getsize(fpath):,} bytes)")
    print(f"=======================================================")
    
    try:
        reader = PdfReader(fpath)
        num_pages = len(reader.pages)
        print(f"Total Pages: {num_pages}")
        
        # Search for pages containing keywords
        cb_pages = []
        ff_pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text_lower = text.lower()
            if "cloudburst" in text_lower or "cloud burst" in text_lower:
                cb_pages.append(i + 1)
            if "flash flood" in text_lower or "flash-flood" in text_lower:
                ff_pages.append(i + 1)
                
        print(f"Pages with 'cloudburst' ({len(cb_pages)}): {cb_pages[:20]}")
        print(f"Pages with 'flash flood' ({len(ff_pages)}): {ff_pages[:20]}")
        
        # Print snippets from the first 3 matching pages
        for pno in (cb_pages[:3] + ff_pages[:3]):
            p = reader.pages[pno - 1]
            txt = p.extract_text() or ""
            print(f"\n--- Page {pno} Snippet ---")
            lines = [line.strip() for line in txt.split("\n") if line.strip()]
            for l in lines[:15]:
                print(f"  {l}")
    except Exception as e:
        print(f"Error reading {rname}: {e}")
