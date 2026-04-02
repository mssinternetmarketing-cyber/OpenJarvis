#!/usr/bin/env bash
NAME=$1
ID=$2
REG_FILE="/var/home/kmonette/OpenJarvis/registry/agents.json"

if [ -z "$NAME" ] || [ -z "$ID" ]; then
    echo "Usage: qcai-agent-add [name] [slack_id]"
    exit 1
fi

# Add to JSON safely
python3 -c "import json; d=json.load(open('$REG_FILE')); d['$NAME']='$ID'; json.dump(d, open('$REG_FILE', 'w'), indent=4)"

echo "✅ Agent $NAME ($ID) registered."
echo "🔄 Triggering bridge hot-reload..."
# We touch a file that our bridge respawn loop (start_qcai.sh) will see
pkill -f slack_bridge.py
