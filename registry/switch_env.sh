#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# qcai-env — Universal Workspace & Mode Switcher
# ─────────────────────────────────────────────────────────────────────────────
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
TARGET_ENV=$1
MODE=${2:-"standard"} # Default to standard, can be "testing"

if [ -z "$TARGET_ENV" ]; then
    echo "Usage: qcai-env [workspace_name] [mode]"
    echo "Example: qcai-env WsTesting testing"
    exit 1
fi

# Create the workspace structure if it doesn't exist
WS_PATH="$JARVIS_ROOT/workspaces/$TARGET_ENV"
mkdir -p "$WS_PATH"/{foundation,knowledge,voice,checkpoints,drafts,logs,memory,components_promoted}

# Seed the environment with Master Knowledge
cp "$JARVIS_ROOT/SYSTEM_MASTER_KNOWLEDGE.md" "$WS_PATH/knowledge/"

# Update the System Link (Simulating a 'Hot-Swap')
ln -sfn "$WS_PATH" "$JARVIS_ROOT/active_ws"

# Log the mode
echo "{\"active_ws\": \"$TARGET_ENV\", \"mode\": \"$MODE\", \"timestamp\": \"$(date)\"}" > "$JARVIS_ROOT/ENV_STATUS.json"

echo "✅ Environment Switched to: $TARGET_ENV"
echo "🛠️  System Mode: $MODE"
echo "🚀 Run 'qcai-launch' to start in this context."
