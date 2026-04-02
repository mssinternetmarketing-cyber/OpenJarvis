#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# launch_qcai.sh v9.2 — Full QCAI system launcher
# Starts: Ollama → OpenJarvis API → Bridge → Viz watcher loop
#
# The viz watcher (viz_loop.sh) is event-driven:
#   - Opens a visual terminal window immediately if qcai_3d.py is valid
#   - Watches for file changes from agents (inotifywait, instant response)
#   - When a new version arrives: kills old window → validates → relaunches
#   - If the file never changes: the window NEVER closes and reopens
#   - Polling fallback (60s) if inotifywait is unavailable
#
# Usage: qcai-launch            (start all)
#        qcai-launch --no-viz   (skip viz terminal, bridge only)
# ─────────────────────────────────────────────────────────────────────────────

JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
OLLAMA_BIN="/usr/local/bin/ollama"
OLLAMA_HOST_ADDR="0.0.0.0:11434"
OLLAMA_CHECK="http://192.168.1.183:11434/api/tags"
OLLAMA_KEEP_ALIVE="30m"
VIZ_LOOP="$JARVIS_ROOT/viz_loop.sh"

NO_VIZ=false
for arg in "$@"; do
    case "$arg" in
        --no-viz) NO_VIZ=true ;;
    esac
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 QCAI Full System Launcher v9.2"
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

# ── 2. Start viz watcher in background terminal (before bridge blocks) ────────
if [ "$NO_VIZ" = false ]; then
    echo ""
    echo "▶ Starting visualization watcher..."

    if [ ! -f "$VIZ_LOOP" ]; then
        echo "  ⚠️  viz_loop.sh not found at $VIZ_LOOP — skipping viz"
        echo "     Deploy it via: qcai-update"
    else
        # Resolve the active workspace for display
        ACTIVE_WS_FILE="$JARVIS_ROOT/workspaces/active_workspace.txt"
        ACTIVE_WS="ws_1"
        if [ -f "$ACTIVE_WS_FILE" ]; then
            ACTIVE_WS=$(basename "$(cat "$ACTIVE_WS_FILE")")
        fi

        # Detect available terminal and launch viz_loop.sh in it
        VIZ_CMD="bash $VIZ_LOOP; exec bash"
        VIZ_TITLE="QCAI Viz Watcher [$ACTIVE_WS]"
        LAUNCHED_VIZ=false

        if   command -v ptyxis          &>/dev/null; then
            ptyxis --title="$VIZ_TITLE" -- bash -c "$VIZ_CMD" &
            LAUNCHED_VIZ=true
        elif command -v gnome-terminal   &>/dev/null; then
            gnome-terminal --title="$VIZ_TITLE" -- bash -c "$VIZ_CMD" &
            LAUNCHED_VIZ=true
        elif command -v konsole          &>/dev/null; then
            konsole --title "$VIZ_TITLE" -e bash -c "$VIZ_CMD" &
            LAUNCHED_VIZ=true
        elif command -v xterm            &>/dev/null; then
            xterm -title "$VIZ_TITLE" -e bash -c "$VIZ_CMD" &
            LAUNCHED_VIZ=true
        elif flatpak list 2>/dev/null | grep -q "org.gnome.Ptyxis"; then
            flatpak run org.gnome.Ptyxis --title="$VIZ_TITLE" -- bash -c "$VIZ_CMD" &
            LAUNCHED_VIZ=true
        fi

        if [ "$LAUNCHED_VIZ" = true ]; then
            echo "  ✅ Viz watcher launched in terminal: $VIZ_TITLE"
            echo "     Controls: qcai-viz-pause | qcai-viz-resume | qcai-stop"
        else
            # No GUI terminal — run viz_loop in background, attach to current tty
            echo "  ⚠️  No GUI terminal found — running viz watcher in background"
            nohup bash "$VIZ_LOOP" > /tmp/viz_loop.log 2>&1 &
            echo "  ✅ Viz watcher running (bg) — logs: tail -f /tmp/viz_loop.log"
        fi
    fi
fi

# ── 3. Start the bridge (blocks — must be last) ───────────────────────────────
echo ""
echo "▶ Starting QCAI bridge..."
exec "$JARVIS_ROOT/start_qcai.sh"
