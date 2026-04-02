#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install_host_commands.sh — Install HOST-side QCAI command shortcuts
#
# Run this ONCE on the HOST (outside distrobox).
# Creates thin wrappers in ~/bin/ that enter distrobox and run the real scripts.
# After running, all QCAI commands work from the HOST terminal directly.
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
make_cmd() {
    local cmd_name="$1"       # e.g. qcai-launch
    local inner_cmd="$2"      # e.g. /var/home/kmonette/OpenJarvis/launch_qcai.sh
    local description="$3"

    cat > "$BIN_DIR/$cmd_name" << EOF
#!/usr/bin/env bash
# $description
# Runs inside distrobox: $DISTROBOX_NAME
distrobox enter $DISTROBOX_NAME -- bash -c "$inner_cmd \$@"
EOF
    chmod +x "$BIN_DIR/$cmd_name"
    echo "  ✅ $cmd_name  →  $description"
}

# ── Install all QCAI commands ─────────────────────────────────────────────────

make_cmd "qcai-launch"   "$JARVIS_ROOT/launch_qcai.sh"          "Start full QCAI system: Ollama + API + Bridge"
make_cmd "qcai-stop"     "$JARVIS_ROOT/stop_qcai.sh"            "Stop QCAI bridge + clear port 9999"
make_cmd "qcai-restart"  "$JARVIS_ROOT/stop_qcai.sh && $JARVIS_ROOT/launch_qcai.sh" "Stop then relaunch QCAI"
make_cmd "qcai-reset"    "$HOME/reset_workspace.sh"             "Reset active workspace (with backup)"
make_cmd "qcai-update"   "$JARVIS_ROOT/jarvis_update.sh"        "Deploy files from OpenJarvisUpdater/"
make_cmd "qcai-status"   "curl -sf http://127.0.0.1:8000/health && echo '✅ API healthy' || echo '❌ API down'" "Check OpenJarvis API health"
make_cmd "qcai-logs"     "tail -f $JARVIS_ROOT/logs/update_log.txt" "Tail the update log"
make_cmd "qcai-update-updater" "$JARVIS_ROOT/update_updater.sh" "Update jarvis_update.sh safely"

# Full reset + restart in one command
cat > "$BIN_DIR/qcai-fresh" << EOF
#!/usr/bin/env bash
# Full clean restart: reset workspace → stop → launch
# Usage: qcai-fresh [workspace_name]
WS=\${1:-}
distrobox enter $DISTROBOX_NAME -- bash -c "
  \$HOME/reset_workspace.sh \$WS && \\
  $JARVIS_ROOT/stop_qcai.sh && \\
  $JARVIS_ROOT/launch_qcai.sh
"
EOF
chmod +x "$BIN_DIR/qcai-fresh"
echo "  ✅ qcai-fresh    →  reset + stop + launch in one command"
echo "                       Usage: qcai-fresh [workspace_name]"

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
echo "  qcai-launch          Start full system: Ollama + API + Bridge"
echo "  qcai-stop            Stop the bridge"
echo "  qcai-restart         Stop + relaunch"
echo "  qcai-reset           Reset active workspace (backed up)"
echo "  qcai-reset ws_2      Reset specific workspace"
echo "  qcai-fresh           Reset + stop + launch in one go"
echo "  qcai-fresh ws_2      Fresh start on specific workspace"
echo "  qcai-update          Deploy files from OpenJarvisUpdater/"
echo "  qcai-status          Check API health"
echo "  qcai-logs            Tail update log
  qcai-update-updater  Update jarvis_update.sh itself safely"
echo ""
echo "  Your existing sequence now becomes:"
echo "  qcai-fresh"
echo "  (replaces: ~/reset_workspace.sh && ~/stop_qcai.sh && ~/launch_qcai.sh)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
