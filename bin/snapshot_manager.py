import shutil, os, datetime

ROOT = "/var/home/kmonette/OpenJarvis"
BACKUP_DIR = os.path.join(ROOT, "archive/snapshots")

def create_snapshot():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(BACKUP_DIR, f"snapshot_{timestamp}")
    os.makedirs(target, exist_ok=True)
    
    # Backup critical DNA only
    for folder in ['config', 'agents', 'Personalities']:
        shutil.copytree(os.path.join(ROOT, folder), os.path.join(target, folder))
    print(f"📸 Snapshot created: {target}")

if __name__ == "__main__":
    create_snapshot()
