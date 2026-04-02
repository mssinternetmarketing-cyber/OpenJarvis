#!/usr/bin/env bash
python3 /var/home/kmonette/OpenJarvis/toolbox/update_sentinel.py || exit 1
# ─────────────────────────────────────────────────────────────────────────────
# qcai-refresh-links v12.0 — Intelligent Container Orchestrator
# ─────────────────────────────────────────────────────────────────────────────
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
BIN_DIR="/var/home/kmonette/bin"
DISTROBOX_NAME="openjarvis-box"

# 1. Create the Host-Side Decision Engine
cat << 'INNER_EOF' > "$BIN_DIR/qcai-exec-engine"
#!/usr/bin/env bash
CMD_PATH=$1
shift
# Logic: If the file is a Python script or lives in the JARVIS_ROOT, use Container.
if [[ "$CMD_PATH" == *.py ]] || [[ "$CMD_PATH" == *"/OpenJarvis/"* ]]; then
    distrobox enter $DISTROBOX_NAME -- $CMD_PATH "$@"
else
    # Fallback to Host execution
    $CMD_PATH "$@"
fi
INNER_EOF
chmod +x "$BIN_DIR/qcai-exec-engine"

# 2. Re-link all tools to use the Engine
for tool in $JARVIS_ROOT/toolbox/*.{sh,py}; do
    [ -e "$tool" ] || continue
    TNAME="qtool-$(basename "${tool%.*}")"
    echo "#!/usr/bin/env bash" > "$BIN_DIR/$TNAME"
    echo "$BIN_DIR/qcai-exec-engine $tool \"\$@\"" >> "$BIN_DIR/$TNAME"
    chmod +x "$BIN_DIR/$TNAME"
done

echo "✅ Container Handler: Orchestrated Intelligence active in $BIN_DIR"
