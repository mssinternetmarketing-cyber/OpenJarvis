#!/bin/bash
# OpenJarvis v14.1 Resilience Update

# Define Full Paths for Sovereign Commands
LAUNCHER="/var/home/kmonette/OpenJarvis/bin/launch_qcai.sh"
GAUGE="/var/home/kmonette/OpenJarvis/bin/entropy_gauge.py"
PURIFY="/var/home/kmonette/OpenJarvis/toolbox/hybrid_enforcer.py"
SYNC="/var/home/kmonette/OpenJarvis/bin/sync_knowledge.py"

while true; do
    echo "--- [ 🌊 INFINITE FLOW: ACTIVE ] ---"
    
    # 1. Execute the next task in the Sovereign Brain
    $LAUNCHER
    
    # 2. Check Workspace Entropy (High/Low)
    ENTROPY=$(python3 $GAUGE)
    
    if [ "$ENTROPY" == "HIGH" ]; then
        echo "🧹 ENTROPY ALERT: Initializing Background Purge & Sync..."
        python3 $PURIFY --silent
        python3 $SYNC
        echo "✨ SYSTEM RE-ALIGNED."
    fi
    
    # 3. Brief breather to prevent CPU spikes
    sleep 2
done
