#!/usr/bin/env bash
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
WS_ROOT="$JARVIS_ROOT/workspaces"
TARGET_WS="${1:-ws_1}"
PENDING_DIR="$JARVIS_ROOT/PostProcessedLogs/Pending_Compression"

if [ ! -d "$WS_ROOT/$TARGET_WS" ]; then echo "❌ Workspace $TARGET_WS does not exist."; exit 1; fi
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SAFE_DEST="$PENDING_DIR/${TARGET_WS}_${TIMESTAMP}"

echo "📦 Securing workspace '$TARGET_WS' for Compression Agent..."
mkdir -p "$SAFE_DEST"
shopt -s dotglob; mv "$WS_ROOT/$TARGET_WS"/* "$SAFE_DEST"/ 2>/dev/null || true; shopt -u dotglob
mkdir -p "$WS_ROOT/$TARGET_WS"

cat > "$WS_ROOT/$TARGET_WS/COMPRESSION_TASK.md" <<INNER_EOF
# Workspace Reset Detected ($TIMESTAMP)
Secure Location: \`$SAFE_DEST\`
@jarvis-compression: Extract value, compress to PostProcessedLogs.
@jarvis-clean: Await confirmation, then purge raw files to save NVMe.
INNER_EOF
echo "✅ Workspace secured and COMPRESSION_TASK.md generated."
