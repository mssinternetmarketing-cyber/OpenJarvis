#!/bin/bash
# USAGE: ./template_update_flow.sh <launcher_path> <gauge_path>
LAUNCHER=${1:-"/var/home/kmonette/OpenJarvis/bin/launch_qcai.sh"}
GAUGE=${2:-"/var/home/kmonette/OpenJarvis/bin/entropy_gauge.py"}

cat << FLOW_EOF > /var/home/kmonette/OpenJarvis/bin/flow_coordinator.sh
#!/bin/bash
# OpenJarvis v14.x - Self-Optimized Flow
LAUNCHER="$LAUNCHER"
GAUGE="$GAUGE"
PURIFY="/var/home/kmonette/OpenJarvis/toolbox/hybrid_enforcer.py"
SYNC="/var/home/kmonette/OpenJarvis/bin/sync_knowledge.py"

while true; do
    echo "--- [ 🌊 INFINITE FLOW: ACTIVE ] ---"
    \$LAUNCHER
    ENTROPY=\$(python3 \$GAUGE)
    if [ "\$ENTROPY" == "HIGH" ]; then
        echo "🧹 ENTROPY ALERT: Initializing Background Purge & Sync..."
        python3 \$PURIFY --silent
        python3 \$SYNC
    fi
    sleep 2
done
FLOW_EOF

chmod +x /var/home/kmonette/OpenJarvis/bin/flow_coordinator.sh
echo "🌊 Flow Architect: flow_coordinator.sh has been re-wired."
