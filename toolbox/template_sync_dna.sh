#!/bin/bash
# USAGE: ./template_sync_dna.sh <version> <status> <architecture_description>
VERSION=$1
STATUS=$2
ARCH_DESC=$3

if [ -z "$VERSION" ]; [ -z "$STATUS" ]; then
    echo "❌ Error: Missing DNA parameters."
    exit 1
fi

# Update the Truth Ledger definition inside the sync script
sed -i "s/\"system_version\": \".*\"/\"system_version\": \"$VERSION\"/" /var/home/kmonette/OpenJarvis/bin/sync_knowledge.py
sed -i "s/\"status\": \".*\"/\"status\": \"$STATUS\"/" /var/home/kmonette/OpenJarvis/bin/sync_knowledge.py

echo "🧬 DNA Template Applied: System is now $VERSION ($STATUS)"
