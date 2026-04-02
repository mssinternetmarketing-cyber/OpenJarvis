#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install_host_wrappers.sh — Links Container Tools to Bazzite Host
# ─────────────────────────────────────────────────────────────────────────────

HOST_BIN="/var/home/kmonette/bin"
mkdir -p "$HOST_BIN"

# Function to create a host-side wrapper
create_wrapper() {
    local cmd_name=$1
    local script_path=$2
    local target="$HOST_BIN/$cmd_name"

    echo "🔗 Linking $cmd_name to Host..."
    
    cat << INNER_EOF > "$target"
#!/usr/bin/env bash
# This script proxies the command into the distrobox container
distrobox enter openjarvis-box -- $script_path "\$@"
INNER_EOF

    chmod +x "$target"
}

# 1. Link the Core QCAI Commands
create_wrapper "qcai-launch" "/var/home/kmonette/OpenJarvis/launch_qcai.sh"
create_wrapper "qcai-stop" "/var/home/kmonette/OpenJarvis/stop_qcai.sh"
create_wrapper "qcai-refresh-links" "/var/home/kmonette/OpenJarvis/registry/refresh_links.sh"

# 2. Link all AI-generated Q-Tools
for tool in /var/home/kmonette/OpenJarvis/toolbox/*.{sh,py}; do
    [ -e "$tool" ] || continue
    TNAME=$(basename "$tool")
    TNAME="${TNAME%.*}" # Remove extension
    
    # Prefix with qtool- so you know it's an AI tool
    if [[ "$tool" == *.py ]]; then
        create_wrapper "qtool-$TNAME" "python3 $tool"
    else
        create_wrapper "qtool-$TNAME" "$tool"
    fi
done

echo "✅ All wrappers installed to $HOST_BIN"
echo "👉 CRITICAL: If you haven't yet, run this ON THE HOST:"
echo "   echo 'export PATH=\"\$PATH:/var/home/kmonette/bin\"' >> ~/.bashrc && source ~/.bashrc"
