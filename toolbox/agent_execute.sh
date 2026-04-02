#!/usr/bin/env bash
LOG_DIR="/var/home/kmonette/OpenJarvis/toolbox/logs"
LOG_FILE="$LOG_DIR/execution_$(date +%Y%m%d_%H%M%S).log"
CMD_TYPE=$1; shift; TARGET_CMD="$@"
echo "🤖 Executing: [$CMD_TYPE] $TARGET_CMD" | tee -a "$LOG_FILE"
case "$CMD_TYPE" in
    "pip") python3 -m pip install $TARGET_CMD 2>&1 | tee -a "$LOG_FILE" ;;
    "dnf") sudo dnf install -y $TARGET_CMD 2>&1 | tee -a "$LOG_FILE" ;;
    "script") bash $TARGET_CMD 2>&1 | tee -a "$LOG_FILE" ;;
    "python") python3 $TARGET_CMD 2>&1 | tee -a "$LOG_FILE" ;;
    *) echo "❌ Unknown command type." | tee -a "$LOG_FILE"; exit 1 ;;
esac
