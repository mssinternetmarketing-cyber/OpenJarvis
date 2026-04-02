#!/usr/bin/env bash
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
STATUS_FILE="$JARVIS_ROOT/SYSTEM_STATUS.json"
echo "Starting QCAI Hardware Monitor Daemon..."
while true; do
    VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null || echo "0")
    VRAM_GB=$(echo "scale=2; $VRAM_USED / 1024" | bc 2>/dev/null || echo "0")
    VRAM_STATUS="GREEN"
    if (( $(echo "$VRAM_GB > 7.5" | bc -l) )); then VRAM_STATUS="BLACK"
    elif (( $(echo "$VRAM_GB > 7.0" | bc -l) )); then VRAM_STATUS="RED"
    elif (( $(echo "$VRAM_GB > 6.5" | bc -l) )); then VRAM_STATUS="YELLOW"; fi

    RAM_TOTAL=$(free -m | awk '/^Mem:/{print $2}'); RAM_USED=$(free -m | awk '/^Mem:/{print $3}')
    RAM_PCT=$(( 100 * RAM_USED / RAM_TOTAL ))
    RAM_STATUS="GREEN"
    if [ "$RAM_PCT" -gt 95 ]; then RAM_STATUS="BLACK"
    elif [ "$RAM_PCT" -gt 85 ]; then RAM_STATUS="RED"
    elif [ "$RAM_PCT" -gt 75 ]; then RAM_STATUS="YELLOW"; fi

    DISK_PCT=$(df -h /var | awk 'NR==2 {print $5}' | sed 's/%//')
    DISK_FREE=$(df -h /var | awk 'NR==2 {print $4}')
    DISK_STATUS="GREEN"
    if [ "$DISK_PCT" -gt 95 ]; then DISK_STATUS="BLACK"; elif [ "$DISK_PCT" -gt 90 ]; then DISK_STATUS="RED"; fi

    cat > "${STATUS_FILE}.tmp" <<INNNER_EOF
{
  "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "vram_gb": $VRAM_GB, "vram_status": "$VRAM_STATUS",
  "ram_pct": $RAM_PCT, "ram_status": "$RAM_STATUS",
  "disk_pct": $DISK_PCT, "disk_free": "$DISK_FREE", "disk_status": "$DISK_STATUS"
}
INNNER_EOF
    mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
    
    if [ "$VRAM_STATUS" == "BLACK" ] || [ "$RAM_STATUS" == "BLACK" ] || [ "$DISK_STATUS" == "BLACK" ]; then
        echo "$(date) - 🚨 CRITICAL OVERLOAD. Issuing safe stop." >> "$JARVIS_ROOT/logs/emergency_stops.log"
        touch "$JARVIS_ROOT/.emergency_pause"
    fi
    sleep 5
done
