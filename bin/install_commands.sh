#!/bin/bash
BIN_DIR="/var/home/kmonette/.local/bin"
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"

# Function to create a shortcut
create_cmd() {
    echo "#!/bin/bash" > "$BIN_DIR/$1"
    echo "$2" >> "$BIN_DIR/$1"
    chmod +x "$BIN_DIR/$1"
    echo "✅ Linked: $1"
}

# Mapping the Swarm and Tools
create_cmd "qcai-pulse" "python3 $JARVIS_ROOT/agents/compression_agent.py"
create_cmd "qcai-sentinel" "python3 $JARVIS_ROOT/toolbox/update_sentinel.py"
create_cmd "qcai-purify" "python3 $JARVIS_ROOT/toolbox/hybrid_enforcer.py"
create_cmd "qcai-marathon" "bash $JARVIS_ROOT/bin/pulse_coordinator.sh"
create_cmd "qcai-logs" "tail -f $JARVIS_ROOT/logs/debug.log $JARVIS_ROOT/logs/update_integrity.log"

echo "🚀 All commands are now ready for user and agent use."
