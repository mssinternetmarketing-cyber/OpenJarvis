#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# launch_qcai.sh v9.1 — Full QCAI system launcher
# Starts everything: Ollama → OpenJarvis API → Bridge
# Run from HOST or distrobox.
# Usage: ~/launch_qcai.sh
# ─────────────────────────────────────────────────────────────────────────────

JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
OLLAMA_BIN="/usr/local/bin/ollama"
OLLAMA_HOST_ADDR="0.0.0.0:11434"
OLLAMA_CHECK="http://192.168.1.183:11434/api/tags"
OLLAMA_KEEP_ALIVE="30m"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 QCAI Full System Launcher v9.1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Start Ollama if not already running ────────────────────────────────────
echo ""
echo "▶ Checking Ollama..."
if curl -sf "$OLLAMA_CHECK" > /dev/null 2>&1; then
    echo "  ✅ Ollama already running"
else
    echo "  ⚙️  Starting Ollama..."
    pkill ollama 2>/dev/null || true
    sleep 1
    OLLAMA_HOST=$OLLAMA_HOST_ADDR OLLAMA_KEEP_ALIVE=$OLLAMA_KEEP_ALIVE \
        nohup $OLLAMA_BIN serve > /tmp/ollama.log 2>&1 &
    echo "  ⏳ Waiting for Ollama to be ready..."
    for i in $(seq 1 15); do
        sleep 1
        if curl -sf "$OLLAMA_CHECK" > /dev/null 2>&1; then
            echo "  ✅ Ollama started (${i}s)"
            break
        fi
        if [ "$i" = "15" ]; then
            echo "  ❌ Ollama failed to start after 15s"
            echo "     Check: cat /tmp/ollama.log"
            exit 1
        fi
    done
fi

# ── 2. Start the bridge (handles OpenJarvis API check internally) ─────────────
echo ""
echo "▶ Starting QCAI bridge..."
exec "$JARVIS_ROOT/start_qcai.sh"
