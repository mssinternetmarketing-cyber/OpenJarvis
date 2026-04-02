#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# launch_qcai.sh v10.0 — QCAI Master System Orchestrator
# Orchestrates: Monitor → 3D Viz → Bridge → Heartbeat
# ─────────────────────────────────────────────────────────────────────────────

JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
LOG_DIR="$JARVIS_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 INITIALIZING QCAI MASTER SYSTEM"
if [ ! -f "$JARVIS_ROOT/.env" ] || [ ! -s "$JARVIS_ROOT/.env" ]; then 
    echo "  ❌ CRITICAL: .env tokens missing or empty!"; 
    echo "  Please run: cat << EOF > .env (with your Slack tokens)"; 
    exit 1; 
fi
if [ ! -f "$JARVIS_ROOT/.env" ] || [ ! -s "$JARVIS_ROOT/.env" ]; then 
    echo "  ❌ CRITICAL: .env tokens missing or empty!"; 
    echo "  Please run: cat << EOF > .env (with your Slack tokens)"; 
    exit 1; 
fi
if [ ! -f "$JARVIS_ROOT/.env" ] || [ ! -s "$JARVIS_ROOT/.env" ]; then 
    echo "  ❌ CRITICAL: .env tokens missing or empty!"; 
    echo "  Please run: cat << EOF > .env (with your Slack tokens)"; 
    exit 1; 
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Hardware Shield Check
if pgrep -f "qcai_monitor.sh" > /dev/null; then
    echo "  ✅ Hardware Monitor: ACTIVE"
else
    echo "  🛡️ Starting Hardware Monitor Daemon..."
    nohup bash "$JARVIS_ROOT/qcai_monitor.sh" > "$LOG_DIR/monitor.log" 2>&1 &
    sleep 2
fi

# 2. BrowserOS Dependency Check
if [ -d "$JARVIS_ROOT/extensions/browser_os" ]; then
    echo "  🌐 BrowserOS Extension: LINKED"
else
    echo "  ⚠️ Warning: BrowserOS folders missing. Expansion may be limited."
fi

# 3. 3D Visualizer Launch (The "Demystified" Engine)
if pgrep -f "qcai_modern_3d.py" > /dev/null; then
    echo "  ✅ 3D Visualizer: ALREADY RUNNING"
else
    echo "  📊 Launching Modern 3D Visualizer..."
    # Launching in background; output suppressed to keep terminal clean
    python3 "$JARVIS_ROOT/qcai_modern_3d.py" > /dev/null 2>&1 &
fi

# 4. Agent Registry Verification
if [ -f "$JARVIS_ROOT/registry/agents.json" ]; then
    AGENT_COUNT=$(python3 -c "import json; print(len(json.load(open('$JARVIS_ROOT/registry/agents.json'))))")
    echo "  👥 Agent Registry: $AGENT_COUNT Agents Ready"
else
    echo "  ❌ CRITICAL: agents.json not found. Run create_personalities.sh first."
    exit 1
fi

# 5. The Main Event: Slack Bridge (Infinite Respawn Mode)
echo "  🔗 Connecting 41-Agent Swarm to Slack..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  System is now LIVE. Use 'qcai-stop' to terminate all layers."
echo "  Logs: tail -f $LOG_DIR/monitor.log"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# We call start_qcai.sh which contains our infinite respawn logic
bash "$JARVIS_ROOT/start_qcai.sh"
python3 /var/home/kmonette/OpenJarvis/qcai_token_monitor.py &
