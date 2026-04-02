#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# update_updater.sh — Updates jarvis_update.sh safely
# Usage (inside distrobox): ./update_updater.sh
# Usage (from HOST after qcai-install): qcai-update-updater
# ─────────────────────────────────────────────────────────────────────────────

SRC="/var/home/kmonette/OpenJarvis/Updates/OpenJarvisUpdater/jarvis_update.sh"
DST="/var/home/kmonette/OpenJarvis/jarvis_update.sh"
BAK="/var/home/kmonette/OpenJarvis/update_backups/jarvis_update_$(date +%Y%m%d_%H%M%S).sh"

if [ ! -f "$SRC" ]; then
    echo "❌ No jarvis_update.sh found in OpenJarvisUpdater/"
    echo "   Drop the new version there first."
    exit 1
fi

mkdir -p "$(dirname "$BAK")"
[ -f "$DST" ] && cp "$DST" "$BAK" && echo "✅ Backup saved: $BAK"

cp "$SRC" "$DST"
chmod +x "$DST"
mv "$SRC" "/var/home/kmonette/OpenJarvis/Updates/deployed/$(date +%Y%m%d_%H%M%S)_jarvis_update.sh"
echo "✅ jarvis_update.sh updated"
