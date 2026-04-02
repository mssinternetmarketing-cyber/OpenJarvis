# Purpose: Metadata-aware indexing with Atomic File Locking
import json, sys, os, time
import re
import re
from datetime import datetime

TRUTH_FILE = "/var/home/kmonette/OpenJarvis/registry/truth.json"
LOCK_FILE = "/var/home/kmonette/OpenJarvis/registry/truth.json.lock"

def add_resource(category, title, url, tags, summary):
    # Security: URL Sanitization
    if not re.match(r"^https?://", url):
        print("❌ Security Violation: Invalid URL format."); return
    # Security: URL Sanitization
    if not re.match(r"^https?://", url):
        print("❌ Security Violation: Invalid URL format."); return
    # Wait for Lock
    while os.path.exists(LOCK_FILE):
        time.sleep(0.2)
    
    try:
        open(LOCK_FILE, 'w').close() # Create Lock
        
        with open(TRUTH_FILE, 'r') as f:
            data = json.load(f)
        
        if category not in data: data[category] = {}
        resource_id = title.lower().replace(" ", "_")[:50]
        
        data[category][resource_id] = {
            "title": title, "url": url,
            "tags": tags.split(","), "summary": summary,
            "date_added": datetime.now().strftime("%Y-%m-%d"),
            "last_accessed": datetime.now().strftime("%Y-%m-%d")
        }
        
        with open(TRUTH_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"✅ Indexed: {title} in {category}")
    finally:
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)

if __name__ == "__main__":
    if len(sys.argv) > 4:
        add_resource(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
