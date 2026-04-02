import os, shutil, glob
from datetime import datetime

ROOT = "/var/home/kmonette/OpenJarvis"
ARCHIVE = os.path.join(ROOT, "registry/archive")

# THE IRONCLAD MANIFEST: These stay in the root NO MATTER WHAT
PROTECTED_FILES = [
    "launch_qcai.sh", "stop_qcai.sh", "slack_bridge.py", ".env", 
    "ENV_STATUS.json", "SYSTEM_STATUS.json", "pyproject.toml", 
    "uv.lock", "qcai_modern_3d.py", "requirements.txt"
]

# PROTECTED DIRECTORIES: These are never archived
PROTECTED_DIRS = [
    "toolbox", "registry", "workspaces", "Personalities", 
    "agents", "logs", ".venv", ".git"
]

CLEANUP_PATTERNS = ["*.backup", "*.ba", "patch_*.py", "test_*.py", "old_*"]

def purify():
    if not os.path.exists(ARCHIVE): os.makedirs(ARCHIVE)
    print("🧹 Purifier: Executing Ironclad Protection Protocol...")
    
    for item in os.listdir(ROOT):
        item_path = os.path.join(ROOT, item)
        
        # Skip Protected Files and Dirs
        if item in PROTECTED_FILES or item in PROTECTED_DIRS:
            continue
            
        # Archive specifically identified junk
        should_archive = False
        for pattern in CLEANUP_PATTERNS:
            if glob.fnmatch.fnmatch(item, pattern):
                should_archive = True
                break
        
        if should_archive:
            print(f"📦 Safely Archiving: {item}")
            shutil.move(item_path, os.path.join(ARCHIVE, item))

    print("✅ Root purified. Protected assets remain untouched.")

if __name__ == "__main__":
    purify()
