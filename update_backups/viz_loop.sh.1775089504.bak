#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# viz_loop.sh v9.2 — Event-Driven QCAI Visualization Watcher
#
# Reads the ACTIVE workspace from active_workspace.txt at startup.
# Watches qcai_3d.py in that workspace for changes using inotifywait.
# The moment agents save a new version → validates → kills old → relaunches.
# No polling interval — instant update on file change.
# If file NEVER changes — window NEVER closes and reopens.
#
# Controls:
#   PAUSE:  qcai-viz-pause   (or ~/viz_pause.sh)
#   RESUME: qcai-viz-resume  (or ~/viz_resume.sh)
#   STOP:   Ctrl+C or qcai-stop
#
# Usage: qcai-viz
#        viz_loop.sh [--ws ws_2]   (override active workspace)
# ─────────────────────────────────────────────────────────────────────────────

JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
WORKSPACES_ROOT="$JARVIS_ROOT/workspaces"
ACTIVE_WS_FILE="$WORKSPACES_ROOT/active_workspace.txt"

PYTHON="/home/kmonette/miniconda3/bin/python3"
[ ! -f "$PYTHON" ] && PYTHON=$(which python3)

PAUSE_FILE="$HOME/.qcai_viz_pause"
LAST_LINES=0

# ── Parse args ────────────────────────────────────────────────────────────────
OVERRIDE_WS=""
for arg in "$@"; do
    case "$arg" in
        --ws) shift; OVERRIDE_WS="$1" ;;
        --ws=*) OVERRIDE_WS="${arg#--ws=}" ;;
    esac
done

# ── Resolve active workspace ──────────────────────────────────────────────────
resolve_workspace() {
    if [ -n "$OVERRIDE_WS" ]; then
        if [ -d "$WORKSPACES_ROOT/$OVERRIDE_WS" ]; then
            echo "$WORKSPACES_ROOT/$OVERRIDE_WS"
        elif [ -d "$OVERRIDE_WS" ]; then
            echo "$OVERRIDE_WS"
        else
            echo "$WORKSPACES_ROOT/ws_1"
        fi
        return
    fi

    if [ -f "$ACTIVE_WS_FILE" ]; then
        WS=$(cat "$ACTIVE_WS_FILE")
        if [ -d "$WS" ]; then
            echo "$WS"
            return
        fi
    fi

    # Fallback: ws_1
    echo "$WORKSPACES_ROOT/ws_1"
}

WORKSPACE=$(resolve_workspace)
WS_NAME=$(basename "$WORKSPACE")
WATCH_FILE="$WORKSPACE/qcai_3d.py"

# ── Check inotifywait is available ────────────────────────────────────────────
FALLBACK=false
if ! command -v inotifywait &>/dev/null; then
    echo "⚠️  inotifywait not found — installing inotify-tools..."
    sudo dnf install -y inotify-tools 2>/dev/null || \
    sudo apt-get install -y inotify-tools 2>/dev/null || \
    rpm-ostree install inotify-tools 2>/dev/null || true

    if ! command -v inotifywait &>/dev/null; then
        echo "❌ Could not install inotify-tools automatically."
        echo "   Run: sudo rpm-ostree install inotify-tools && reboot"
        echo ""
        echo "   Falling back to 60-second polling mode..."
        FALLBACK=true
    fi
fi

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  🛑 Visualization watcher stopped [$WS_NAME]"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    rm -f "$PAUSE_FILE"
    kill_viz
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Kill all viz windows ──────────────────────────────────────────────────────
kill_viz() {
    pkill -f "qcai_3d" 2>/dev/null || true
    fuser -k 9999/tcp 2>/dev/null || \
        lsof -ti:9999 | xargs kill -9 2>/dev/null || true
    sleep 1
}

# ── Syntax + fence check ──────────────────────────────────────────────────────
check_syntax() {
    $PYTHON -c "
import ast, sys
with open('$1') as f: src = f.read()
if '\`\`\`' in src:
    print('FENCED'); sys.exit(1)
try:
    ast.parse(src); print('OK')
except SyntaxError as e:
    print(f'ERROR: {e}'); sys.exit(1)
" 2>/dev/null
}

# ── Launch viz in new terminal ────────────────────────────────────────────────
launch_viz() {
    local file="$1"
    local label="$2"
    local CMD="cd $WORKSPACE && $PYTHON $file; exec bash"
    local TITLE="QCAI Viz [$WS_NAME | $label]"

    if   command -v ptyxis          &>/dev/null; then ptyxis --title="$TITLE" -- bash -c "$CMD" &
    elif command -v gnome-terminal   &>/dev/null; then gnome-terminal --title="$TITLE" -- bash -c "$CMD" &
    elif command -v konsole          &>/dev/null; then konsole --title "$TITLE" -e bash -c "$CMD" &
    elif command -v xterm            &>/dev/null; then xterm -title "$TITLE" -e bash -c "$CMD" &
    elif flatpak list 2>/dev/null | grep -q "org.gnome.Ptyxis"; then
        flatpak run org.gnome.Ptyxis --title="$TITLE" -- bash -c "$CMD" &
    else
        # No GUI terminal — run directly in background
        cd "$WORKSPACE" && $PYTHON "$file" &
    fi
}

