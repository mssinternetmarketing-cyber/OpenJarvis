#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# stop_qcai.sh v9.2 — Stop all QCAI processes safely
# Kills: Slack bridge, viz_loop watcher, all qcai_3d windows, port 9999
# Usage: ~/stop_qcai.sh
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🛑 Stopping QCAI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Stop bridge ────────────────────────────────────────────────────────────
if pkill -f slack_bridge.py 2>/dev/null; then
    echo "  ✅ Bridge stopped"
else
    echo "  ⚠️  Bridge was not running"
fi

# ── 2. Stop viz_loop watcher (the inotify/poll loop) ─────────────────────────
if pkill -f viz_loop.sh 2>/dev/null; then
    echo "  ✅ Viz watcher stopped"
else
    echo "  ℹ️  Viz watcher was not running"
fi

# ── 3. Stop all running visualizations (qcai_3d windows) ─────────────────────
if pkill -f "qcai_3d" 2>/dev/null; then
    echo "  ✅ Visualization windows closed"
else
    echo "  ℹ️  No visualization windows were running"
fi

# ── 4. Remove viz pause lock if present ──────────────────────────────────────
rm -f "$HOME/.qcai_viz_pause"

# ── 5. Clear port 9999 ────────────────────────────────────────────────────────
sleep 1
if fuser -k 9999/tcp 2>/dev/null || lsof -ti:9999 | xargs kill -9 2>/dev/null; then
    echo "  ✅ Port 9999 cleared"
else
    echo "  ℹ️  Port 9999 already clear"
fi

sleep 1
echo ""
echo "  Done. Run qcai-launch to restart."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
