"""
HP Extreme Weather RAG - Master Clean Data & Normalization Script
Wraps the verified repair and revalidation pipeline.
"""
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    script = PROJECT_ROOT / "scripts" / "repair_and_revalidate.py"
    print(f"Executing verified pipeline: {script} ...")
    res = subprocess.run([sys.executable, str(script)], check=True)
    sys.exit(res.returncode)
