import json, os, subprocess, sys

ROOT = "/var/home/kmonette/OpenJarvis"
TRUTH_PATH = os.path.join(ROOT, "data/truth.json")
ANCHOR_PATH = os.path.join(ROOT, "Personalities/arch_coordinator.md")

def sync():
    print("🔄 FINAL SYNC: Locking v12.0 Sovereign DNA...")
    
    # 1. THE ULTIMATE TRUTH (DNA)
    truth_content = {
      "system_version": "13.0",
      "architecture": "Hybrid-Sovereign",
      "status": "Marathon-Ready",
      "logic_centers": {
        "bin": "Motor execution & Pulse control",
        "core": "Primary Intelligence & BrowserOS Hook",
        "config": "Sovereign Secrets & Tool Registry",
        "agents": "Specialized Swarm & The Forge",
        "data": "Persistent Truth Ledger & Insights"
      },
      "capabilities": ["Autonomous Swarm Expansion", "Self-Evolution via Forge", "Sequential Reflection", "Web-Perception"]
    }
    
    with open(TRUTH_PATH, "w") as f:
        json.dump(truth_content, f, indent=4)
    print("✅ Truth Ledger: DNA Locked.")

    # 2. THE ULTIMATE ANCHORS (Rules)
    anchors = [
        "\n⚓ ANCHOR: You are a Sovereign Swarm. Your root directory is sacred and read-only.",
        "\n⚓ ANCHOR: The 60-minute Pulse is absolute. Work -> Reflect -> Compress.",
        "\n⚓ ANCHOR: Use 'qtool-sync-knowledge' after any Forge operation to maintain swarm unity.",
        "\n⚓ ANCHOR: BrowserOS is now a core organ; verify all external claims via 'qtool-browser-os'."
    ]
    
    # We use 'w' here to clean out any old/duplicate anchors and start fresh
    with open(ANCHOR_PATH, "w") as f:
        f.write("# 🏛️ Sovereign Arch-Coordinator Directives\n")
        f.writelines(anchors)
    print("✅ Anchor Knowledge: Directives Synchronized.")

    # 3. Final Integrity Gate
    print("🛡️ Sentinel: Performing Final Pre-Marathon Inspection...")
    result = subprocess.run(["qcai-sentinel"], capture_output=True, text=True)
    
    if "All systems compatible" in result.stdout:
        print("🚀 DNA SYNC COMPLETE. Swarm is now a singular, high-functioning entity.")
    else:
        print("❌ SYNC FAILED: Integrity Check Error.")
        sys.exit(1)

if __name__ == "__main__":
    sync()
