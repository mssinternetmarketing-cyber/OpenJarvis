#!/bin/bash
# USAGE: ./template_link_cmd.sh <command-name> <path-to-script>
CMD_NAME=$1
SCRIPT_PATH=$2
BIN_DIR="/var/home/kmonette/.local/bin"

if [ -z "$CMD_NAME" ] || [ -z "$SCRIPT_PATH" ]; then
    echo "❌ Error: Missing arguments. Usage: link-cmd <name> <path>"
    exit 1
fi

echo "#!/bin/bash" > "$BIN_DIR/$CMD_NAME"
echo "python3 $SCRIPT_PATH \"\$@\"" >> "$BIN_DIR/$CMD_NAME"
chmod +x "$BIN_DIR/$CMD_NAME"

echo "✅ Success: $CMD_NAME is now linked to $SCRIPT_PATH"
