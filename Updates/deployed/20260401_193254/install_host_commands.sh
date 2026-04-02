#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install_host_commands.sh v9.2 — Install HOST-side QCAI command shortcuts
#
# Run this ONCE on the HOST (outside distrobox).
# Creates thin wrappers in ~/bin/ that enter distrobox and run real scripts.
# All QCAI commands then work from the HOST terminal directly.
#
# Usage: bash install_host_commands.sh
# ─────────────────────────────────────────────────────────────────────────────

DISTROBOX_NAME="openjarvis-box"
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
BIN_DIR="$HOME/bin"
mkdir -p "$BIN_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing QCAI HOST commands → $BIN_DIR"
echo "  Distrobox: $DISTROBOX_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Helper: create a host wrapper that runs a distrobox command ───────────────
# Correctly forwards runtime arguments via '$@' evaluated AT RUNTIME.
make_cmd() {
    local cmd_name="$1"
    local inner_script="$2"
    local description="$3"

    cat > "$BIN_DIR/$cmd_name" << WRAPPER
#!/usr/bin/env bash
# $description
# Runs inside distrobox: $DISTROBOX_NAME
distrobox enter $DISTROBOX_NAME -- bash -c "$inner_script \"\$@\"" -- "\$@"
WRAPPER
    chmod +x "$BIN_DIR/$cmd_name"
    echo "  ✅ $cmd_name  →  $description"
}

# ── Core system commands ──────────────────────────────────────────────────────

make_cmd "qcai-launch"   "$JARVIS_ROOT/launch_qcai.sh"       "Start full QCAI: Ollama + API + Bridge + Viz"
make_cmd "qcai-stop"     "$JARVIS_ROOT/stop_qcai.sh"         "Stop bridge, viz watcher, viz windows + clear port 9999"
make_cmd "qcai-update"   "$JARVIS_ROOT/jarvis_update.sh"     "Deploy files from OpenJarvisUpdater/"
make_cmd "qcai-status"   "curl -sf http://127.0.0.1:8000/health && echo '✅ API healthy' || echo '❌ API down'" "Check OpenJarvis API health"
make_cmd "qcai-logs"     "tail -f $JARVIS_ROOT/logs/update_log.txt" "Tail the update log"
make_cmd "qcai-update-updater" "$JARVIS_ROOT/update_updater.sh" "Update jarvis_update.sh safely"

# ── Visualization commands ────────────────────────────────────────────────────

make_cmd "qcai-viz"        "$JARVIS_ROOT/viz_loop.sh"    "Start visualization watcher (event-driven auto-update)"
make_cmd "qcai-viz-pause"  "$HOME/viz_pause.sh"          "Pause viz auto-updates (window stays open)"
make_cmd "qcai-viz-resume" "$HOME/viz_resume.sh"         "Resume viz auto-updates"
make_cmd "qcai-viz-update" "$JARVIS_ROOT/update_viz.sh"  "Manually trigger viz restart with latest agent output"

# ── Training mode ─────────────────────────────────────────────────────────────

make_cmd "qcai-trainer"  "python3 $JARVIS_ROOT/qcai_trainer.py"  "Launch live quantum training display"

# ── qcai-restart — stop then relaunch ─────────────────────────────────────────
cat > "$BIN_DIR/qcai-restart" << WRAPPER
#!/usr/bin/env bash
# Stop then relaunch full QCAI system
distrobox enter $DISTROBOX_NAME -- bash -c "$JARVIS_ROOT/stop_qcai.sh && $JARVIS_ROOT/launch_qcai.sh \"\$@\"" -- "\$@"
WRAPPER
chmod +x "$BIN_DIR/qcai-restart"
echo "  ✅ qcai-restart  →  Stop + relaunch"

# ── qcai-reset — accepts optional workspace arg ───────────────────────────────
# Fix: arg is forwarded correctly at runtime, not baked in at install time
cat > "$BIN_DIR/qcai-reset" << 'WRAPPER'
#!/usr/bin/env bash
# Reset workspace (active or named)
# Usage: qcai-reset           (reset active workspace)
#        qcai-reset ws_2      (reset specific workspace)
#        qcai-reset --list    (list workspaces)
#        qcai-reset --dry-run (preview)
DISTROBOX_NAME="openjarvis-box"
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
distrobox enter "$DISTROBOX_NAME" -- bash "$HOME/reset_workspace.sh" "$@"
WRAPPER
chmod +x "$BIN_DIR/qcai-reset"
echo "  ✅ qcai-reset    →  Reset workspace (args forwarded correctly)"
echo "                      Usage: qcai-reset [ws_2] [--dry-run] [--list]"

# ── qcai-fresh — reset + stop + launch in one go ──────────────────────────────
cat > "$BIN_DIR/qcai-fresh" << 'WRAPPER'
#!/usr/bin/env bash
# Full clean restart: reset workspace → stop → launch
# Usage: qcai-fresh           (fresh start on active workspace)
#        qcai-fresh ws_2      (fresh start on specific workspace)
#        qcai-fresh --no-viz  (skip viz terminal)
DISTROBOX_NAME="openjarvis-box"
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
WS_ARG=""
LAUNCH_ARGS=""
for arg in "$@"; do
    case "$arg" in
        --no-viz) LAUNCH_ARGS="--no-viz" ;;
        *) WS_ARG="$arg" ;;
    esac
done
distrobox enter "$DISTROBOX_NAME" -- bash -c "
  $HOME/reset_workspace.sh $WS_ARG &&
  $JARVIS_ROOT/stop_qcai.sh &&
  $JARVIS_ROOT/launch_qcai.sh $LAUNCH_ARGS
