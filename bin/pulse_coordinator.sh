#!/bin/bash
# OpenJarvis v12.5 Master Orchestrator

while true; do
    echo "------------------------------------------------"
    echo "🚀 PHASE 1: WORK MODE (Starting 60 Minute Block)"
    echo "------------------------------------------------"
    
    # 1. Pre-Flight Ghost Check
    qcai-ghost || { echo "❌ Critical Environment Failure. Aborting."; exit 1; }
    
    # 2. Start Work (Runs for 1 Hour)
    timeout 1h /var/home/kmonette/OpenJarvis/bin/launch_qcai.sh
    
    echo "------------------------------------------------"
    echo "⏸️ PHASE 2: PAUSING & ANALYZING"
    echo "------------------------------------------------"
    /var/home/kmonette/OpenJarvis/bin/stop_qcai.sh
    
    # 3. Trigger the Swarm Reflection
    qcai-pulse
    
    # 4. Final Purify (Ensure root is clean for the next hour)
    qcai-purify
    
    echo "------------------------------------------------"
    echo "♻️ PHASE 3: HOUR RESET (Looping to New Work Block)"
    echo "------------------------------------------------"
    sleep 5
done