# ── Handle a file change event ────────────────────────────────────────────────
handle_update() {
    local TIMESTAMP
    TIMESTAMP=$(date +"%H:%M:%S")

    echo ""
    echo "──────────────────────────────────────────────────"
    echo "  📝 File changed at $TIMESTAMP [$WS_NAME]"

    # Paused?
    if [ -f "$PAUSE_FILE" ]; then
        echo "  ⏸  PAUSED — ignoring update"
        echo "     Run qcai-viz-resume to resume"
        return
    fi

    # File exists?
    if [ ! -f "$WATCH_FILE" ]; then
        echo "  ⚠️  File disappeared — skipping"
        return
    fi

    CURRENT_LINES=$(wc -l < "$WATCH_FILE")

    # Too short?
    if [ "$CURRENT_LINES" -lt 400 ]; then
        echo "  ⚠️  Only $CURRENT_LINES lines — looks incomplete, skipping"
        return
    fi

    # Validate syntax
    SYNTAX=$(check_syntax "$WATCH_FILE")

    if [ "$SYNTAX" = "FENCED" ]; then
        echo "  ⚠️  Markdown fences detected — Builder output still bad format"
        echo "     Skipping this version, waiting for next loop"
        return
    fi

    if [[ "$SYNTAX" == ERROR* ]]; then
        echo "  ⚠️  Syntax error — skipping"
        echo "  $SYNTAX"
        return
    fi

    # Same as last version? → no restart
    if [ "$CURRENT_LINES" -eq "$LAST_LINES" ]; then
        echo "  ℹ️  Same line count ($CURRENT_LINES) — no meaningful change, window stays open"
        return
    fi

    # Valid new version — update viz
    echo "  ✅ Valid new version: $CURRENT_LINES lines (was $LAST_LINES)"

    # Back up previous running version
    if [ -f "$WORKSPACE/qcai_3d_running.py" ]; then
        BACKUP="$WORKSPACE/versions/output/viz_backup_$(date +%Y%m%d_%H%M%S).py"
        mkdir -p "$WORKSPACE/versions/output"
        cp "$WORKSPACE/qcai_3d_running.py" "$BACKUP" 2>/dev/null || true
        echo "  📦 Previous version backed up"
    fi

    echo "  🔪 Closing previous visualization..."
    kill_viz

    cp "$WATCH_FILE" "$WORKSPACE/qcai_3d_running.py"
    LAST_LINES=$CURRENT_LINES

    echo "  🚀 Launching updated visualization..."
    launch_viz "qcai_3d_running.py" "$TIMESTAMP"
    echo "  ✅ Visualization updated"
    echo "     Pause: qcai-viz-pause  |  Resume: qcai-viz-resume"
}

# ── Write helper scripts to home dir ─────────────────────────────────────────
write_helpers() {
    cat > "$HOME/viz_pause.sh" << 'EOF'
#!/usr/bin/env bash
touch ~/.qcai_viz_pause
echo "⏸  Visualization watcher PAUSED — current window will stay open"
echo "   Run qcai-viz-resume (or ~/viz_resume.sh) to resume"
EOF
    chmod +x "$HOME/viz_pause.sh"

    cat > "$HOME/viz_resume.sh" << 'EOF'
#!/usr/bin/env bash
rm -f ~/.qcai_viz_pause
echo "▶️  Visualization watcher RESUMED — will update on next agent save"
echo "   Run qcai-viz-pause (or ~/viz_pause.sh) to pause again"
EOF
    chmod +x "$HOME/viz_resume.sh"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

write_helpers
rm -f "$PAUSE_FILE"   # always start unpaused

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  👁  QCAI Visualization Watcher v9.2"
echo "  Workspace: $WS_NAME  ($WORKSPACE)"
echo "  Watching:  $WATCH_FILE"
echo "  Mode: $([ "$FALLBACK" = true ] && echo 'polling (60s)' || echo 'event-driven (instant)')"
echo ""
echo "  Controls:"
echo "    PAUSE:  qcai-viz-pause"
echo "    RESUME: qcai-viz-resume"
echo "    STOP:   Ctrl+C or qcai-stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Wait for file to exist before watching
if [ ! -f "$WATCH_FILE" ]; then
    echo ""
    echo "⏳ Waiting for $WATCH_FILE to exist..."
    while [ ! -f "$WATCH_FILE" ]; do sleep 2; done
    echo "  ✅ File found — starting watcher"
fi

# Initial launch with current file (if valid)
CURRENT_LINES=$(wc -l < "$WATCH_FILE")
echo ""
echo "▶ Initial launch with current file ($CURRENT_LINES lines)..."
SYNTAX=$(check_syntax "$WATCH_FILE")
if [ "$SYNTAX" = "OK" ] && [ "$CURRENT_LINES" -ge 400 ]; then
    cp "$WATCH_FILE" "$WORKSPACE/qcai_3d_running.py"
    LAST_LINES=$CURRENT_LINES
    launch_viz "qcai_3d_running.py" "initial"
    echo "  ✅ Visualization launched"
else
    echo "  ⚠️  Initial file not valid ($SYNTAX, $CURRENT_LINES lines)"
    echo "     Watching for agents to produce a clean version..."
fi

echo ""
echo "👁  Watching for changes..."

# ── Event loop ────────────────────────────────────────────────────────────────
if [ "$FALLBACK" = true ]; then
    echo "  (polling mode — checking every 60s)"
    while true; do
        sleep 60
        handle_update
    done
else
    # inotifywait fires instantly when file is written/closed
    while inotifywait -q -e close_write "$WATCH_FILE" 2>/dev/null; do
        handle_update
    done
fi
