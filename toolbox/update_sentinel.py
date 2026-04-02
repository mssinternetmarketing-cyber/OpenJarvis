import json, os, sys
from datetime import datetime

# DEFINITIVE PATHS (v12.0 Hybrid-Sovereign)
ROOT = "/var/home/kmonette/OpenJarvis"
CONFIG_DIR = os.path.join(ROOT, "config")
AGENTS_DIR = os.path.join(ROOT, "agents")
LOG_FILE = os.path.join(ROOT, "logs/update_integrity.log")

def log_event(message, status="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] [{status}] {message}\n")

def check_integrity():
    print("🛡️ Sentinel: Performing Full-Scope Compatibility Check...")
    
    # 1. CORE MANIFEST (Identity & State)
    core_manifest = {
        "State Registry": os.path.join(ROOT, "ENV_STATUS.json"),
        "Sovereign Secrets": os.path.join(CONFIG_DIR, ".env"),
        "Agent Registry": os.path.join(CONFIG_DIR, "agents.json"),
        "Tool Registry": os.path.join(CONFIG_DIR, "tools.json")
    }

    # 2. SWARM MANIFEST (The Processing Specialists)
    swarm_manifest = {
        "Logic Refiner": os.path.join(AGENTS_DIR, "logic_refiner.py"),
        "Debt Collector": os.path.join(AGENTS_DIR, "debt_collector.py"),
        "Insight Architect": os.path.join(AGENTS_DIR, "insight_architect.py"),
        "Browser Engine": os.path.join(ROOT, "core/browser_engine.py"), "Compression Agent": os.path.join(AGENTS_DIR, "compression_agent.py")
    }

    # Combine all checks
    all_checks = {**core_manifest, **swarm_manifest}

    for name, path in all_checks.items():
        if not os.path.exists(path):
            log_event(f"CRITICAL MISSING: {name} at {path}", "FAILED")
            print(f"❌ Swarm Failure: {name} is offline. (Searched: {path})")
            return False
        
        # Verify JSON validity for registries
        if path.endswith(".json"):
            try:
                with open(path, "r") as f:
                    json.load(f)
            except Exception as e:
                log_event(f"CORRUPT JSON: {name} - {e}", "FAILED")
                print(f"⚠️ Corruption in {name}")
                return False

    log_event("Full System Integrity Verified. Swarm is Operational.", "SUCCESS")
    print("✅ Sentinel: All systems compatible. Swarm is online.")
    return True

if __name__ == "__main__":
    if not check_integrity():
        sys.exit(1)
