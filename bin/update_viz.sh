#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# update_viz.sh — Restart QCAI Visualization with Latest Agent Output
# Kills the running visualization, backs up the current version,
# copies the latest agent output, and relaunches cleanly.
# Run this from the HOST when agents have produced a new version.
# Usage: ~/update_viz.sh
# ─────────────────────────────────────────────────────────────────────────────

WORKSPACE="/var/home/kmonette/OpenJarvis/workspace"
PYTHON="/home/kmonette/miniconda3/bin/python3"
[ ! -f "$PYTHON" ] && PYTHON=$(which python3)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔄 QCAI Visualization Update"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Check agent output exists ────────────────────────────────────────
if [ ! -f "$WORKSPACE/qcai_3d.py" ]; then
    echo "❌ No qcai_3d.py found in workspace"
    echo "   Run LOAD_TASK in Slack first to let agents produce output"
    exit 1
fi

LINES=$(wc -l < "$WORKSPACE/qcai_3d.py")
echo ""
echo "▶ Agent output: qcai_3d.py ($LINES lines)"

# Warn if file looks too short to be complete
if [ "$LINES" -lt 100 ]; then
    echo "⚠️  File is only $LINES lines — may be incomplete"
    echo "   Check #jarvis-physics for PASS status before updating"
    read -p "   Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  Aborted. Wait for a Physics PASS loop."
        exit 0
    fi
fi

# Check for markdown fences — sign of a bad agent output
if grep -q '^\`\`\`' "$WORKSPACE/qcai_3d.py" 2>/dev/null; then
    echo "⚠️  File contains markdown fences (```)"
    echo "   This means Builder output wasn't raw Python"
    echo "   The file will likely crash. Wait for next loop."
    read -p "   Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  Aborted. Letting agents fix the fence issue."
        exit 0
    fi
fi

# ── Step 2: Quick syntax check ───────────────────────────────────────────────
echo ""
echo "▶ Checking Python syntax..."
if ! $PYTHON -c "
import ast, sys
with open('$WORKSPACE/qcai_3d.py') as f:
    src = f.read()
try:
    ast.parse(src)
    print('  ✅ Syntax valid')
except SyntaxError as e:
    print(f'  ❌ SyntaxError: {e}')
    sys.exit(1)
" 2>/dev/null; then
    echo "❌ File has syntax errors — not safe to run"
    echo "   Wait for Physics agent to produce a clean version"
    exit 1
fi

# ── Step 3: Back up current running version ───────────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP="$WORKSPACE/qcai_3d_backup_$TIMESTAMP.py"

if [ -f "$WORKSPACE/qcai_3d_running.py" ]; then
    cp "$WORKSPACE/qcai_3d_running.py" "$BACKUP"
    echo "▶ Backed up previous version → qcai_3d_backup_$TIMESTAMP.py"
fi

# ── Step 4: Kill running visualization ───────────────────────────────────────
echo ""
echo "▶ Stopping current visualization..."
if pkill -f "qcai_3d" 2>/dev/null; then
    sleep 2
    echo "  ✅ Previous visualization stopped"
else
    echo "  ℹ️  No visualization was running"
fi

# Clear port 9999
fuser -k 9999/tcp 2>/dev/null || lsof -ti:9999 | xargs kill -9 2>/dev/null || true
sleep 1

# ── Step 5: Copy agent output as new running version ─────────────────────────
cp "$WORKSPACE/qcai_3d.py" "$WORKSPACE/qcai_3d_running.py"
echo "▶ Copied agent output → qcai_3d_running.py"

# ── Step 6: Launch new visualization ─────────────────────────────────────────
echo ""
echo "▶ Launching updated visualization..."

# Detect terminal and open viz
open_terminal() {
    local title="$1"
    local cmd="$2"
    if   command -v ptyxis        &>/dev/null; then ptyxis --title="$title" -- bash -c "$cmd" &
    elif command -v gnome-terminal &>/dev/null; then gnome-terminal --title="$title" -- bash -c "$cmd" &
    elif command -v konsole        &>/dev/null; then konsole --title "$title" -e bash -c "$cmd" &
    elif command -v xterm          &>/dev/null; then xterm -title "$title" -e bash -c "$cmd" &
    elif command -v kitty          &>/dev/null; then kitty --title "$title" bash -c "$cmd" &
    elif flatpak list 2>/dev/null | grep -q "org.gnome.Ptyxis"; then
        flatpak run org.gnome.Ptyxis --title="$title" -- bash -c "$cmd" &
    else
        echo "  Running in background..."
        cd "$WORKSPACE" && $PYTHON qcai_3d.py &
        return
    fi
}

VIZ_CMD="echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
echo '  QCAI Visualization — Updated'
echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
cd $WORKSPACE && $PYTHON qcai_3d.py
exec bash"

open_terminal "QCAI Visualization" "$VIZ_CMD"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Visualization updated and relaunching"
echo ""
echo "  Agent output: $LINES lines"
echo "  Backup saved: qcai_3d_backup_$TIMESTAMP.py"
echo ""
echo "  To revert to backup if something looks wrong:"
echo "  cp $WORKSPACE/qcai_3d_backup_$TIMESTAMP.py $WORKSPACE/qcai_3d.py"
echo "  ~/update_viz.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
