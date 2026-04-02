#!/usr/bin/env bash
NAME=$1
PERS_DIR="/var/home/kmonette/OpenJarvis/Personalities"
PREPARE_DIR="/var/home/kmonette/OpenJarvis/prepare_for_update"

if [ -z "$NAME" ]; then echo "Usage: qcai-agent-draft [name]"; exit 1; fi

cat << INNER_EOF > "$PREPARE_DIR/${NAME}_proposal.md"
# Proposed Agent: $NAME
**Role:** [AI to fill in]
**Status:** PENDING ID CONFIRMATION
INNER_EOF

echo "✅ Drafted personality for $NAME in prepare_for_update/"
