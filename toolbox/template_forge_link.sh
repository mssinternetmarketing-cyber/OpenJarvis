#!/bin/bash
# USAGE: ./template_forge_link.sh <alias> <target_script>
ALIAS=$1
TARGET=$2

if [ -z "$ALIAS" ] || [ -z "$TARGET" ]; then
    echo "❌ Error: Alias and Target are required."
    exit 1
fi

# 1. Ensure target is executable
chmod +x "$TARGET"

# 2. Use the base linker to create the global bin entry
/var/home/kmonette/OpenJarvis/toolbox/template_link_cmd.sh "$ALIAS" "$TARGET"

echo "🔗 Forge: Global link created for '$ALIAS' -> '$TARGET'"
