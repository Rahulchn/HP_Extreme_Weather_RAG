import os
import shutil
import datetime

backup_dir = 'HP_Extreme_Weather_RAG/data/backup/milestone1_pre_repair'
os.makedirs(backup_dir, exist_ok=True)

dirs_to_backup = [
    ('HP_Extreme_Weather_RAG/data/processed/rainfall', os.path.join(backup_dir, 'rainfall')),
    ('HP_Extreme_Weather_RAG/data/processed/cloudburst', os.path.join(backup_dir, 'cloudburst')),
    ('HP_Extreme_Weather_RAG/data/processed/flash_flood', os.path.join(backup_dir, 'flash_flood')),
    ('HP_Extreme_Weather_RAG/data/processed/combined', os.path.join(backup_dir, 'combined')),
    ('HP_Extreme_Weather_RAG/scripts', os.path.join(backup_dir, 'scripts')),
    ('HP_Extreme_Weather_RAG/reports', os.path.join(backup_dir, 'reports')),
]

for src, dst in dirs_to_backup:
    if os.path.exists(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"Backed up {src} -> {dst}")

timestamp = datetime.datetime.now().isoformat()
with open(os.path.join(backup_dir, 'backup_manifest.txt'), 'w', encoding='utf-8') as f:
    f.write(f"Milestone 1 Pre-Repair Backup\n")
    f.write(f"Timestamp: {timestamp}\n")
    f.write(f"Purpose: Preserve raw processed outputs and scripts before executing Milestone 1 repair.\n")

print(f"Pre-repair backup successfully completed at: {timestamp}")
