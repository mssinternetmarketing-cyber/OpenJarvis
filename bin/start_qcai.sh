#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start_qcai.sh v9.3 — QCAI Bridge Startup Script (Infinite Respawn)
# ─────────────────────────────────────────────────────────────────────────────

BRIDGE_DIR="/var/home/kmonette/OpenJarvis"
BRIDGE_FILE="slack_bridge.py"

echo "🚀 Starting OpenJarvis Slack Bridge (Resiliency Mode Active)"

# The Infinite Respawn Loop
while true; do
    echo "🔄 (Re)starting bridge at $(date)"
    python3 "$BRIDGE_DIR/$BRIDGE_FILE"
    
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "🛑 Bridge exited cleanly. Stopping respawn loop."
        break
    else
        echo "⚠️ Bridge crashed with exit code $EXIT_CODE."
        echo "⏳ Auto-respawning in 5 seconds..."
        sleep 5
    fi
done
