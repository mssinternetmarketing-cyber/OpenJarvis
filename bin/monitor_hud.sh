#!/bin/bash
echo "🖥️  OpenJarvis PRIME HUD: Monitoring Logs & Truth Ledger..."
echo "--- [ Press CTRL+C to Exit ] ---"
# This streams the debug log and the Truth DNA in real-time
tail -f /var/home/kmonette/OpenJarvis/logs/debug.log /var/home/kmonette/OpenJarvis/registry/truth.json
