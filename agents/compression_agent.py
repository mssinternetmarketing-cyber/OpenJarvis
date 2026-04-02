import os, json, time, shutil, subprocess
from datetime import datetime

# Path Configuration (v12.0 Sovereign)
ROOT = "/var/home/kmonette/OpenJarvis"
LOG_DIR = os.path.join(ROOT, "logs")
DATA_DIR = os.path.join(ROOT, "data")
TRUTH_FILE = os.path.join(DATA_DIR, "truth.json")
ARCHIVE_DIR = os.path.join(ROOT, "archive/logs")
AGENTS_DIR = os.path.join(ROOT, "agents")

def synthesize_insights(log_content):
    """
    Simulates the swarm's creative POV to drive architectural insights.
    """
    print("🧠 Swarm Intelligence: Synthesizing creative insights...")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    insight = {
        "timestamp": timestamp,
        "creative_takeaway": "Collaborative Swarm Sync: Logic Refined, Debt Cataloged, Patterns Archived.",
        "significant_data": f"Processed {len(log_content)} bytes of raw log data into high-value truth."
    }
    return insight

def run_full_compression():
    print("🧹 Phase 2: Starting Full System Compression...")
    
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

    debug_log = os.path.join(LOG_DIR, "debug.log")
    if os.path.exists(debug_log) and os.path.getsize(debug_log) > 0:
        with open(debug_log, "r") as f:
            raw_data = f.read()

        new_insight = synthesize_insights(raw_data)

        try:
            with open(TRUTH_FILE, "r") as f:
                truth_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            truth_data = []

        truth_data.append(new_insight)
        
        with open(TRUTH_FILE, "w") as f:
            json.dump(truth_data, f, indent=4)

        archive_name = f"log_archive_{int(time.time())}.txt"
        shutil.move(debug_log, os.path.join(ARCHIVE_DIR, archive_name))
        open(debug_log, 'w').close() 
        
        print(f"✅ Compression Finished. {archive_name} archived.")
    else:
        print("ℹ️ No new data to compress this hour.")

def run_collaborative_cycle():
    """
    The Master Loop: Summon specialists before final compression.
    """
    print("\n🤝 PHASE 1: Summoning the Support Swarm for Full-Scope Analysis...")
    
    # List of specialized support agents
    agents = ["logic_refiner.py", "debt_collector.py", "insight_architect.py"]
    
    for agent_file in agents:
        agent_path = os.path.join(AGENTS_DIR, agent_file)
        if os.path.exists(agent_path):
            print(f"   -> Launching {agent_file}...")
            subprocess.run(["python3", agent_path])
        else:
            print(f"   ⚠️ Warning: {agent_file} not found in {AGENTS_DIR}")
    
    # After specialists finish their analysis, run the data compression
    run_full_compression()

if __name__ == "__main__":
    # The entry point is now the Collaborative Cycle
    run_collaborative_cycle()
