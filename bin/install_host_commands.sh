#!/usr/bin/env bash
DISTROBOX_NAME="openjarvis-box"
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
HOST_BIN="/var/home/kmonette/bin"
BOX_BIN="/home/kmonette/bin"
CUR_BIN="$HOME/bin"
mkdir -p "$HOST_BIN" "$BOX_BIN" "$CUR_BIN" 2>/dev/null || true

function write_wrapper() {
    local cmd_name="$1"
    local script_path="$2"
    for dest in "$HOST_BIN" "$BOX_BIN" "$CUR_BIN"; do
        cat << INNER_EOF > "$dest/$cmd_name"
#!/usr/bin/env bash
if [ -f /run/.containerenv ]; then bash "$script_path" "\$@"; else distrobox enter "$DISTROBOX_NAME" -- bash "$script_path" "\$@"; fi
INNER_EOF
        chmod +x "$dest/$cmd_name"
    done
}

write_wrapper "qcai-launch" "$JARVIS_ROOT/launch_qcai.sh"
write_wrapper "qcai-stop" "$JARVIS_ROOT/stop_qcai.sh"
write_wrapper "qcai-monitor" "$JARVIS_ROOT/qcai_monitor.sh"

for dest in "$HOST_BIN" "$BOX_BIN" "$CUR_BIN"; do
    cat << INNER_EOF > "$dest/qcai-reset"
#!/usr/bin/env bash
bash $JARVIS_ROOT/safe_workspace_reset.sh "\$1"
INNER_EOF
    chmod +x "$dest/qcai-reset"

    cat << INNER_EOF > "$dest/qcai-fresh"
#!/usr/bin/env bash
echo "🔄 Initiating safe reset and system refresh..."
bash $JARVIS_ROOT/safe_workspace_reset.sh "\$1"
bash $JARVIS_ROOT/stop_qcai.sh
bash $JARVIS_ROOT/launch_qcai.sh
INNER_EOF
    chmod +x "$dest/qcai-fresh"
done
echo "✅ QCAI Host commands updated (safe-reset applied)."
write_wrapper "qcai-agent-add" "$JARVIS_ROOT/registry/add_agent.sh"
write_wrapper "qcai-agent-draft" "$JARVIS_ROOT/registry/draft_agent.sh"
write_wrapper "qcai-agent-add" "$JARVIS_ROOT/registry/add_agent.sh"
write_wrapper "qcai-agent-draft" "$JARVIS_ROOT/registry/draft_agent.sh"