"
WRAPPER
chmod +x "$BIN_DIR/qcai-fresh"
echo "  ✅ qcai-fresh    →  Reset + stop + launch in one go"
echo "                      Usage: qcai-fresh [ws_2] [--no-viz]"

# ── qcai-mode — switch between frontend and training mode ─────────────────────
cat > "$BIN_DIR/qcai-mode" << 'WRAPPER'
#!/usr/bin/env bash
# Switch QCAI operating mode
# Usage: qcai-mode frontend   (ws_1 — build qcai_3d.py frontend)
#        qcai-mode training   (quantum network training + PEIG experiments)
#        qcai-mode status     (show current mode)
DISTROBOX_NAME="openjarvis-box"
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
WORKSPACES="$JARVIS_ROOT/workspaces"
MODE="${1:-status}"

case "$MODE" in
    frontend)
        distrobox enter "$DISTROBOX_NAME" -- bash -c "
            echo '$WORKSPACES/ws_1' > '$WORKSPACES/active_workspace.txt'
            echo '✅ Mode: FRONTEND (ws_1)'
            echo '   Agents will build qcai_3d.py — the 3D visualization frontend'
            echo '   Start system: qcai-launch'
        "
        ;;
    training)
        distrobox enter "$DISTROBOX_NAME" -- bash -c "
            # Ensure ws_training exists
            mkdir -p '$WORKSPACES/ws_training'
            echo '$WORKSPACES/ws_training' > '$WORKSPACES/active_workspace.txt'
            echo '✅ Mode: QUANTUM TRAINING (ws_training)'
            echo '   Agents will run PEIG experiments and quantum network training'
            echo '   Launch trainer: qcai-trainer'
            echo '   Launch full system: qcai-launch'
        "
        ;;
    status)
        distrobox enter "$DISTROBOX_NAME" -- bash -c "
            if [ -f '$WORKSPACES/active_workspace.txt' ]; then
                WS=\$(basename \$(cat '$WORKSPACES/active_workspace.txt'))
                echo \"Active workspace: \$WS\"
                case \"\$WS\" in
                    ws_1)        echo 'Mode: FRONTEND — building qcai_3d.py' ;;
                    ws_training) echo 'Mode: QUANTUM TRAINING — PEIG experiments' ;;
                    ws_2)        echo 'Mode: JARVIS SYSTEM — bridge self-improvement' ;;
                    *)           echo 'Mode: CUSTOM (\$WS)' ;;
                esac
            else
                echo 'No active workspace set — defaults to ws_1 (frontend)'
            fi
        "
        ;;
    *)
        echo "Usage: qcai-mode [frontend|training|status]"
        echo "  frontend  — ws_1: build the 3D visualization frontend"
        echo "  training  — ws_training: quantum network training + PEIG"
        echo "  status    — show current mode"
        ;;
esac
WRAPPER
chmod +x "$BIN_DIR/qcai-mode"
echo "  ✅ qcai-mode     →  Switch operating mode"
echo "                      Usage: qcai-mode [frontend|training|status]"

# ── Add ~/bin to PATH if not already there ────────────────────────────────────
echo ""
SHELL_RC=""
if [ -f "$HOME/.bashrc" ];  then SHELL_RC="$HOME/.bashrc"; fi
if [ -f "$HOME/.zshrc" ];   then SHELL_RC="$HOME/.zshrc";  fi

PATH_LINE='export PATH="$HOME/bin:$PATH"'
if [ -n "$SHELL_RC" ]; then
    if ! grep -q 'HOME/bin' "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# QCAI HOST commands" >> "$SHELL_RC"
        echo "$PATH_LINE" >> "$SHELL_RC"
        echo "  ✅ Added ~/bin to PATH in $SHELL_RC"
        echo "  ⚠️  Run: source $SHELL_RC  (or open a new terminal)"
    else
        echo "  ✅ ~/bin already in PATH"
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ HOST commands installed"
echo ""
echo "  System:"
echo "    qcai-launch          Start full system: Ollama + API + Bridge + Viz"
echo "    qcai-stop            Stop bridge, viz watcher, viz windows"
echo "    qcai-restart         Stop + relaunch"
echo "    qcai-reset           Reset active workspace (backed up)"
echo "    qcai-reset ws_2      Reset specific workspace"
echo "    qcai-fresh           Reset + stop + launch in one go"
echo "    qcai-fresh ws_2      Fresh start on specific workspace"
echo "    qcai-update          Deploy files from OpenJarvisUpdater/"
echo "    qcai-status          Check API health"
echo "    qcai-logs            Tail update log"
echo "    qcai-update-updater  Update jarvis_update.sh itself safely"
echo ""
echo "  Visualization:"
echo "    qcai-viz             Start viz watcher (event-driven auto-update)"
echo "    qcai-viz-pause       Pause auto-updates (window stays open)"
echo "    qcai-viz-resume      Resume auto-updates"
echo "    qcai-viz-update      Manually restart viz with latest agent output"
echo ""
echo "  Mode:"
echo "    qcai-mode frontend   Switch to frontend build mode (ws_1)"
echo "    qcai-mode training   Switch to quantum training mode"
echo "    qcai-mode status     Show current mode"
echo ""
echo "  Training:"
echo "    qcai-trainer         Launch live quantum training display"
echo ""
echo "  Quick start:"
echo "    qcai-fresh           (replaces: reset + stop + launch)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
