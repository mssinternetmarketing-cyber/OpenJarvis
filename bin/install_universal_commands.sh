#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install_universal_commands.sh — Host/Container Agnostic Wrapper
# ─────────────────────────────────────────────────────────────────────────────

JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
BIN_DIR="/var/home/kmonette/bin"
DISTROBOX_NAME="openjarvis-box"

mkdir -p "$BIN_DIR"

# List of all the commands we want available everywhere
COMMANDS=(
    "qcai-launch:$JARVIS_ROOT/launch_qcai.sh"
    "qcai-stop:$JARVIS_ROOT/stop_qcai.sh"
    "qcai-restart:$JARVIS_ROOT/registry/restart_qcai.sh"
    "qcai-reset:$JARVIS_ROOT/safe_workspace_reset.sh"
    "qcai-monitor:$JARVIS_ROOT/qcai_monitor.sh"
    "qcai-agent-add:$JARVIS_ROOT/registry/add_agent.sh"
    "qcai-agent-draft:$JARVIS_ROOT/registry/draft_agent.sh"
    "qcai-viz:python3 $JARVIS_ROOT/qcai_modern_3d.py"
    "qcai-update:bash $JARVIS_ROOT/jarvis_update.sh"
)

for cmd_pair in "${COMMANDS[@]}"; do
    CMD_NAME="${cmd_pair%%:*}"
    CMD_PATH="${cmd_pair#*:}"
    
    TARGET_FILE="$BIN_DIR/$CMD_NAME"
    
    cat << INNER_EOF > "$TARGET_FILE"
#!/usr/bin/env bash
# Detect if we are already inside the container
if [ -f /run/.containerenv ]; then
    # We are inside the container: Run directly
    $CMD_PATH "\$@"
else
    # We are on the Host: Route into the Distrobox
    distrobox enter $DISTROBOX_NAME -- $CMD_PATH "\$@"
fi
INNER_EOF

    chmod +x "$TARGET_FILE"
    echo "✅ Universal Command Linked: $CMD_NAME"
done

# Ensure /var/home/kmonette/bin is in the PATH for Bazzite
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo 'export PATH="$PATH:/var/home/kmonette/bin"' >> ~/.bashrc
    echo "⚠️ Added $BIN_DIR to your .bashrc. Please run 'source ~/.bashrc' or restart terminal."
fi
